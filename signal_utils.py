# signal_utils.py

import hashlib
import re
import csv

from config import (TELEGRAM_API_ID, TELEGRAM_API_HASH, TELEGRAM_CHANNEL,
                    DEFAULT_ORDER_TYPE, DEFAULT_LIMIT_PRICE, DEFAULT_STOP_PRICE,
                    UNDERLYING_SYMBOL, CSV_FILE_PATH, CSV_COLUMN_MAPPING,
                    CSV_STATUS_COLUMN, CSV_PENDING_VALUE, MULTI_SIGNAL_REGEX)

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
    if not TELEGRAM_API_ID or "YOUR_API_ID" in TELEGRAM_API_ID: return None
    try:
        from telethon import TelegramClient
        client = TelegramClient('session_name', TELEGRAM_API_ID, TELEGRAM_API_HASH)
        import asyncio
        async def run():
            await client.start(); message = await client.get_messages(TELEGRAM_CHANNEL, limit=1); return message[0].text
        return asyncio.run(run())
    except Exception as e:
        print(f"Could not connect to Telegram: {e}. Please use manual entry.")
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
                "expiry": expiry, "sc_strike": sc_str, "lc_strike": lc_str, 
                "trigger_price": str(trigger_midpoint),
                "order_type": DEFAULT_ORDER_TYPE, "lmt_price": DEFAULT_LIMIT_PRICE, "stop_price": DEFAULT_STOP_PRICE
            })
        except (ValueError, IndexError):
            print(f"Warning: Skipping an invalid line in message: {match.group(0)}")
            continue
    return signals if signals else None

def get_signals_from_csv():
    if not CSV_FILE_PATH: return None
    signals = []
    try:
        with open(CSV_FILE_PATH, mode='r', encoding='utf-8') as infile:
            reader = csv.DictReader(infile)
            for row in reader:
                if row.get(CSV_STATUS_COLUMN) == CSV_PENDING_VALUE:
                    try:
                        expiry = row[CSV_COLUMN_MAPPING["expiry"]].replace('-', '')
                        lc = round_strike(row[CSV_COLUMN_MAPPING["lc_strike"]])
                        sc = round_strike(row[CSV_COLUMN_MAPPING["sc_strike"]])
                        trigger = row[CSV_COLUMN_MAPPING["trigger_price"]]
                        signals.append({"expiry": expiry, "sc_strike": sc, "lc_strike": lc, "trigger_price": trigger, "order_type": DEFAULT_ORDER_TYPE, "lmt_price": DEFAULT_LIMIT_PRICE, "stop_price": DEFAULT_STOP_PRICE})
                    except (KeyError, ValueError): continue
        return signals if signals else None
    except FileNotFoundError: return None

def get_signal_interactively():
    """Presents a menu for manual signal entry."""
    print("\n--- MANUAL SIGNAL ENTRY ---")
    print("  1. Paste the full multi-signal message.")
    print("  2. Enter details for one or more trades one-by-one.")
    
    while True:
        choice = input("Please choose an option (1 or 2): ").strip()
        if choice == '1':
            pasted_text = input("\nPaste message here in ONE line and press Enter:\n> ")
            if pasted_text.strip():
                parsed_signals = parse_multi_signal_message(pasted_text)
                if parsed_signals:
                    print(f"Parsed {len(parsed_signals)} signal(s) successfully from pasted text.")
                    return parsed_signals
                else:
                    print("\nCould not find any valid, untriggered signals in the pasted message.")
            else: print("No message pasted.")
        
        elif choice == '2':
            # --- NEW: Loop for multiple single entries ---
            manual_signals = []
            while True:
                print("\n--- Entering details for a trade ---")
                try:
                    tp = float(input(f"Enter {UNDERLYING_SYMBOL} Trigger Price: "))
                    ed = input("Enter Expiry Date (YYYY-MM-DD): ")
                    ls = float(input("Enter Long Call (LC) Strike: "))
                    ss = float(input("Enter Short Call (SC) Strike: "))
                    ot_in = input(f"Enter Order Type [default: {DEFAULT_ORDER_TYPE}]: ").strip().upper()
                    ot = ot_in if ot_in else DEFAULT_ORDER_TYPE
                    lp, sp = None, None
                    if ot == 'LMT': lp = float(input("Enter Limit Price: "))
                    elif ot == 'STP': sp = float(input("Enter Stop Price: "))
                    elif ot == 'STP LMT': sp = float(input("Enter Stop Price: ")); lp = float(input("Enter Limit Price: "))
                    
                    signal_data = {"expiry": ed.replace('-', ''), "sc_strike": str(ss), "lc_strike": str(ls), "trigger_price": str(tp), "order_type": ot, "lmt_price": lp, "stop_price": sp}
                    manual_signals.append(signal_data)
                except ValueError:
                    print("Invalid input. Please try this trade again.")

                if input("\nAdd another trade manually? (y/n): ").lower() != 'y':
                    break # Exit the inner loop
            
            return manual_signals

        else: print("Invalid choice. Please enter 1 or 2.")
