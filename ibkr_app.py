# ibkr_app.py

from ibapi.client import EClient
from ibapi.wrapper import EWrapper
from ibapi.contract import Contract
import time

class IBKRApp(EWrapper, EClient):
    def __init__(self):
        EClient.__init__(self, self)
        self.nextOrderId = None
        self.underlying_open_price = None
        self.lastConId = None  # Add this

    def nextValidId(self, orderId: int): self.nextOrderId = orderId
    def error(self, reqId, errorCode, errorString):
        print(f"IBKR ERROR: {errorCode} - {errorString}")

    def historicalData(self, reqId, bar):
        if reqId == 99: self.underlying_open_price = bar.open

    def get_spx_index_conid(self):
        """Fetches the contract ID for the SPX index."""
        contract = Contract()
        contract.symbol = "SPX"
        contract.secType = "IND"
        contract.exchange = "CBOE"
        contract.currency = "USD"
        self.lastConId = None
        self.reqContractDetails(1002, contract) # Use a different reqId
        # Wait for callback
        for _ in range(20):
            if self.lastConId:
                return self.lastConId
            time.sleep(0.2)
        raise Exception("Could not fetch conId for SPX index.")

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
        self.reqContractDetails(1001, contract)
        # Wait for callback (simple blocking for demo)
        for _ in range(20):
            if self.lastConId:
                return self.lastConId
            time.sleep(0.2)
        raise Exception("Could not fetch conId for SPX option.")

    def contractDetails(self, reqId, contractDetails):
        self.lastConId = contractDetails.contract.conId
        print(f"ContractDetails for reqId {reqId}: conId={self.lastConId}")

    def openOrder(self, orderId, contract, order, orderState):
        print(f"Open Order: ID={orderId}, Symbol={contract.symbol}, Type={order.orderType}, Status={orderState.status}, LmtPrice={order.lmtPrice}, AuxPrice={order.auxPrice}")

    def orderStatus(self, orderId, status, filled, remaining, avgFillPrice, permId, parentId, lastFillPrice, clientId, whyHeld, mktCapPrice):
        print(f"Order Status: ID={orderId}, Status={status}, Filled={filled}, Remaining={remaining}, AvgFillPrice={avgFillPrice}")
