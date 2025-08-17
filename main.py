# main.py

import threading
import time
from datetime import datetime, timedelta
import pytz
import asyncio
import argparse # 1. Import argparse
import json

from config import (IBKR_HOST, IBKR_PORT, IBKR_CLIENT_ID, 
                    UNDERLYING_SYMBOL, IBKR_ACCOUNT, SNAPMID_OFFSET)
from signal_utils import (get_signal_from_telegram, parse_multi_signal_message, 
                          get_signals_from_csv, get_signal_interactively, 
                          get_signal_hash)
from ibkr_app import IBKRApp

from ibapi.contract import ComboLeg, Contract
from ibapi.order import Order
from ibapi.order_condition import Create, OrderCondition
from ibapi.execution import ExecutionFilter

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
    # Add this argument
    parser.add_argument(
        '--client-id',
        type=int,
        default=None,
        help="Override the IBKR Client ID from the config file."
    )
    args = parser.parse_args()
    day_selection = args.check_day

    # Use the client ID from args if provided, otherwise from config
    client_id_to_use = args.client_id if args.client_id is not None else IBKR_CLIENT_ID

    app = IBKRApp()
    # Ensure executions_event exists for compatibility
    if not hasattr(app, "executions_event"):
        import threading
        app.executions_event = threading.Event()
    app.connect(IBKR_HOST, IBKR_PORT, client_id_to_use) # Use the new variable here
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

    print("Requesting filled orders...")
    app.executions_event.clear()
    app.reqExecutions(app.get_new_reqid(), ExecutionFilter())
    app.executions_event.wait(5)  # Wait up to 5 seconds for filled orders

    existing_orders = app.open_orders + app.filled_orders
    print(f"Found {len(existing_orders)} open or filled order(s).")

    try:
        trigger_conid = app.get_spx_index_conid()
        print(f"Successfully fetched current SPX Index conId: {trigger_conid}")
    except Exception as e:
        print(f"Fatal Error: {e}. Exiting.")
        app.disconnect()
        return

    # --- ADD THIS SECTION TO START THE PRICE STREAM ---
    print("\nStarting live SPX price stream...")
    spx_stream_contract = Contract()
    spx_stream_contract.symbol = "SPX"
    spx_stream_contract.secType = "IND"
    spx_stream_contract.exchange = "CBOE"
    spx_stream_contract.currency = "USD"
    # reqId 100 is dedicated to this stream (matches tickPrice)
    app.reqMktData(100, spx_stream_contract, "", False, False, [])
    time.sleep(2) # Give a moment for the stream to start
    # --- END OF ADDED SECTION ---

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
        print(f"Processing signal: {json.dumps(signal_data)}")
        
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
        # --- FIX: ADD STRIKES TO THE DICTIONARY ---
        managed_orders.append({
            "id": orderId, 
            "trigger": float(signal_data['trigger_price']), 
            "lc_strike": float(signal_data['lc_strike']), # Add this
            "sc_strike": float(signal_data['sc_strike']), # Add this
            "contract": combo_contract, 
            "order_obj": order, 
            "hash": signal_hash
        })
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

    # --- SAFER ALTERNATIVE: Retry up to 5 times ---
    max_attempts = 5
    for attempt_count in range(1, max_attempts + 1):
        app.underlying_open_price = None  # Reset before request
        app.historical_data_event.clear() # Reset event
        
        print(f"Attempt {attempt_count}/{max_attempts} to fetch {UNDERLYING_SYMBOL} open price...")
        app.reqHistoricalData(99, underlying_contract, "", "1 D", "1 day", "TRADES", 1, 1, False, [])
        
        app.historical_data_event.wait(10) # Wait up to 10 seconds for data

        if app.underlying_open_price is not None:
            break  # Success
    else: # This 'else' belongs to the 'for' loop, runs if the loop finishes without a 'break'
        print(f"Could not get {UNDERLYING_SYMBOL} open price after {max_attempts} attempts. Please manually transmit orders.")
        app.disconnect()
        return

    print(f"SPX open price: {app.underlying_open_price}")

    managed_orders.sort(key=lambda x: x["trigger"])
    process_managed_orders(app, managed_orders, UNDERLYING_SYMBOL)
    time.sleep(10)
    
    # Check for critical error after placing orders. Loop as long as there are error IDs.
    while app.error_order_ids:
        now = datetime.now(tz)
        if now >= market_close_time:
            print("Market close reached. Stopping error retry loop.")
            break
        
        print(f"Critical error(s) detected for order IDs: {app.error_order_ids}. Retrying after 1 minute.")
        time.sleep(60)  # Always wait 60 seconds before next retry

        # Loop through a copy of the error list to avoid modification issues
        for error_id in list(app.error_order_ids):
            error_orders = [o for o in managed_orders if o["id"] == error_id]

            if not error_orders:
                # This error was likely resolved (ID changed), so remove it from the list.
                print(f"Order ID {error_id} seems resolved. Removing from error list.")
                app.error_order_ids.remove(error_id)
                continue

            # Since we know there's only one order, access it directly
            order_info = error_orders[0] 
            
            lc_strike = order_info.get("lc_strike")

            if lc_strike is None:
                print(f"Could not determine LC strike for error order {error_id}. Skipping.")
                continue

            # --- USE THE LIVE PRICE HERE ---
            live_price = app.current_spx_price
            if live_price is None:
                print(f"\nLive SPX price not available yet. Waiting...")
                continue

            print(f"\nChecking retry condition for order {error_id}: Live SPX price: {live_price}, LC strike: {lc_strike}")
            if live_price >= lc_strike:
                print(f"Condition met. Retrying order {error_id}...")
                new_orderId = app.nextOrderId
                app.nextOrderId += 1
                final_order = order_info["order_obj"]
                final_order.transmit = True
                app.placeOrder(new_orderId, order_info["contract"], final_order)
                # This is the key step: updating the ID resolves the error for the next loop check
                order_info["id"] = new_orderId
            else:
                print(f"Condition not met for order {error_id}. Will re-check in the next cycle.")

    print("\nScript has completed its automated tasks.")
    app.cancelMktData(100)
    time.sleep(2)
    app.disconnect()

if __name__ == "__main__":
    main_loop()
