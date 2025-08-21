# signal_utils.py

import asyncio
import hashlib
import re
import csv
import os
import json
from telethon import TelegramClient
from telethon.errors import SessionPasswordNeededError

from config import (TELEGRAM_API_ID, TELEGRAM_API_HASH, TELEGRAM_CHANNEL, get_user_data_dir,
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
    print("telegram channel:", TELEGRAM_CHANNEL, flush=True)
    print("Fetching latest signal from Telegram channel...", flush=True)
    if not TELEGRAM_API_ID or not TELEGRAM_API_HASH:
        print("Missing Telegram API credentials.", flush=True)
        return None

    async def run():
        # --- Use the correct user data directory ---
        USER_DATA_DIR = get_user_data_dir()
        session_name_with_path = os.path.join(USER_DATA_DIR, 'session_name')
        session_file = session_name_with_path + '.session'
        
        # ONLY try client.start() if session file exists AND we can verify it works
        if os.path.exists(session_file):
            # --- Use the full path for the client ---
            client = TelegramClient(session_name_with_path, int(TELEGRAM_API_ID), TELEGRAM_API_HASH)
            try:
                await client.start()
                # Check if actually logged in
                if await client.is_user_authorized():
                    message = await client.get_messages(TELEGRAM_CHANNEL, limit=1)
                    await client.disconnect()
                    return message[0].text
                else:
                    # Session exists but is invalid, go to manual login
                    print("Session invalid, manual login required.", flush=True)
                    await client.disconnect()
            except Exception as e:
                print(f"Session failed: {e}", flush=True)
                if 'client' in locals() and client.is_connected(): await client.disconnect()
        
        # If no session or session failed, do manual login
        client = await run_manual_login()
        if client is None:
            return None
        try:
            message = await client.get_messages(TELEGRAM_CHANNEL, limit=1)
            await client.disconnect()
            return message[0].text
        except Exception as e:
            print(f"Failed to fetch messages: {e}", flush=True)
            if client.is_connected(): await client.disconnect()
            return None

    try:
        return asyncio.run(run())
    except Exception as e:
        print(f"Telegram fetch/parse error: {e}", flush=True)
        return None

async def run_manual_login():
    # --- Use the correct user data directory here as well ---
    USER_DATA_DIR = get_user_data_dir()
    session_name_with_path = os.path.join(USER_DATA_DIR, 'session_name')
    client = TelegramClient(session_name_with_path, int(TELEGRAM_API_ID), TELEGRAM_API_HASH)
    await client.connect()
    print("Enter your phone number (with country code, e.g. +85265778011):", flush=True)
    phone_number = input().strip()
    if not phone_number.startswith('+'):
        print("Phone number must start with '+'. Please try again.", flush=True)
        return None
    sms_req = await client.send_code_request(phone_number, force_sms=False)
    print("Enter the code sent to your Telegram app", flush=True)
    code = input().strip()
    if not code.isdigit():
        print("Code must be numeric. Please try again.", flush=True)
        return None
    try:
        await client.sign_in(phone_number, code=code, phone_code_hash=sms_req.phone_code_hash)
    except SessionPasswordNeededError:
        print("Two-factor authentication is enabled. Please enter your 2FA password:", flush=True)
        password = input().strip()
        await client.sign_in(password=password)
    # Now you are logged in and can fetch messages
    return client

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
    
    # Add the user-friendly explanation here
    print(
        "Please paste the full Telegram message.\n"
        "The message can contain multiple lines, but each valid signal must contain:\n"
        "到期日: YYYY-MM-DD SC: [STRIKE_PRICE] LC: [STRIKE_PRICE] ...other text... 未觸發 ...other text...\n"
        "Here is an example of a valid line:\n"
        "到期日: 2025-08-22 SC: 6500 LC: 6495 ...other text... 未觸發 ...other text...\n"
        "The bot will automatically calculate the trigger price as the midpoint of the strikes.\n"
        "Please paste the full Telegram message:"
    , flush=True)

    pasted_text = input().strip()
    if pasted_text:
        parsed_signals = parse_multi_signal_message(pasted_text)
        if parsed_signals:
            print(f"Parsed {len(parsed_signals)} signal(s) successfully from pasted text.", flush=True)
            return parsed_signals
        else:
            print("Could not find any valid, untriggered signals in the pasted message.", flush=True)
    else: print("No message pasted.", flush=True)

