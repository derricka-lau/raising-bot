# signal_utils.py

import asyncio
import hashlib
import re
import os
import requests
import pandas_market_calendars as mcal
import pandas as pd
from telethon import TelegramClient
from telethon.errors import SessionPasswordNeededError
from datetime import datetime, timezone
from typing import List
from config import (TELEGRAM_API_ID, TELEGRAM_API_HASH, TELEGRAM_CHANNEL, get_user_data_dir,
                    DEFAULT_ORDER_TYPE, DEFAULT_LIMIT_PRICE, DEFAULT_STOP_PRICE, MULTI_SIGNAL_REGEX, SNAPMID_OFFSET)
from dataclasses import dataclass
from typing import Optional
from pytz import timezone
from collections import Counter

@dataclass
class Signal:
    expiry: str
    lc_strike: float
    sc_strike: float
    trigger_price: float
    order_type: str
    lmt_price: Optional[float] = None
    stop_price: Optional[float] = None
    snapmid_offset: Optional[float] = None
    allowed_duplicates: int = 1  # <-- Add this field

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

def gather_signals(allow_manual_fallback: bool = True) -> List[Signal]:
    signals: List[Signal] = []

    # 1If no signals, try Telegram
    if not signals:
        try:
            txt = get_signal_from_telegram()
            if txt:
                parsed = parse_multi_signal_message(txt) or []
                for d in parsed:
                    try:
                        signals.append(to_signal(d))
                    except Exception as e:
                        print(f"Skipping malformed Telegram signal {d}: {e}", flush=True)
        except Exception as e:
            print(f"Telegram fetch/parse error: {e}", flush=True)

    # 2. Manual fallback only if allowed
    if not signals and allow_manual_fallback:
        manual = get_signal_interactively() or []
        for d in manual:
            try:
                signals.append(to_signal(d))
            except Exception as e:
                print(f"Skipping malformed manual signal {d}: {e}")
    
    # Use a tuple as the key for each signal
    signal_keys = [
        (s.expiry, s.lc_strike, s.sc_strike, s.trigger_price)
        for s in signals
    ]
    counts = Counter(signal_keys)

    # Set allowed_duplicates for each signal
    for s in signals:
        key = (s.expiry, s.lc_strike, s.sc_strike, s.trigger_price)
        s.allowed_duplicates = counts[key]

    return signals

def to_signal(d: dict) -> Signal:
    expiry = get_valid_trading_day(str(d["expiry"]))
    return Signal(
        expiry=expiry,
        lc_strike=float(d["lc_strike"]),
        sc_strike=float(d["sc_strike"]),
        trigger_price=float(d["trigger_price"]),
        order_type=str(d["order_type"]),
        lmt_price=(None if d.get("lmt_price") in (None, "", "None") else float(d["lmt_price"])),
        stop_price=(None if d.get("stop_price") in (None, "", "None") else float(d["stop_price"])),
        snapmid_offset=(None if d.get("snapmid_offset") in (None, "", "None") else float(d.get("snapmid_offset", SNAPMID_OFFSET))),
        allowed_duplicates=int(d.get("allowed_duplicates", 1))  # <-- Set from dict, default 1
    )

def get_valid_trading_day(date_str):
    """
    Returns date_str (YYYYMMDD) if it's a valid US trading day, otherwise returns previous valid trading day.
    """
    nyse = mcal.get_calendar('NYSE')
    date = datetime.strptime(date_str, "%Y%m%d")
    schedule = nyse.valid_days(start_date="2000-01-01", end_date=date.strftime("%Y-%m-%d"))
    if len(schedule) == 0:
        raise ValueError("No valid trading days found before given date.")
    if pd.Timestamp(date) in schedule:
        return date_str
    else:
        prev_trading_day = schedule[-1]
        return prev_trading_day.strftime("%Y%m%d")

