# ibkr_app.py

import threading
from datetime import datetime
from ibapi.client import EClient
from ibapi.wrapper import EWrapper
from ibapi.contract import Contract
from ibapi.order_condition import PriceCondition

class IBKRApp(EWrapper, EClient):
    # Define constants for request IDs
    REQID_HISTORICAL_OPEN = 99
    REQID_SPX_STREAM = 100
    # Removed REQID constants for contract details as they are now dynamic

    def __init__(self):
        EClient.__init__(self, self)
        self.nextOrderId = None
        self.underlying_open_price = None
        self.current_spx_price = None
        
        # --- NEW: Thread-safe request ID generation and result storage ---
        self.nextReqId = 1
        self.req_id_lock = threading.Lock()
        self.contract_details_results = {}
        self.contract_details_events = {}
        
        # --- Threading events for synchronization ---
        self.connected_event = threading.Event()
        self.open_orders_event = threading.Event()
        self.historical_data_event = threading.Event()
        self.order_status_event = threading.Event()
        
        self.open_orders = []
        self.error_order_ids = []
        # --- Add these fields for countdown ---
        self.market_close_time = None
        self.tz = None
        self.conid_to_strike = {}
        self.conid_to_expiry = {}

    def get_new_reqid(self):
        """Generates a new, unique, thread-safe request ID."""
        with self.req_id_lock:
            reqid = self.nextReqId
            self.nextReqId += 1
            return reqid

    def nextValidId(self, orderId: int):
        super().nextValidId(orderId)
        self.nextOrderId = orderId
        self.connected_event.set() # Signal that connection is complete

    def error(self, reqId, errorCode, errorString):
        # Informational codes
        info_codes = [2104, 2106, 2158, 162, 2107, 2108, 2110, 2111, 2112, 2113, 2114]
        if errorCode in info_codes:
            print(f"IBKR INFO: reqId {reqId}, Code {errorCode} - {errorString}", flush=True)
            return
        if errorCode == 202:
            print(f"Order cancellation confirmed for reqId {reqId}.", flush=True)
        # For contract detail errors, signal the event to unblock the waiting thread
        if reqId in self.contract_details_events:
            self.contract_details_events[reqId].set()
        print(f"IBKR Log: reqId {reqId}, Code {errorCode} - {errorString}", flush=True)

    def tickPrice(self, reqId, tickType, price, attrib):
        """Callback for streaming market data."""
        super().tickPrice(reqId, tickType, price, attrib)
        # tickType 4 is 'LAST_PRICE'
        if reqId == 100 and tickType == 4: # Use a dedicated reqId for the SPX stream
            self.current_spx_price = price
            if hasattr(self, "market_close_time") and hasattr(self, "tz"):
                now = datetime.now(self.tz)
                seconds_left = int((self.market_close_time - now).total_seconds())
                if seconds_left > 0:
                    hours, remainder = divmod(seconds_left, 3600)
                    mins, secs = divmod(remainder, 60)
                    print(f"Live SPX Price: {self.current_spx_price} | Market Close Countdown: {hours:02d}:{mins:02d}:{secs:02d}", flush=True)
                else:
                    print(f"Live SPX Price: {self.current_spx_price} | Market closed | Countdown: 00:00:00", flush=True)
            else:
                print(f"Live SPX Price: {self.current_spx_price}", flush=True)

    def historicalData(self, reqId, bar):
        if reqId == self.REQID_HISTORICAL_OPEN:
            self.underlying_open_price = bar.open
            print(f"Received historical data: Open={bar.open}", flush=True)
            self.historical_data_event.set() # Signal that data has arrived

    def historicalDataEnd(self, reqId: int, start: str, end: str):
        super().historicalDataEnd(reqId, start, end)
        if not self.underlying_open_price:
            print("Historical data request finished but no data was received.", flush=True)
            self.historical_data_event.set() # Unblock the wait even if there's no data

    def get_contract_details(self, contract: Contract, timeout=7) -> int:
        """
        Fetches contract details for a given contract object in a thread-safe manner.
        Returns the conId.
        """
        req_id = self.get_new_reqid()
        self.contract_details_events[req_id] = threading.Event()
        self.contract_details_results[req_id] = None

        print(f"Requesting contract details with reqId {req_id}...", flush=True)
        self.reqContractDetails(req_id, contract)

        event_triggered = self.contract_details_events[req_id].wait(timeout)

        details = self.contract_details_results.pop(req_id, None)
        del self.contract_details_events[req_id]

        if not event_triggered:
            raise Exception(f"Request for {contract.symbol} details timed out.")
        if not details:
            raise Exception(f"Failed to get contract details for {contract.symbol} {getattr(contract, 'strike', '')} {getattr(contract, 'right', '')}. No details found.")
        
        return details.contract.conId

    def contractDetails(self, reqId, contractDetails):
        super().contractDetails(reqId, contractDetails)
        # If this reqId is one we are waiting for, store the result
        if reqId in self.contract_details_results:
            self.contract_details_results[reqId] = contractDetails
        
        # Also update our general-purpose mappings
        conId = contractDetails.contract.conId
        self.conid_to_strike[conId] = contractDetails.contract.strike
        self.conid_to_expiry[conId] = contractDetails.contract.lastTradeDateOrContractMonth

    def contractDetailsEnd(self, reqId: int):
        super().contractDetailsEnd(reqId)
        # If this reqId is one we are waiting for, signal its event to unblock it
        if reqId in self.contract_details_events:
            self.contract_details_events[reqId].set()

    def openOrder(self, orderId, contract, order, orderState):
        super().openOrder(orderId, contract, order, orderState)
        order_info = {
            "orderId": orderId,
            "symbol": contract.symbol,
            "secType": contract.secType,
            "order_type": order.orderType,
            "leg_conIds": [],
            "trigger_price": None,
            "transmit": getattr(order, "transmit", None),  # <-- ADD THIS LINE
        }
        if contract.secType == 'BAG' and contract.comboLegs:
            order_info["leg_conIds"] = sorted([leg.conId for leg in contract.comboLegs])
        for cond in order.conditions:
            if isinstance(cond, PriceCondition):
                order_info["trigger_price"] = cond.price
        self.open_orders.append(order_info)

    def openOrderEnd(self):
        super().openOrderEnd()
        print("Finished receiving open orders.", flush=True)
        self.open_orders_event.set() # Signal that all open orders have been received

    def orderStatus(self, orderId, status, filled, remaining, avgFillPrice, permId, parentId, lastFillPrice, clientId, whyHeld, mktCapPrice):
        super().orderStatus(orderId, status, filled, remaining, avgFillPrice, permId, parentId, lastFillPrice, clientId, whyHeld, mktCapPrice)
        print(f"OrderStatus. ID: {orderId}, Status: {status}, Filled: {filled}, Remaining: {remaining}, AvgFillPrice: {avgFillPrice}", flush=True)
        # Set the event when all orders are processed
        if status in ("Filled", "Cancelled", "Inactive", "Rejected"):
            self.order_status_event.set()
        if status == "Inactive":
            if orderId not in self.error_order_ids:
                self.error_order_ids.append(orderId)

    def fetch_contract_details_for_conids(self, conid_list):
        """
        Given a list of conIds, fetch contract details and update mappings.
        """
        for conid in set(conid_list):
            if conid in self.conid_to_strike:  # Skip if we already have it
                continue
            contract = Contract()
            contract.conId = conid
            try:
                # This call will populate the conid_to_strike/expiry maps via the callback
                self.get_contract_details(contract)
            except Exception as e:
                print(f"Could not fetch details for conId {conid}: {e}", flush=True)
        
        # Return copies of the mappings
        return dict(self.conid_to_strike), dict(self.conid_to_expiry)
