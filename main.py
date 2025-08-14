# main.py

import threading
import time
from datetime import datetime, timedelta
import pytz
import tkinter as tk

from config import (IBKR_HOST, IBKR_PORT, IBKR_CLIENT_ID, 
                    UNDERLYING_SYMBOL, IBKR_ACCOUNT, SNAPMID_OFFSET)
from signal_utils import (get_signal_from_telegram, parse_multi_signal_message, 
                          get_signals_from_csv, get_signal_interactively, 
                          get_signal_hash)
from ibkr_app import IBKRApp

from ibapi.contract import ComboLeg, Contract
from ibapi.order import Order
from ibapi.order_condition import Create, OrderCondition

def get_trading_day_open(tz, choice='next'):
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

def main():
    app = IBKRApp()
    app.connect(IBKR_HOST, IBKR_PORT, IBKR_CLIENT_ID)
    api_thread = threading.Thread(target=app.run, daemon=True)
    api_thread.start()
    time.sleep(2)
    app.reqOpenOrders()  # <-- This will log ALL open orders in TWS
    time.sleep(2)
    if not app.nextOrderId: print("Failed to connect to IBKR."); return

    # Fetch the current conId for the SPX Index once
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
    
    # telegram_text = get_signal_from_telegram()
    # if telegram_text:
    #     telegram_signals = parse_multi_signal_message(telegram_text)
    #     if telegram_signals:
    #         print(f"Found {len(telegram_signals)} untriggered signals on Telegram.")
    #         signals_to_process.extend(telegram_signals)
    
    # if not signals_to_process:
    #     csv_signals = get_signals_from_csv()
    #     if csv_signals:
    #         print(f"Found {len(csv_signals)} PENDING signals in CSV file.")
    #         signals_to_process.extend(csv_signals)
    
    if not signals_to_process:
        manual_signals = get_signal_interactively()
        if manual_signals:
            signals_to_process.extend(manual_signals)

    if not signals_to_process:
        print("No new signals found from any source. Exiting.")
        app.disconnect(); return
    
    for signal_data in signals_to_process:
        print(f"Processing signal: {signal_data}")
        identifier = f"{UNDERLYING_SYMBOL}-{signal_data['expiry']}-{signal_data['lc_strike']}-{signal_data['sc_strike']}-{signal_data['trigger_price']}"
        signal_hash = get_signal_hash(identifier)
        orderId = app.nextOrderId
        app.nextOrderId += 1
        combo_contract = Contract(); combo_contract.symbol=UNDERLYING_SYMBOL; combo_contract.secType="BAG"; combo_contract.currency="USD"; combo_contract.exchange="SMART"
        
        lc_conid = app.get_spx_option_conid(signal_data['expiry'], signal_data['lc_strike'], "C")
        sc_conid = app.get_spx_option_conid(signal_data['expiry'], signal_data['sc_strike'], "C")

        leg1 = ComboLeg(); leg1.conId=lc_conid; leg1.ratio=1; leg1.action="BUY"; leg1.exchange="SMART"; leg1.lastTradeDateOrContractMonth=signal_data['expiry']; leg1.strike=float(signal_data['lc_strike']); leg1.right="C"
        leg2 = ComboLeg(); leg2.conId=sc_conid; leg2.ratio=1; leg2.action="SELL"; leg2.exchange="SMART"; leg2.lastTradeDateOrContractMonth=signal_data['expiry']; leg2.strike=float(signal_data['sc_strike']); leg2.right="C"
        combo_contract.comboLegs = [leg1, leg2]
        order = Order()
        order.action = "BUY"
        order.totalQuantity = 1
        order.tif = "DAY"
        order.transmit = False
        order.orderType = signal_data['order_type']
        order.account = IBKR_ACCOUNT  # <-- Add this line
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

    # Always use US/Eastern time for market open
    tz = pytz.timezone('US/Eastern')

    # User chooses when to run the check
    day_selection = ''
    while day_selection not in ['today', 'next']:
        user_input = input("\nWhen should the GO/NO-GO check run? [1] Today's Open [2] Next Trading Day's Open: ")
        if user_input == '1':
            day_selection = 'today'
        elif user_input == '2':
            day_selection = 'next'
        else:
            print("Invalid choice. Please enter 1 or 2.")

    market_open_time = get_trading_day_open(tz, day_selection)
    print(f"Scheduled market open check for: {market_open_time.strftime('%Y-%m-%d %H:%M:%S %Z')}")
    print(f"\nStaged {len(managed_orders)} order(s). Waiting for market open...")
    while datetime.now(tz) < market_open_time:
        time.sleep(10)

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
        attempt_count += 1
        print(f"Attempt {attempt_count} to fetch {UNDERLYING_SYMBOL} open price...")
        app.reqHistoricalData(99, underlying_contract, "", "1 D", "1 day", "TRADES", 1, 1, False, [])
        time.sleep(5)  # Wait for data to arrive

        if app.underlying_open_price:
            break  # Success

        retry_choice = input("Failed to fetch open price. Try again? (y/n): ").lower()
        if retry_choice != 'y':
            break  # User chose not to retry

    if not app.underlying_open_price:
        print(f"Could not get {UNDERLYING_SYMBOL} open price. Please manually transmit orders.")
        app.disconnect()
        return

    print(f"SPX open price: {app.underlying_open_price}")

    for order_info in managed_orders:
        if app.underlying_open_price >= order_info["trigger"]:
            print(f"!! NO-GO for Order {order_info['id']} !! {UNDERLYING_SYMBOL} open ({app.underlying_open_price}) >= trigger ({order_info['trigger']}). CANCELLING.")
            app.cancelOrder(order_info["id"])
        else:
            print(f"** GO for Order {order_info['id']}! ** Open price ({app.underlying_open_price}) is favorable. TRANSMITTING.")
            final_order = order_info["order_obj"]
            final_order.transmit = True
            app.placeOrder(order_info["id"], order_info["contract"], final_order)
    print("\nScript has completed its automated tasks.")
    app.reqOpenOrders()
    time.sleep(5)
    app.disconnect()

if __name__ == "__main__":
    main()
