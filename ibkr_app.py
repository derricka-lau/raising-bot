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
    REQID_CONTRACT_DETAILS_IND = 10
    REQID_CONTRACT_DETAILS_OPT = 11

    def __init__(self):
        EClient.__init__(self, self)
        self.nextOrderId = None
        self.underlying_open_price = None
        self.current_spx_price = None
        self.lastConId = None
        self.open_orders = []
        self.nextReqId = 1
        # --- Add threading events for synchronization ---
        self.connected_event = threading.Event()
        self.open_orders_event = threading.Event()
        self.historical_data_event = threading.Event()
        self.contract_details_event = threading.Event()
        self.order_status_event = threading.Event()
        self.error_order_ids = []
        # --- Add these fields for countdown ---
        self.market_close_time = None
        self.tz = None

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

    def get_spx_index_conid(self):
        """Fetches the contract ID for the SPX index."""
        contract = Contract()
        contract.symbol = "SPX"
        contract.secType = "IND"
        contract.exchange = "CBOE"
        contract.currency = "USD"
        self.lastConId = None
        self.contract_details_event.clear()
        self.reqContractDetails(10, contract)
        self.contract_details_event.wait(5) # Wait up to 5 seconds
        if not self.lastConId:
            raise Exception("Failed to get SPX Index conId.")
        return self.lastConId

    def get_spx_option_conid(self, expiry, strike, right):
        contract = Contract()
        contract.symbol = "SPX"
        contract.secType = "OPT"
        contract.exchange = "SMART"
        contract.currency = "USD"
        contract.lastTradeDateOrContractMonth = expiry
        contract.strike = float(strike)
        contract.right = right
        contract.multiplier = "100"
        self.lastConId = None
        self.contract_details_event.clear()
        self.reqContractDetails(11, contract)  # <-- Use a fixed reqId here
        self.contract_details_event.wait(5) # Wait up to 5 seconds
        if not self.lastConId:
            raise Exception(f"Failed to get option conId for {strike} {right}.")
        return self.lastConId

    def contractDetails(self, reqId, contractDetails):
        super().contractDetails(reqId, contractDetails)
        self.lastConId = contractDetails.contract.conId
        self.contract_details_event.set() # Signal that contract details have arrived

    def contractDetailsEnd(self, reqId: int):
        super().contractDetailsEnd(reqId)
        self.contract_details_event.set() # Also signal on end in case no details found

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

    def get_new_reqid(self):
        reqid = self.nextReqId
        self.nextReqId += 1
        return reqid
