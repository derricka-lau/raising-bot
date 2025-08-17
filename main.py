# main.py

import threading
import time
from datetime import datetime, timedelta
import pytz
import asyncio
import argparse # 1. Import argparse
import json
from dataclasses import dataclass
from typing import List, Optional, Tuple

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

@dataclass
class ManagedOrder:
    id: int
    trigger: float
    lc_strike: float
    sc_strike: float
    contract: Contract
    order_obj: Order
    hash: str

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

def connect_with_retry(app, host, port, client_id, attempts=3):
    for i in range(1, attempts + 1):
        try:
            app.connect(host, port, client_id)
            api_thread = threading.Thread(target=app.run, daemon=True)
            api_thread.start()
            print(f"Connecting to IBKR... (attempt {i}/{attempts})")
            if app.connected_event.wait(10) and app.nextOrderId:
                print(f"Successfully connected. Next Order ID: {app.nextOrderId}")
                return True
            print("Connection wait timed out or no OrderId.")
        except Exception as e:
            print(f"Connect error: {e}")
        finally:
            if (not app.connected_event.is_set()) or (not app.nextOrderId):
                try:
                    app.disconnect()
                except Exception:
                    pass
                time.sleep(1.5 * i)
    return False

def request_with_retry(request_fn, event, attempts=3, wait_secs=6, before_each=None, desc="request"):
    for i in range(1, attempts + 1):
        try:
            if before_each: before_each()
            event.clear()
            request_fn()
            if event.wait(wait_secs):
                return True
            print(f"{desc} timed out (attempt {i}/{attempts}). Retrying...")
        except Exception as e:
            print(f"{desc} error (attempt {i}/{attempts}): {e}")
        time.sleep(1.0 * i)
    return False

async def wait_until_market_open(market_open_time, tz):
    # keep single-line printing for terminal; web will de-duplicate on client
    while True:
        now = datetime.now(tz)
        seconds_left = (market_open_time - now).total_seconds()
        if seconds_left <= 0:
            break
        mins, secs = divmod(int(seconds_left), 60)
        print(f"Waiting for market open: {mins:02d}:{secs:02d} remaining...", flush=True)
        await asyncio.sleep(1)
    print("Market open reached!", flush=True)

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

def to_signal(d: dict) -> Signal:
    return Signal(
        expiry=str(d["expiry"]),
        lc_strike=float(d["lc_strike"]),
        sc_strike=float(d["sc_strike"]),
        trigger_price=float(d["trigger_price"]),
        order_type=str(d["order_type"]),
        lmt_price=(None if d.get("lmt_price") in (None, "", "None") else float(d["lmt_price"])),
        stop_price=(None if d.get("stop_price") in (None, "", "None") else float(d["stop_price"])),
        snapmid_offset=(None if d.get("snapmid_offset") in (None, "", "None") else float(d.get("snapmid_offset", SNAPMID_OFFSET))),
    )

def fetch_existing_orders(app: IBKRApp) -> List[dict]:
    print("Requesting open orders...")
    ok = request_with_retry(lambda: app.reqOpenOrders(), app.open_orders_event, attempts=3, wait_secs=8, desc="Open orders")
    if not ok:
        print("Failed to fetch open orders after retries. Continuing with empty set.")
    open_orders = app.open_orders

    print("Requesting filled orders...")
    ok = request_with_retry(lambda: app.reqExecutions(app.get_new_reqid(), ExecutionFilter()),
                            app.executions_event, attempts=3, wait_secs=8, desc="Filled orders")
    if not ok:
        print("Failed to fetch filled orders after retries. Continuing with open orders only.")
    all_orders = open_orders + app.filled_orders
    print(f"Found {len(all_orders)} open or filled order(s).")
    return all_orders

def get_trigger_conid_with_retry(app: IBKRApp, attempts: int = 3) -> Optional[int]:
    trigger_conid = None
    for i in range(1, attempts + 1):
        try:
            trigger_conid = app.get_spx_index_conid()
            print(f"Successfully fetched current SPX Index conId: {trigger_conid}")
            return trigger_conid
        except Exception as e:
            print(f"Fetch SPX conId failed (attempt {i}/{attempts}): {e}")
            time.sleep(1.5 * i)
    return None

def start_spx_stream(app: IBKRApp, req_id_start: int = 100, tries: int = 3) -> None:
    print("\nStarting live SPX price stream...")
    spx = Contract(); spx.symbol="SPX"; spx.secType="IND"; spx.exchange="CBOE"; spx.currency="USD"
    for i in range(tries):
        req_id = req_id_start + i  # Use a different req_id each time
        app.reqMktData(req_id, spx, "", False, False, [])
        time.sleep(1.5 * (i + 1))
        if app.current_spx_price is not None:
            break
        print(f"SPX live price not yet available (attempt {i+1}/{tries}). Retrying stream request...")

def get_option_conid_with_retry(app: IBKRApp, expiry: str, strike: float, right: str, attempts: int = 3) -> int:
    last_err: Optional[Exception] = None
    for i in range(1, attempts + 1):
        try:
            return app.get_spx_option_conid(expiry, strike, right)
        except Exception as e:
            last_err = e
            print(f"get_conid failed for {expiry} {strike}{right} (attempt {i}/{attempts}): {e}")
            time.sleep(0.5 * i)
    raise last_err or Exception("Unknown conid error")

def build_combo_contract(lc_conid: int, sc_conid: int) -> Contract:
    c = Contract(); c.symbol=UNDERLYING_SYMBOL; c.secType="BAG"; c.currency="USD"; c.exchange="SMART"
    leg1 = ComboLeg(); leg1.conId=lc_conid; leg1.ratio=1; leg1.action="BUY"; leg1.exchange="SMART"
    leg2 = ComboLeg(); leg2.conId=sc_conid; leg2.ratio=1; leg2.action="SELL"; leg2.exchange="SMART"
    c.comboLegs = [leg1, leg2]
    return c

def build_staged_order(signal: Signal, trigger_conid: int) -> Order:
    o = Order()
    o.action = "BUY"
    o.totalQuantity = 1
    o.tif = "DAY"
    o.transmit = False
    o.orderType = signal.order_type
    o.account = IBKR_ACCOUNT

    if o.orderType == "LMT":
        if signal.lmt_price is None: raise ValueError("LMT order requires lmt_price")
        o.lmtPrice = float(signal.lmt_price)
    elif o.orderType == "STP":
        if signal.stop_price is None: raise ValueError("STP order requires stop_price")
        o.auxPrice = float(signal.stop_price)
    elif o.orderType == "STP LMT":
        if signal.lmt_price is None or signal.stop_price is None: raise ValueError("STP LMT requires lmt_price and stop_price")
        o.lmtPrice = float(signal.lmt_price); o.auxPrice = float(signal.stop_price)
    elif o.orderType == "SNAP MID":
        # IB uses auxPrice for offset for SNAP MID
        if signal.snapmid_offset is not None:
            o.auxPrice = float(signal.snapmid_offset)
        else:
            o.auxPrice = float(SNAPMID_OFFSET)

    cond = Create(OrderCondition.Price)
    cond.conId = int(trigger_conid)
    cond.exchange = "CBOE"
    cond.isMore = True
    cond.price = float(signal.trigger_price)
    cond.triggerMethod = 0
    o.conditions.append(cond)
    o.eTradeOnly = False
    o.firmQuoteOnly = False
    return o

def stage_order(app: IBKRApp, signal: Signal, contract: Contract, order: Order, signal_hash: str) -> ManagedOrder:
    order_id = app.nextOrderId
    app.nextOrderId += 1
    app.placeOrder(order_id, contract, order)
    print(f"--> Staged Order {order_id} for {UNDERLYING_SYMBOL} ({order.orderType}) with trigger at {signal.trigger_price} for review.")
    return ManagedOrder(
        id=order_id,
        trigger=signal.trigger_price,
        lc_strike=signal.lc_strike,
        sc_strike=signal.sc_strike,
        contract=contract,
        order_obj=order,
        hash=signal_hash,
    )

def gather_signals() -> List[Signal]:
    signals: List[Signal] = []
    # Telegram
    try:
        txt = get_signal_from_telegram()
        if txt:
            parsed = parse_multi_signal_message(txt) or []
            for d in parsed:
                try:
                    signals.append(to_signal(d))
                except Exception as e:
                    print(f"Skipping malformed Telegram signal {d}: {e}")
    except Exception as e:
        print(f"Telegram fetch/parse error: {e}")
    # Manual fallback
    if not signals:
        manual = get_signal_interactively() or []
        for d in manual:
            try:
                signals.append(to_signal(d))
            except Exception as e:
                print(f"Skipping malformed manual signal {d}: {e}")
    return signals

def fetch_open_price_with_retry(app: IBKRApp, symbol: str, attempts: int = 5, wait_secs: int = 10) -> Optional[float]:
    underlying_contract = Contract(); underlying_contract.symbol = symbol; underlying_contract.secType = "IND"; underlying_contract.currency = "USD"; underlying_contract.exchange = "CBOE"
    for i in range(1, attempts + 1):
        app.underlying_open_price = None
        app.historical_data_event.clear()
        print(f"Attempt {i}/{attempts} to fetch {symbol} open price...")
        app.reqHistoricalData(99, underlying_contract, "", "1 D", "1 day", "TRADES", 1, 1, False, [])
        got = app.historical_data_event.wait(wait_secs)
        if app.underlying_open_price is not None and got:
            return app.underlying_open_price
    return None

def run_error_retry_loop(app: IBKRApp, managed_orders: List[ManagedOrder], market_close_time: datetime, tz) -> None:
    while app.error_order_ids:
        now = datetime.now(tz)
        if now >= market_close_time:
            print("Market close reached. Stopping error retry loop.")
            break
        print(f"Critical error(s) detected for order IDs: {app.error_order_ids}. Retrying after 1 minute.")
        time.sleep(60)
        for error_id in list(app.error_order_ids):
            matches = [m for m in managed_orders if m.id == error_id]
            if not matches:
                print(f"Order ID {error_id} seems resolved. Removing from error list.")
                app.error_order_ids.remove(error_id)
                continue
            mo = matches[0]
            live_price = app.current_spx_price
            if live_price is None:
                print("Live SPX price not available yet. Waiting...")
                continue
            print(f"Checking retry condition for order {error_id}: Live={live_price}, LC={mo.lc_strike}")
            if live_price >= mo.lc_strike:
                print(f"Condition met. Retrying order {error_id}...")
                new_id = app.nextOrderId
                app.nextOrderId += 1
                mo.order_obj.transmit = True
                app.placeOrder(new_id, mo.contract, mo.order_obj)
                mo.id = new_id
            else:
                print(f"Condition not met for order {error_id}. Will re-check in the next cycle.")

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
    if not hasattr(app, "executions_event"):
        app.executions_event = threading.Event()

    # Connection retry
    if not connect_with_retry(app, IBKR_HOST, IBKR_PORT, client_id_to_use, attempts=3):
        print("Failed to connect to IBKR after retries. Exiting.")
        return

    existing_orders = fetch_existing_orders(app)

    trigger_conid = get_trigger_conid_with_retry(app, attempts=3)
    if trigger_conid is None:
        print("Fatal Error: could not fetch SPX conId. Exiting.")
        app.disconnect(); return

    print("\n--------------------------")
    print("Looking for new signals...")
    signals = gather_signals()
    if not signals:
        print("No new signals found from any source. Exiting.")
        app.disconnect(); return

    managed_orders: List[ManagedOrder] = []
    for s in signals:
        print(f"Processing signal: {json.dumps(s.__dict__)}")
        try:
            lc_conid = get_option_conid_with_retry(app, s.expiry, s.lc_strike, "C", attempts=3)
            sc_conid = get_option_conid_with_retry(app, s.expiry, s.sc_strike, "C", attempts=3)
        except Exception as e:
            print(f"Could not get contract details for signal {s}. Skipping. Error: {e}")
            continue
        leg_ids = sorted([lc_conid, sc_conid])
        if is_duplicate(leg_ids, s.trigger_price, existing_orders):
            print(f"--> Duplicate order detected for {s.lc_strike}/{s.sc_strike} @ {s.trigger_price}. Skipping.")
            continue
        identifier = f"{UNDERLYING_SYMBOL}-{s.expiry}-{s.lc_strike}-{s.sc_strike}-{s.trigger_price}"
        sig_hash = get_signal_hash(identifier)
        contract = build_combo_contract(lc_conid, sc_conid)
        try:
            order = build_staged_order(s, trigger_conid)
        except Exception as e:
            print(f"Invalid order for {s}: {e}. Skipping.")
            continue
        mo = stage_order(app, s, contract, order, sig_hash)
        managed_orders.append(mo)

    if not managed_orders:
        print("No orders were staged (duplicates/invalid). Exiting.")
        app.disconnect(); return

    tz = pytz.timezone('US/Eastern')
    market_open_time = get_trading_day_open(tz, day_selection)
    market_close_time = market_open_time.replace(hour=16, minute=0, second=0, microsecond=0)

    print(f"Scheduled market open check for '{day_selection}' open: {market_open_time.strftime('%Y-%m-%d %H:%M:%S %Z')}")
    print(f"\nStaged {len(managed_orders)} order(s). Waiting for market open...")
    asyncio.run(wait_until_market_open(market_open_time, tz))

    open_px = fetch_open_price_with_retry(app, UNDERLYING_SYMBOL, attempts=5, wait_secs=10)
    if open_px is None:
        print(f"Could not get {UNDERLYING_SYMBOL} open price after retries. Please manually transmit orders.")
        app.disconnect(); return
    print(f"{UNDERLYING_SYMBOL} open price: {open_px}")

    managed_orders.sort(key=lambda x: x.trigger)
    process_managed_orders(app, managed_orders, UNDERLYING_SYMBOL)

    # Start SPX price stream only after market is open
    start_spx_stream(app, req_id_start=100, tries=3)

    # Post-place error retry loop
    run_error_retry_loop(app, managed_orders, market_close_time, tz)

    print("\nScript has completed its automated tasks.")
    app.cancelMktData(100)
    time.sleep(2)
    app.disconnect()

if __name__ == "__main__":
    main_loop()
