# ibkr_app.py

import threading
from ibapi.client import EClient
from ibapi.wrapper import EWrapper
from ibapi.contract import Contract
from ibapi.order_condition import PriceCondition

class IBKRApp(EWrapper, EClient):
    def __init__(self):
        EClient.__init__(self, self)
        self.nextOrderId = None
        self.underlying_open_price = None
        self.current_spx_price = None # <-- ADD THIS: For the live price
        self.lastConId = None
        self.open_orders = []
        self.filled_orders = []  # <-- add this
        self.nextReqId = 1  # Start from 1 or any number
        # --- Add threading events for synchronization ---
        self.connected_event = threading.Event()
        self.open_orders_event = threading.Event()
        self.historical_data_event = threading.Event()
        self.contract_details_event = threading.Event()
        self.order_status_event = threading.Event()
        self.error_order_ids = []

    def nextValidId(self, orderId: int):
        super().nextValidId(orderId)
        self.nextOrderId = orderId
        self.connected_event.set() # Signal that connection is complete

    def error(self, reqId, errorCode, errorString):
        print(f"IBKR ERROR: reqId {reqId}, Code {errorCode} - {errorString}")
        # Error codes for completed data requests
        if errorCode == 162: # Historical data farm is connected
            return # Ignore this informational message
        if reqId > -1 and errorCode in [2104, 2106, 2158]: # Market data connection OK
            return # Ignore informational messages
        if errorCode == 202: # Order Canceled
            print(f"Order cancellation confirmed for reqId {reqId}.")

    def tickPrice(self, reqId, tickType, price, attrib):
        """Callback for streaming market data."""
        super().tickPrice(reqId, tickType, price, attrib)
        # tickType 4 is 'LAST_PRICE'
        if reqId == 100 and tickType == 4: # Use a dedicated reqId for the SPX stream
            self.current_spx_price = price
            print(f"\rLive SPX Price: {self.current_spx_price}", end="", flush=True)

    def historicalData(self, reqId, bar):
        if reqId == 99:
            self.underlying_open_price = bar.open
            print(f"Received historical data: Open={bar.open}")
            self.historical_data_event.set() # Signal that data has arrived

    def historicalDataEnd(self, reqId: int, start: str, end: str):
        super().historicalDataEnd(reqId, start, end)
        if not self.underlying_open_price:
            print("Historical data request finished but no data was received.")
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
        # Store key info for duplicate checking
        order_info = {
            "orderId": orderId,
            "symbol": contract.symbol,
            "secType": contract.secType,
            "order_type": order.orderType,
            "leg_conIds": [], # We will store conIds instead of strikes
            "trigger_price": None
        }
        if contract.secType == 'BAG' and contract.comboLegs:
            # CORRECTED: Get conIds from legs, as strike/right are not populated here.
            order_info["leg_conIds"] = sorted([leg.conId for leg in contract.comboLegs])
        
        for cond in order.conditions:
            # Check if it's a price condition before accessing price
            if isinstance(cond, PriceCondition):
                order_info["trigger_price"] = cond.price

        self.open_orders.append(order_info)

    def openOrderEnd(self):
        super().openOrderEnd()
        print("Finished receiving open orders.")
        self.open_orders_event.set() # Signal that all open orders have been received

    def orderStatus(self, orderId, status, filled, remaining, avgFillPrice, permId, parentId, lastFillPrice, clientId, whyHeld, mktCapPrice):
        super().orderStatus(orderId, status, filled, remaining, avgFillPrice, permId, parentId, lastFillPrice, clientId, whyHeld, mktCapPrice)
        print(f"OrderStatus. ID: {orderId}, Status: {status}, Filled: {filled}, Remaining: {remaining}, AvgFillPrice: {avgFillPrice}")
        # Set the event when all orders are processed
        if status in ("Filled", "Cancelled", "Inactive", "Rejected"):
            self.order_status_event.set()
        if status == "Inactive":
            if orderId not in self.error_order_ids:
                self.error_order_ids.append(orderId)

    def execDetails(self, reqId, contract, execution):
        # This is called for each filled order
        order_info = {
            "orderId": execution.orderId,
            "symbol": contract.symbol,
            "secType": contract.secType,
            "conId": contract.conId,
            "price": execution.price,
            # Add more fields as needed
        }
        self.filled_orders.append(order_info)

    def execDetailsEnd(self, reqId):
        """Called when all execution details have been received."""
        super().execDetailsEnd(reqId)
        print("Finished receiving executions.")
        self.executions_event.set() # <-- ADD THIS

    def get_new_reqid(self):
        reqid = self.nextReqId
        self.nextReqId += 1
        return reqid
