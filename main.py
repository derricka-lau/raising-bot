# main.py

import threading
import time
from datetime import datetime, timedelta
import pytz
import asyncio
import argparse # 1. Import argparse

from config import (IBKR_HOST, IBKR_PORT, IBKR_CLIENT_ID, 
                    UNDERLYING_SYMBOL, IBKR_ACCOUNT, SNAPMID_OFFSET)
from signal_utils import (get_signal_from_telegram, parse_multi_signal_message, 
                          get_signals_from_csv, get_signal_interactively, 
                          get_signal_hash)
from ibkr_app import IBKRApp

from ibapi.contract import ComboLeg, Contract
from ibapi.order import Order
from ibapi.order_condition import Create, OrderCondition

def get_trading_day_open(tz, choice='today'):
    """
    Calculates the market open time for 'today' or the 'next' trading day.
    """
    now = datetime.now(tz)
    target_day = now

    if choice == 'next':
        # Always start from the next calendar day
        target_day = now + timedelta(days=1)
    
    # For 'next' choice, find the next weekday if the target is a weekend.
    # For 'today' choice, this loop won't run if today is a weekday.
    while target_day.weekday() >= 5:  # 5 = Saturday, 6 = Sunday
        target_day += timedelta(days=1)
        
    return target_day.replace(hour=9, minute=30, second=0, microsecond=0)

def is_duplicate(signal_leg_conIds, signal_trigger, existing_orders):
    """
    Checks if a signal matches any existing open order by comparing leg conIds and trigger price.
    """
    for order in existing_orders:
        if (order.get("secType") == "BAG" and
            order.get("trigger_price") == signal_trigger and
            order.get("leg_conIds") == signal_leg_conIds):
            return True # Found a perfect match
    return False

async def wait_until_market_open(market_open_time, tz):
    while True:
        now = datetime.now(tz)
        seconds_left = (market_open_time - now).total_seconds()
        if seconds_left <= 0:
            break
        mins, secs = divmod(int(seconds_left), 60)
        print(f"\rWaiting for market open: {mins:02d}:{secs:02d} remaining...", end="", flush=True)
        await asyncio.sleep(1)
    print("\nMarket open reached!")

def process_managed_orders(app, managed_orders, underlying_symbol):
    """
    Processes managed orders by comparing open price to trigger and transmitting/cancelling as needed.
    """
    for order_info in managed_orders:
        if app.underlying_open_price >= order_info["trigger"]:
            print(f"!! NO-GO for Order {order_info['id']} !! {underlying_symbol} open ({app.underlying_open_price}) >= trigger ({order_info['trigger']}). CANCELLING.")
            app.cancelOrder(order_info["id"])
        else:
            print(f"** GO for Order {order_info['id']}! ** Open price ({app.underlying_open_price}) is favorable. TRANSMITTING.")
            final_order = order_info["order_obj"]
            final_order.transmit = True
            app.placeOrder(order_info["id"], order_info["contract"], final_order)

def main_loop():
    parser = argparse.ArgumentParser(description="Automated SPX Bull Spread Order Management for IBKR.")
    parser.add_argument(
        '--check-day', 
        type=str, 
        choices=['today', 'next'], 
        default='today', 
        help="Specify whether to run the GO/NO-GO check at 'today's' or the 'next' trading day's open. Defaults to 'today'."
    )
    args = parser.parse_args()
    day_selection = args.check_day

    app = IBKRApp()
    app.connect(IBKR_HOST, IBKR_PORT, IBKR_CLIENT_ID)
    api_thread = threading.Thread(target=app.run, daemon=True)
    api_thread.start()

    print("Connecting to IBKR...")
    connected = app.connected_event.wait(5)
    if not connected or not app.nextOrderId:
        print("Failed to connect to IBKR or get next OrderId. Exiting.")
        return

    print(f"Successfully connected. Next Order ID: {app.nextOrderId}")

    print("Requesting open orders...")
    app.reqOpenOrders()
    app.open_orders_event.wait(5)
    existing_orders = app.open_orders
    print(f"Found {len(existing_orders)} open order(s).")

    try:
        trigger_conid = app.get_spx_index_conid()
        print(f"Successfully fetched current SPX Index conId: {trigger_conid}")
    except Exception as e:
        print(f"Fatal Error: {e}. Exiting.")
        app.disconnect()
        return

    managed_orders = []
    signals_to_process = []

    print("\n--------------------------")
    print("Looking for new signals...")

    telegram_text = get_signal_from_telegram()
    if telegram_text:
        telegram_signals = parse_multi_signal_message(telegram_text)
        if telegram_signals:
            print(f"Found {len(telegram_signals)} untriggered signals on Telegram.")
            signals_to_process.extend(telegram_signals)

    if not signals_to_process:
        manual_signals = get_signal_interactively()
        if manual_signals:
            signals_to_process.extend(manual_signals)

    if not signals_to_process:
        print("No new signals found from any source. Waiting for next trading day setup...")
        app.disconnect()
        day_selection = 'next'  # Always wait for next trading day after first run
        time.sleep(10)

    for signal_data in signals_to_process:
        print(f"Processing signal: {signal_data}")
        
        # --- Get conIds for the new signal's legs FIRST ---
        try:
            lc_conid = app.get_spx_option_conid(signal_data['expiry'], signal_data['lc_strike'], "C")
            sc_conid = app.get_spx_option_conid(signal_data['expiry'], signal_data['sc_strike'], "C")
            signal_leg_conIds = sorted([lc_conid, sc_conid])
        except Exception as e:
            print(f"Could not get contract details for signal {signal_data}. Skipping. Error: {e}")
            continue

        # --- Perform duplicate check using conIds ---
        if is_duplicate(signal_leg_conIds, float(signal_data['trigger_price']), existing_orders):
            print(f"--> Duplicate order detected: An existing order with strikes {signal_data['lc_strike']}/{signal_data['sc_strike']} and trigger {signal_data['trigger_price']} already exists. Skipping.")
            continue

        identifier = f"{UNDERLYING_SYMBOL}-{signal_data['expiry']}-{signal_data['lc_strike']}-{signal_data['sc_strike']}-{signal_data['trigger_price']}"
        signal_hash = get_signal_hash(identifier)
        orderId = app.nextOrderId
        app.nextOrderId += 1
        combo_contract = Contract(); combo_contract.symbol=UNDERLYING_SYMBOL; combo_contract.secType="BAG"; combo_contract.currency="USD"; combo_contract.exchange="SMART"
        
        leg1 = ComboLeg(); leg1.conId=lc_conid; leg1.ratio=1; leg1.action="BUY"; leg1.exchange="SMART"
        leg2 = ComboLeg(); leg2.conId=sc_conid; leg2.ratio=1; leg2.action="SELL"; leg2.exchange="SMART"
        combo_contract.comboLegs = [leg1, leg2]
        order = Order()
        order.action = "BUY"
        order.totalQuantity = 1
        order.tif = "DAY"
        order.transmit = False
        order.orderType = signal_data['order_type']
        order.account = IBKR_ACCOUNT
        if order.orderType == 'LMT': 
            order.lmtPrice = signal_data['lmt_price']
        elif order.orderType == 'STP': 
            order.auxPrice = signal_data['stop_price']
        elif order.orderType == 'STP LMT': 
            order.lmtPrice = signal_data['lmt_price']; order.auxPrice = signal_data['stop_price']
        elif order.orderType == 'SNAP MID':
            order.auxPrice = signal_data.get('snapmid_offset', SNAPMID_OFFSET)
        condition = Create(OrderCondition.Price)
        condition.conId = trigger_conid
        condition.exchange = 'CBOE'
        condition.isMore = True
        condition.price = float(signal_data['trigger_price'])
        condition.triggerMethod = 0
        order.conditions.append(condition)
        order.eTradeOnly = False
        order.firmQuoteOnly = False

        app.placeOrder(orderId, combo_contract, order)
        managed_orders.append({"id": orderId, "trigger": float(signal_data['trigger_price']), "contract": combo_contract, "order_obj": order, "hash": signal_hash})
        print(f"--> Staged Order {orderId} for {UNDERLYING_SYMBOL} ({order.orderType}) with trigger at {signal_data['trigger_price']} for review.")
    # Fetch and display open orders from IBKR
    if not managed_orders:
        print("No orders were staged (they may have been duplicates or none were valid). Exiting."); app.disconnect(); return

    # Always use US/Eastern time for market open/close
    tz = pytz.timezone('US/Eastern')
    market_open_time = get_trading_day_open(tz, day_selection)
    market_close_time = market_open_time.replace(hour=16, minute=0, second=0, microsecond=0)

    print(f"Scheduled market open check for '{day_selection}' open: {market_open_time.strftime('%Y-%m-%d %H:%M:%S %Z')}")
    print(f"\nStaged {len(managed_orders)} order(s). Waiting for market open...")

    asyncio.run(wait_until_market_open(market_open_time, tz))

    print(f"\n--- AT-OPEN GO/NO-GO CHECK for {UNDERLYING_SYMBOL} ---")
    underlying_contract = Contract()
    underlying_contract.symbol = UNDERLYING_SYMBOL
    underlying_contract.secType = "IND"
    underlying_contract.currency = "USD"
    underlying_contract.exchange = "CBOE"

    # Interactive retry logic for fetching the open price
    attempt_count = 0
    while True:
        app.underlying_open_price = None  # Reset before request
        app.historical_data_event.clear() # Reset event
        attempt_count += 1
        print(f"Attempt {attempt_count} to fetch {UNDERLYING_SYMBOL} open price...")
        app.reqHistoricalData(99, underlying_contract, "", "1 D", "1 day", "TRADES", 1, 1, False, [])
        
        # --- Best Practice: Wait for historical data using an event ---
        app.historical_data_event.wait(10) # Wait up to 10 seconds for data

        if app.underlying_open_price is not None:
            break  # Success

        retry_choice = input("Failed to fetch open price. Try again? (y/n): ").lower()
        if retry_choice != 'y':
            break  # User chose not to retry

    if not app.underlying_open_price:
        print(f"Could not get {UNDERLYING_SYMBOL} open price. Please manually transmit orders.")
        app.disconnect()
        return

    print(f"SPX open price: {app.underlying_open_price}")

    managed_orders.sort(key=lambda x: x["trigger"])
    process_managed_orders(app, managed_orders, UNDERLYING_SYMBOL)
    time.sleep(10)
    
    # Check for critical error after placing orders
    while app.both_sides_error:
        now = datetime.now(tz)
        # Retry until market close
        if now >= market_close_time:
            print("Market close reached. Stopping error retry loop.")
            break

        print("A critical error occurred: Both sides of the US Option contract were detected. Process again after 1 minute.")
        time.sleep(60)  # Wait 1 minutes before retrying

        # Filter managed_orders for the problematic reqId/orderId
        error_order_id = app.last_error_orderId
        error_orders = [o for o in managed_orders if o["id"] == error_order_id]

        # Assign a new orderId for retransmitting only the problematic order
        for order_info in error_orders:
            print(f"Retransmitting order {order_info['id']} with new OrderId...")
            new_orderId = app.nextOrderId
            app.nextOrderId += 1
            final_order = order_info["order_obj"]
            final_order.transmit = True
            app.placeOrder(new_orderId, order_info["contract"], final_order)
            # Update managed_orders so the new orderId is tracked
            order_info["id"] = new_orderId
        time.sleep(10)
        if not app.both_sides_error:
            print("No more critical errors detected. Continuing with normal operation.")
            break

    print("\nScript has completed its automated tasks.")
    time.sleep(2) # Give a moment for final messages
    app.disconnect()

if __name__ == "__main__":
    main_loop()
