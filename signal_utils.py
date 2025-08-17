# signal_utils.py

import asyncio
import hashlib
import re
import csv
from telethon import TelegramClient

from config import (TELEGRAM_API_ID, TELEGRAM_API_HASH, TELEGRAM_CHANNEL,
                    DEFAULT_ORDER_TYPE, DEFAULT_LIMIT_PRICE, DEFAULT_STOP_PRICE,
                    UNDERLYING_SYMBOL, MULTI_SIGNAL_REGEX)

# --- Hash and Record-Keeping Functions (Unchanged) ---
def get_signal_hash(text): return hashlib.sha256(text.encode()).hexdigest()
def already_processed(hash_str, filename='processed_signals.txt'):
    try:
        with open(filename, 'r') as f: return hash_str in f.read().splitlines()
    except FileNotFoundError: return False
def record_processed(hash_str, filename='processed_signals.txt'):
    with open(filename, 'a') as f: f.write(hash_str + '\n')

# --- Signal Input Functions ---
def get_signal_from_telegram():
    print("telegram id:", TELEGRAM_API_ID, flush=True)
    print("Fetching latest signal from Telegram channel...", flush=True)
    if not TELEGRAM_API_ID or "YOUR_API_ID" in TELEGRAM_API_ID: return None
    try:
        client = TelegramClient('session_name', TELEGRAM_API_ID, TELEGRAM_API_HASH)
        async def run():
            await client.start()
            message = await client.get_messages(TELEGRAM_CHANNEL, limit=1)
            return message[0].text
        # Add timeout here (e.g., 5 seconds)
        return asyncio.run(asyncio.wait_for(run(), timeout=5))
    except asyncio.TimeoutError:
        print("Telegram connection timed out. Please use manual entry.", flush=True)
        return None
    except Exception as e:
        print(f"Could not connect to Telegram: {e}. Please use manual entry.", flush=True)
        return None

def round_strike(strike):
    try:
        return str(round(float(strike) / 5) * 5)
    except Exception:
        return strike  # fallback if not a number

def parse_multi_signal_message(text):
    signals = []
    for match in re.finditer(MULTI_SIGNAL_REGEX, text):
        try:
            expiry = match.group(1).replace('-', '')
            sc_str = round_strike(match.group(2))
            lc_str = round_strike(match.group(3))
            trigger_midpoint = (float(sc_str) + float(lc_str)) / 2.0
            signals.append({
                "expiry": expiry,
                "sc_strike": sc_str,
                "lc_strike": lc_str,  # <-- fix here
                "trigger_price": str(trigger_midpoint),
                "order_type": DEFAULT_ORDER_TYPE,
                "lmt_price": DEFAULT_LIMIT_PRICE,
                "stop_price": DEFAULT_STOP_PRICE
            })
        except (ValueError, IndexError):
            print(f"Warning: Skipping an invalid line in message: {match.group(0)}", flush=True)
            continue
    return signals if signals else None

def get_signal_interactively():
    """Presents a menu for manual signal entry."""
    print("--- MANUAL SIGNAL ENTRY ---", flush=True)
    print("Paste the full telegram signal message:", flush=True)
    pasted_text = input().strip()
    if pasted_text:
        parsed_signals = parse_multi_signal_message(pasted_text)
        if parsed_signals:
            print(f"Parsed {len(parsed_signals)} signal(s) successfully from pasted text.", flush=True)
            return parsed_signals
        else:
            print("Could not find any valid, untriggered signals in the pasted message.", flush=True)
    else: print("No message pasted.", flush=True)

