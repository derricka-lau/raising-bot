# tests/test_ibkr_app.py
import unittest
import threading
import time
from unittest.mock import MagicMock, patch, call
from ibapi.contract import Contract
from ibapi.order_condition import PriceCondition, OrderCondition
from ibkr_app import IBKRApp


class TestIBKRAppInitialization(unittest.TestCase):
    """Test that IBKRApp initializes correctly with all necessary thread-safe components."""

    def setUp(self):
        self.app = IBKRApp()

    def test_initialization(self):
        """Verify IBKRApp has required attributes including thread-safe lock and per-request dictionaries."""
        self.assertIsNotNone(self.app.nextReqId)
        self.assertEqual(self.app.nextReqId, 1)
        self.assertIsNotNone(self.app.req_id_lock)
        # Use duck-typing instead of isinstance for cross-version compatibility
        self.assertTrue(hasattr(self.app.req_id_lock, 'acquire'))
        self.assertTrue(hasattr(self.app.req_id_lock, 'release'))
        self.assertIsInstance(self.app.contract_details_results, dict)
        self.assertIsInstance(self.app.contract_details_events, dict)
        self.assertIsInstance(self.app.conid_to_strike, dict)
        self.assertIsInstance(self.app.conid_to_expiry, dict)

    def test_get_new_reqid_thread_safety(self):
        """Test that get_new_reqid generates unique IDs even under concurrent access."""
        num_threads = 500
        req_ids = []
        req_ids_lock = threading.Lock()

        def worker():
            req_id = self.app.get_new_reqid()
            with req_ids_lock:
                req_ids.append(req_id)

        threads = [threading.Thread(target=worker) for _ in range(num_threads)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # All IDs should be unique
        self.assertEqual(len(req_ids), num_threads)
        self.assertEqual(len(set(req_ids)), num_threads)

    def test_get_new_reqid_increments(self):
        """Test that get_new_reqid increments correctly in sequence."""
        first_id = self.app.get_new_reqid()
        second_id = self.app.get_new_reqid()
        third_id = self.app.get_new_reqid()
        self.assertEqual(first_id, 1)
        self.assertEqual(second_id, 2)
        self.assertEqual(third_id, 3)


class TestContractDetailsThreadSafety(unittest.TestCase):
    """Test thread-safe contract details fetching under concurrent requests."""

    def setUp(self):
        self.app = IBKRApp()

    def test_multiple_concurrent_requests(self):
        """Test that concurrent contract detail requests get unique request IDs and isolated results."""
        num_requests = 10
        results = []
        results_lock = threading.Lock()

        def mock_req_contract_details(req_id, contract):
            # Simulate async callback
            def callback():
                time.sleep(0.01)
                from ibapi.contract import ContractDetails
                details = MagicMock(spec=ContractDetails)
                details.contract = MagicMock(spec=Contract)
                details.contract.conId = 1000 + req_id  # Unique per request
                details.contract.strike = 5900.0 + req_id
                details.contract.lastTradeDateOrContractMonth = "20251231"
                self.app.contractDetails(req_id, details)
                self.app.contractDetailsEnd(req_id)
            
            threading.Thread(target=callback).start()

        self.app.reqContractDetails = mock_req_contract_details

        def worker(index):
            try:
                contract = Contract()
                contract.symbol = "SPX"
                contract.secType = "OPT"
                conid = self.app.get_contract_details(contract, timeout=2)
                with results_lock:
                    results.append(conid)
            except Exception as e:
                with results_lock:
                    results.append(None)

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(num_requests)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # Should have all results
        self.assertEqual(len(results), num_requests)
        # All should be successful (no None values from exceptions)
        self.assertTrue(all(r is not None for r in results))
        # All should be unique
        self.assertEqual(len(set(results)), num_requests)

    def test_get_contract_details_success(self):
        """Test successful contract details retrieval with new architecture."""
        contract = Contract()
        contract.symbol = "SPX"
        contract.secType = "IND"
        
        def mock_req_contract_details(req_id, contract):
            # Simulate async callback
            def callback():
                time.sleep(0.05)
                from ibapi.contract import ContractDetails
                details = MagicMock(spec=ContractDetails)
                details.contract = MagicMock(spec=Contract)
                details.contract.conId = 12345
                details.contract.strike = 5900.0
                details.contract.lastTradeDateOrContractMonth = "20251231"
                self.app.contractDetails(req_id, details)
                self.app.contractDetailsEnd(req_id)
            
            threading.Thread(target=callback).start()

        self.app.reqContractDetails = mock_req_contract_details
        
        conid = self.app.get_contract_details(contract, timeout=2)
        
        self.assertEqual(conid, 12345)
        self.assertEqual(self.app.conid_to_strike[12345], 5900.0)
        self.assertEqual(self.app.conid_to_expiry[12345], "20251231")

    def test_get_contract_details_timeout(self):
        """Test that contract details request handles timeout."""
        contract = Contract()
        contract.symbol = "SPX"
        
        def mock_req_contract_details(req_id, contract):
            # Don't call callback - let it timeout
            pass

        self.app.reqContractDetails = mock_req_contract_details
        
        with self.assertRaises(Exception) as context:
            self.app.get_contract_details(contract, timeout=0.1)
        
        self.assertIn("timed out", str(context.exception))

    def test_get_contract_details_no_details_found(self):
        """Test handling when no contract details are found."""
        contract = Contract()
        contract.symbol = "SPX"
        
        def mock_req_contract_details(req_id, contract):
            # Signal end without providing details
            def callback():
                time.sleep(0.05)
                self.app.contractDetailsEnd(req_id)
            
            threading.Thread(target=callback).start()

        self.app.reqContractDetails = mock_req_contract_details
        
        with self.assertRaises(Exception) as context:
            self.app.get_contract_details(contract, timeout=1)
        
        self.assertIn("No details found", str(context.exception))

    def test_contract_details_updates_mappings(self):
        """Test that contractDetails callback updates strike and expiry mappings."""
        from ibapi.contract import ContractDetails
        details = MagicMock(spec=ContractDetails)
        details.contract = MagicMock(spec=Contract)
        details.contract.conId = 99999
        details.contract.strike = 6000.0
        details.contract.lastTradeDateOrContractMonth = "20260115"

        # Simulate a request
        req_id = 1
        self.app.contract_details_results[req_id] = None
        self.app.contractDetails(req_id, details)

        self.assertIn(99999, self.app.conid_to_strike)
        self.assertEqual(self.app.conid_to_strike[99999], 6000.0)
        self.assertIn(99999, self.app.conid_to_expiry)
        self.assertEqual(self.app.conid_to_expiry[99999], "20260115")

    def test_fetch_contract_details_for_conids(self):
        """Test fetch_contract_details_for_conids with thread-safe request ID generation."""
        conid_list = [123, 456, 789]
        
        def mock_get_contract_details(contract):
            # Return the conId directly
            return contract.conId
        
        self.app.get_contract_details = mock_get_contract_details
        
        # Pre-populate some mappings
        for conid in conid_list:
            self.app.conid_to_strike[conid] = float(5900 + conid)
            self.app.conid_to_expiry[conid] = "20251231"
        
        strike_map, expiry_map = self.app.fetch_contract_details_for_conids(conid_list)
        
        # Verify mappings contain expected data
        for conid in conid_list:
            self.assertIn(conid, strike_map)
            self.assertIn(conid, expiry_map)


class TestErrorHandling(unittest.TestCase):
    """Test error handling and event signaling."""

    def setUp(self):
        self.app = IBKRApp()

    def test_error_callback_signals_event(self):
        """Test that error callback properly signals per-request event on errors."""
        req_id = 123
        self.app.contract_details_events[req_id] = threading.Event()
        
        # Error code 200 is a real error that should signal the event
        self.app.error(req_id, 200, "Test error")
        
        # Event should be signaled for this specific request
        self.assertTrue(self.app.contract_details_events[req_id].is_set())

    def test_informational_codes_dont_interfere(self):
        """Test that informational codes don't interfere with normal operation."""
        info_codes = [2104, 2106, 2158, 162, 2107, 2108]
        for code in info_codes:
            self.app.error(1, code, "Informational message")
        # Should not raise any exceptions
        self.assertTrue(True)


if __name__ == "__main__":
    unittest.main()
