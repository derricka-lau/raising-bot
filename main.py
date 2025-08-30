# main.py

import threading
import time

from flask import app
import print_utils
from datetime import datetime, timedelta
import pytz
import asyncio
import argparse # 1. Import argparse
import json
from dataclasses import dataclass
from typing import List, Optional, Tuple

from config import (IBKR_HOST, IBKR_PORT, IBKR_CLIENT_ID, 
                    UNDERLYING_SYMBOL, IBKR_ACCOUNT, SNAPMID_OFFSET, WAIT_AFTER_OPEN_SECONDS)
from signal_utils import (Signal, gather_signals, get_signal_hash)
from ibkr_app import IBKRApp

from ibapi.contract import ComboLeg, Contract
from ibapi.order import Order
from ibapi.order_condition import Create, OrderCondition
from ibapi.execution import ExecutionFilter
@dataclass
class ManagedOrder:
    id: int
    trigger: float
    lc_strike: float
    sc_strike: float
    contract: Contract
    order_obj: Order
    hash: str

failed_conid_signals = []  # <-- Add here, after imports

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

def is_duplicate_order(leg_ids, trigger_price, existing_orders, managed_orders):
    """
    Checks if an order with the given leg_ids and trigger_price exists in existing_orders or managed_orders.
    """
    # Check existing TWS orders
    for order in existing_orders:
        if (order.get("secType") == "BAG" and
            tuple(order.get("leg_conIds", [])) == tuple(leg_ids) and
            order.get("trigger_price") == trigger_price):
            return True
    # Check managed orders in current session
    for mo in managed_orders:
        mo_leg_ids = sorted([leg.conId for leg in mo.contract.comboLegs])
        if tuple(mo_leg_ids) == tuple(leg_ids) and mo.trigger == trigger_price:
            return True
    return False

def connect_with_retry(app, host, port, client_id, attempts=3):
    for i in range(1, attempts + 1):
        try:
            app.connect(host, port, client_id)
            api_thread = threading.Thread(target=app.run, daemon=True)
            api_thread.start()
            print(f"Connecting to IBKR... (attempt {i}/{attempts})", flush=True)
            if app.connected_event.wait(10) and app.nextOrderId:
                print(f"Successfully connected. Next Order ID: {app.nextOrderId}")
                return True
            print("Connection wait timed out or no OrderId.", flush=True)
        except Exception as e:
            print(f"Connect error: {e}", flush=True)
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
        hours, remainder = divmod(int(seconds_left), 3600)
        mins, secs = divmod(remainder, 60)
        print(f"Waiting for market open: {hours:02d}:{mins:02d}:{secs:02d} remaining...", flush=True)
        await asyncio.sleep(1)
    print("Market is open!", flush=True)

def process_managed_orders(app, managed_orders, underlying_symbol):
    """
    Processes managed orders by comparing open price to trigger and transmitting/cancelling as needed.
    """
    for order_info in managed_orders:
        if app.underlying_open_price >= order_info.trigger:
            print(f"!! NO-GO for Order {order_info.id} !! {underlying_symbol} open ({app.underlying_open_price}) >= trigger ({order_info.trigger}). CANCELLING.", flush=True)
            app.cancelOrder(order_info.id)
        else:
            print(f"** GO for Order {order_info.id}! ** Open price ({app.underlying_open_price}) is favorable. TRANSMITTING.", flush=True)
            final_order = order_info.order_obj
            final_order.transmit = True
            app.placeOrder(order_info.id, order_info.contract, final_order)

def fetch_existing_orders(app: IBKRApp) -> List[dict]:
    """Fetches only the currently open orders."""
    print("Requesting open orders...", flush=True)
    ok = request_with_retry(lambda: app.reqAllOpenOrders(), app.open_orders_event, attempts=3, wait_secs=8, desc="Open orders")
    if not ok:
        print("Failed to fetch open orders after retries. Continuing with empty set.", flush=True)

    open_orders = app.open_orders
    print(f"Found {len(open_orders)} open SPX order(s).", flush=True)
    return open_orders

def get_trigger_conid_with_retry(app: IBKRApp, attempts: int = 3) -> Optional[int]:
    trigger_conid = None
    for i in range(1, attempts + 1):
        try:
            trigger_conid = app.get_spx_index_conid()
            print(f"Successfully fetched current SPX Index conId: {trigger_conid}", flush=True)
            return trigger_conid
        except Exception as e:
            print(f"Fetch SPX conId failed (attempt {i}/{attempts}): {e}", flush=True)
            time.sleep(1.5 * i)
    return None

def start_spx_stream(app: IBKRApp, req_id_start: int = 100, tries: int = 3) -> None:
    print("Starting live SPX price stream...", flush=True)
    spx = Contract(); spx.symbol="SPX"; spx.secType="IND"; spx.exchange="CBOE"; spx.currency="USD"
    for i in range(tries):
        req_id = req_id_start + i  # Use a different req_id each time
        app.reqMktData(req_id, spx, "", False, False, [])
        time.sleep(1.5 * (i + 1))
        if app.current_spx_price is not None:
            break
        print(f"SPX live price not yet available (attempt {i+1}/{tries}). Retrying stream request...", flush=True)

def get_option_conid_with_retry(app: IBKRApp, expiry: str, strike: float, right: str, attempts: int = 3) -> int:
    print(f"Fetching option conId for {expiry} {strike}{right}...", flush=True)
    last_err: Optional[Exception] = None
    for i in range(1, attempts + 1):
        try:
            return app.get_spx_option_conid(expiry, strike, right)
        except Exception as e:
            last_err = e
            print(f"get_conid failed for {expiry} {strike}{right} (attempt {i}/{attempts}): {e}", flush=True)
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
    print(f"--> Staged Order {order_id} for {UNDERLYING_SYMBOL} ({order.orderType}) with trigger at {signal.trigger_price} for review.", flush=True)
    return ManagedOrder(
        id=order_id,
        trigger=signal.trigger_price,
        lc_strike=signal.lc_strike,
        sc_strike=signal.sc_strike,
        contract=contract,
        order_obj=order,
        hash=signal_hash,
    )

def process_and_stage_new_signals(app: IBKRApp, signals: List[Signal], managed_orders: List[ManagedOrder], existing_orders: List[dict], trigger_conid: int):
    """
    Processes a new batch of signals, checks for duplicates against all known orders (API + current session),
    and stages valid new orders. Appends new ManagedOrder objects to the managed_orders list.
    """
    if not signals:
        return

    for s in signals:
        print(f"Processing signal: {json.dumps(s.__dict__)}", flush=True)
        try:
            lc_conid = get_option_conid_with_retry(app, s.expiry, s.lc_strike, "C", attempts=3)
            sc_conid = get_option_conid_with_retry(app, s.expiry, s.sc_strike, "C", attempts=3)
            
            leg_ids = sorted([lc_conid, sc_conid])
            if is_duplicate_order(leg_ids, s.trigger_price, existing_orders, managed_orders):
                print(f"--> Duplicate order detected for {s.lc_strike}/{s.sc_strike} @ {s.trigger_price}. Skipping.", flush=True)
                continue

            identifier = f"{UNDERLYING_SYMBOL}-{s.expiry}-{s.lc_strike}-{s.sc_strike}-{s.trigger_price}"
            sig_hash = get_signal_hash(identifier)
            contract = build_combo_contract(lc_conid, sc_conid)
            order = build_staged_order(s, trigger_conid)
            
            # Stage the order and add it to our managed list
            mo = stage_order(app, s, contract, order, sig_hash)
            managed_orders.append(mo)

        except Exception as e:
            print(f"Could not process or stage signal {s}. Adding to failed conId signals to retry later. Error: {e}", flush=True)
            signal_key = (s.expiry, s.lc_strike, s.sc_strike, s.trigger_price)
            if signal_key not in { (fs.expiry, fs.lc_strike, fs.sc_strike, fs.trigger_price) for fs, _ in failed_conid_signals }:
                failed_conid_signals.append((s, s.expiry))
            else:
                print(f"Signal {s} already in failed conId list. Skipping duplicate addition.", flush=True)
            continue

def fetch_open_price_with_retry(app: IBKRApp, symbol: str, attempts: int = 5, wait_secs: int = 3) -> Optional[float]:
    underlying_contract = Contract(); underlying_contract.symbol = symbol; underlying_contract.secType = "IND"; underlying_contract.currency = "USD"; underlying_contract.exchange = "CBOE"
    for i in range(1, attempts + 1):
        app.underlying_open_price = None
        app.historical_data_event.clear()
        print(f"Attempt {i}/{attempts} to fetch {symbol} open price...", flush=True)
        app.reqHistoricalData(99, underlying_contract, "", "1 D", "1 day", "TRADES", 1, 1, False, [])
        got = app.historical_data_event.wait(wait_secs)
        if app.underlying_open_price is not None and got:
            return app.underlying_open_price
    return None

def run_post_open_retry_loops(app, managed_orders, failed_conid_signals, trigger_conid, market_close_time, tz, existing_orders):
    while datetime.now(tz) < market_close_time and (app.error_order_ids or failed_conid_signals):
        live_price = app.current_spx_price

        # Gather all LC strikes from error orders and failed conid signals
        error_lc_strikes = [mo.lc_strike for mo in managed_orders if mo.id in app.error_order_ids]
        failed_lc_strikes = [signal.lc_strike for signal, _ in failed_conid_signals]
        all_lc_strikes = error_lc_strikes + failed_lc_strikes

        if not all_lc_strikes or live_price is None:
            # Nothing actionable or no price yet
            now = time.time()
            if now - last_status_print > 30:
                print("Waiting for SPX live price or actionable signals...", flush=True)
                last_status_print = now
            time.sleep(1)
            continue

        lowest_lc_strike = min(all_lc_strikes)

        if live_price >= lowest_lc_strike:
            # Live price is above the lowest LC strike, we can act on it
            print(f"Live price {live_price} is above lowest LC strike {lowest_lc_strike}.", flush=True)
            # --- Error order retry ---
            if app.error_order_ids:
                print(f"Critical error(s) detected for order IDs: {app.error_order_ids}. Retrying...", flush=True)
                for error_id in list(app.error_order_ids):
                    matches = [m for m in managed_orders if m.id == error_id]
                    if not matches:
                        print(f"Order ID {error_id} seems resolved. Removing from error list.", flush=True)
                        app.error_order_ids.remove(error_id)
                        continue
                    mo = matches[0]
                    live_price = app.current_spx_price
                    if live_price is None:
                        print("Live SPX price not available yet. Waiting...", flush=True)
                        continue
                    print(f"Checking retry condition for order {error_id}: Live={live_price}, LC={mo.lc_strike}", flush=True)
                    if live_price >= mo.lc_strike:
                        print(f"Condition met. Retrying order {error_id}...", flush=True)
                        new_id = app.nextOrderId
                        app.nextOrderId += 1
                        mo.order_obj.transmit = True
                        app.placeOrder(new_id, mo.contract, mo.order_obj)
                        mo.id = new_id
                    else:
                        print(f"Condition not met for order {error_id}. Will re-check in the next cycle.", flush=True)

            # --- Failed conId retry ---
            if failed_conid_signals:
                print(f"Retrying failed conId signals: {len(failed_conid_signals)} remaining.", flush=True)
                for idx, (signal, expiry) in enumerate(list(failed_conid_signals)):
                    live_price = app.current_spx_price
                    if live_price is None:
                        print("Live SPX price not available yet. Waiting...", flush=True)
                        continue
                    print(f"Checking retry for signal {signal}: Live={live_price}, LC={signal.lc_strike}", flush=True)
                    if live_price >= signal.lc_strike:
                        try:
                            try:
                                lc_conid = get_option_conid_with_retry(app, expiry, signal.lc_strike, "C", attempts=3)
                            except Exception as e:
                                print(f"LC conId fetch failed for {signal.lc_strike}. Trying LC strike -5...", flush=True)
                                lc_conid = get_option_conid_with_retry(app, expiry, signal.lc_strike - 5, "C", attempts=3)
                            try:
                                sc_conid = get_option_conid_with_retry(app, expiry, signal.sc_strike, "C", attempts=3)
                            except Exception as e:
                                print(f"SC conId fetch failed for {signal.sc_strike}. Trying SC strike +5...", flush=True)
                                sc_conid = get_option_conid_with_retry(app, expiry, signal.sc_strike + 5, "C", attempts=3)

                            leg_ids = sorted([lc_conid, sc_conid])
                            # Check for duplicates before placing order
                            if is_duplicate_order(leg_ids, signal.trigger_price, existing_orders, managed_orders):
                                print(f"--> Duplicate order detected for {signal.lc_strike}/{signal.sc_strike} @ {signal.trigger_price}. Skipping.", flush=True)
                                failed_conid_signals.pop(idx)
                                continue
                            contract = build_combo_contract(lc_conid, sc_conid)
                            order = build_staged_order(signal, trigger_conid)
                            order.transmit = True  # <-- Make order live immediately
                            order_id = app.nextOrderId
                            app.nextOrderId += 1
                            app.placeOrder(order_id, contract, order)
                            print(f"Successfully submitted LIVE order for signal {signal} after retry.", flush=True)
                            failed_conid_signals.pop(idx)
                        except Exception as e:
                            print(f"Retry failed for signal {signal}: {e}", flush=True)
                    else:
                        print(f"Condition not met for signal {signal}. Will re-check in the next cycle.", flush=True)
        time.sleep(1)
    print("Post-open retry loops concluded (either market close reached or no pending issues).", flush=True)

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
    client_id_to_use = args.client_id if args.client_id is not None else IBKR_CLIENT_ID

    while True:  # <-- This keeps your bot running 24/7
        app = IBKRApp()
        app.tz = pytz.timezone('US/Eastern')
        if not hasattr(app, "executions_event"):
            app.executions_event = threading.Event()

        print("Attempting to connect to IBKR...", flush=True)
        if not connect_with_retry(app, IBKR_HOST, IBKR_PORT, client_id_to_use, attempts=5):
            print("Connection failed after multiple retries. Will try again in 5 minutes.", flush=True)
            time.sleep(300)
            continue # Restart the connection loop

        try:
            existing_orders = fetch_existing_orders(app)

            if existing_orders:
                # Find the highest ID among all open/filled orders fetched
                max_existing_id = max(order.get("orderId", 0) for order in existing_orders)
                
                # If the highest existing ID is greater than what the API suggested, update it.
                if max_existing_id >= app.nextOrderId:
                    new_next_id = max_existing_id + 1
                    print(f"Adjusting nextOrderId. API gave {app.nextOrderId}, but max existing is {max_existing_id}. Setting next ID to {new_next_id}.", flush=True)
                    app.nextOrderId = new_next_id

            trigger_conid = get_trigger_conid_with_retry(app, attempts=3)
            if trigger_conid is None:
                print("Fatal Error: could not fetch SPX conId. Exiting.")
                app.disconnect(); return

            # Sleep to wait for any async data to settle
            time.sleep(5)
            print("--------------------------", flush=True)
            print("Looking for new signals...", flush=True)
            signals = gather_signals(allow_manual_fallback=True)

            managed_orders: List[ManagedOrder] = []
            process_and_stage_new_signals(app, signals, managed_orders, existing_orders, trigger_conid)

            market_open_time = get_trading_day_open(app.tz, day_selection)
            app.market_close_time = market_open_time.replace(hour=16, minute=0, second=0, microsecond=0)
            print(f"Scheduled market open check for '{day_selection}' open: {market_open_time.strftime('%Y-%m-%d %H:%M:%S %Z')}", flush=True)
            print(f"Staged {len(managed_orders)} order(s). Waiting for market open...", flush=True)
            time.sleep(2)  # Give some time for the app to settle
            asyncio.run(wait_until_market_open(market_open_time, app.tz))

            # Wait WAIT_AFTER_OPEN_SECONDS second(s) after market open for IBKR to publish the open bar
            print(f"Waiting {WAIT_AFTER_OPEN_SECONDS} second(s) after market open for IBKR to publish the official open price...", flush=True)
            time.sleep(int(WAIT_AFTER_OPEN_SECONDS))

            open_px = fetch_open_price_with_retry(app, UNDERLYING_SYMBOL, attempts=5, wait_secs=3)
            if open_px is None:
                print(f"Could not get {UNDERLYING_SYMBOL} open price after retries. Please manually transmit orders.", flush=True)
                app.disconnect(); return
            print(f"{UNDERLYING_SYMBOL} open price: {open_px}", flush=True)

            managed_orders.sort(key=lambda x: x.trigger)
            process_managed_orders(app, managed_orders, UNDERLYING_SYMBOL)

            # Start SPX price stream only after market is open
            start_spx_stream(app, req_id_start=100, tries=3)

            # --- Post-open signal checks at 9:31 ---
            print("--- Entering post-open signal monitoring phase ---", flush=True)

            # Wait until 9:32:00
            wait_time_931 = market_open_time.replace(minute=32, second=0)
            print(f"Waiting until {wait_time_931.strftime('%H:%M:%S %Z')} to check for new signals...", flush=True)
            time.sleep(max(0, (wait_time_931 - datetime.now(app.tz)).total_seconds()))

            print("--- 9:32:00 AM: Fetching new signals... ---", flush=True)
            signals_932 = gather_signals(allow_manual_fallback=False)
            if not signals_932:
                print("No signals found at 9:32:00. If you need to manually enter any signal again, please stop and rerun the bot.", flush=True)
            else:
                print(f"Found {len(signals_932)} signal(s) at 9:32:00.", flush=True)
            process_and_stage_new_signals(app, signals_932, managed_orders, existing_orders, trigger_conid)
            print("--- Post-open signal checks complete. Monitoring for errors. ---", flush=True)

            # Post-place error retry loop
            run_post_open_retry_loops(app, managed_orders, failed_conid_signals, trigger_conid, app.market_close_time, app.tz, existing_orders)

            # If the script completes normally, we can break the loop.
            print("Script has completed its automated tasks.", flush=True)

            while datetime.now(app.tz) < app.market_close_time:
                time.sleep(60)

            print("Market close reached. Sleeping until next trading day...", flush=True)
            app.disconnect()  # <-- Disconnect from IBKR after market close
            now = datetime.now(app.tz)
            # Calculate next 5AM US/Eastern
            next_5am = (now + timedelta(days=1)).replace(hour=5, minute=0, second=0, microsecond=0)
            sleep_seconds = (next_5am - now).total_seconds()
            print(f"Sleeping for {int(sleep_seconds)} seconds until {next_5am.strftime('%Y-%m-%d %H:%M:%S %Z')}", flush=True)
            time.sleep(max(1, sleep_seconds))
            print("Waking up for new trading day.", flush=True)
            # The loop will restart and run the next day's logic

        except Exception as e:
            print(f"An error occurred in the main processing loop: {e}", flush=True)
            time.sleep(60)  # Wait before retrying the whole process

    # app.cancelMktData(100)
    # time.sleep(2)
    # app.disconnect()

if __name__ == "__main__":
    main_loop()
