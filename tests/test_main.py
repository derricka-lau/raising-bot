# tests/test_main.py
import unittest
import threading
import time
from unittest.mock import MagicMock, patch, call
from datetime import datetime, timedelta
from dataclasses import dataclass
from typing import Optional

# Import the functions and classes we're testing
from main import (
    is_duplicate_order,
    build_combo_contract,
    build_staged_order,
    ManagedOrder,
    get_trading_day_open
)
from signal_utils import Signal
from ibkr_app import IBKRApp
from ibapi.contract import Contract
from ibapi.order import Order


class TestIBKRAppInitialization(unittest.TestCase):
    """Test IBKRApp initialization (duplicate from test_ibkr_app.py for completeness)."""

    def setUp(self):
        self.app = IBKRApp()

    def test_initialization(self):
        """Verify IBKRApp has thread-safe lock."""
        self.assertIsNotNone(self.app.req_id_lock)
        # Use duck-typing for cross-version compatibility
        self.assertTrue(hasattr(self.app.req_id_lock, 'acquire'))
        self.assertTrue(hasattr(self.app.req_id_lock, 'release'))


class TestDuplicateOrderDetection(unittest.TestCase):
    """Test duplicate order detection logic with allowed_duplicates support."""

    def test_no_duplicates_when_allowed_one(self):
        """Test that first order is not considered duplicate when allowed_duplicates=1."""
        leg_ids = [123, 456]
        trigger = 6000.0
        existing = []
        managed = []
        signal = Signal(
            expiry="20251231",
            lc_strike=5900.0,
            sc_strike=5905.0,
            trigger_price=6000.0,
            order_type="SNAP MID",
            allowed_duplicates=1
        )
        result = is_duplicate_order(leg_ids, trigger, existing, managed, signal)
        self.assertFalse(result)

    def test_duplicate_detected_in_existing_orders(self):
        """Test duplicate detection when matching order exists in TWS."""
        leg_ids = [123, 456]
        trigger = 6000.0
        existing = [{
            "secType": "BAG",
            "leg_conIds": [123, 456],
            "trigger_price": 6000.0
        }]
        managed = []
        signal = Signal(
            expiry="20251231",
            lc_strike=5900.0,
            sc_strike=5905.0,
            trigger_price=6000.0,
            order_type="SNAP MID",
            allowed_duplicates=1
        )
        result = is_duplicate_order(leg_ids, trigger, existing, managed, signal)
        self.assertTrue(result)

    def test_duplicate_detected_in_managed_orders(self):
        """Test duplicate detection in current session's managed orders."""
        leg_ids = [123, 456]
        trigger = 6000.0
        existing = []
        
        # Create a mock managed order with proper structure
        mock_contract = MagicMock()
        mock_leg1 = MagicMock(conId=123)
        mock_leg2 = MagicMock(conId=456)
        mock_contract.comboLegs = [mock_leg1, mock_leg2]
        
        managed = [
            MagicMock(contract=mock_contract, trigger=6000.0)
        ]
        signal = Signal(
            expiry="20251231",
            lc_strike=5900.0,
            sc_strike=5905.0,
            trigger_price=6000.0,
            order_type="SNAP MID",
            allowed_duplicates=1
        )
        result = is_duplicate_order(leg_ids, trigger, existing, managed, signal)
        self.assertTrue(result)

    def test_allowed_duplicates_two(self):
        """Test that allowed_duplicates=2 allows first duplicate."""
        leg_ids = [123, 456]
        trigger = 6000.0
        existing = [{
            "leg_conIds": [123, 456],
            "trigger_price": 6000.0
        }]
        managed = []
        signal = Signal(
            expiry="20251231",
            lc_strike=5900.0,
            sc_strike=5905.0,
            trigger_price=6000.0,
            order_type="SNAP MID",
            allowed_duplicates=2
        )
        result = is_duplicate_order(leg_ids, trigger, existing, managed, signal)
        self.assertFalse(result)  # Should allow second order

    def test_allowed_duplicates_exceeded(self):
        """Test that duplicate is detected when count exceeds allowed_duplicates."""
        leg_ids = [123, 456]
        trigger = 6000.0
        existing = [
            {"secType": "BAG", "leg_conIds": [123, 456], "trigger_price": 6000.0},
            {"secType": "BAG", "leg_conIds": [123, 456], "trigger_price": 6000.0}
        ]
        managed = []
        signal = Signal(
            expiry="20251231",
            lc_strike=5900.0,
            sc_strike=5905.0,
            trigger_price=6000.0,
            order_type="SNAP MID",
            allowed_duplicates=2
        )
        result = is_duplicate_order(leg_ids, trigger, existing, managed, signal)
        self.assertTrue(result)  # Already have 2, can't add more


class TestTradingDayCalculations(unittest.TestCase):
    """Test trading day calculation functions."""

    def test_get_trading_day_open_today_weekday(self):
        """Test getting today's market open on a weekday."""
        import pytz
        tz = pytz.timezone("America/New_York")
        
        # Mock a weekday (Monday = 0)
        with patch('main.datetime') as mock_dt:
            mock_now = datetime(2025, 1, 6, 8, 0, 0)  # Monday 8 AM
            mock_dt.now.return_value = tz.localize(mock_now)
            
            result = get_trading_day_open(tz, 'today')
            
            # Should return 9:30 AM same day
            self.assertEqual(result.hour, 9)
            self.assertEqual(result.minute, 30)

    def test_get_trading_day_open_next_weekday(self):
        """Test getting next trading day's market open."""
        import pytz
        tz = pytz.timezone("America/New_York")
        result = get_trading_day_open(tz, 'next')
        
        # Should return a future time
        self.assertIsNotNone(result)
        self.assertEqual(result.hour, 9)
        self.assertEqual(result.minute, 30)

    def test_get_trading_day_open_skips_weekend(self):
        """Test that weekend days are skipped to next Monday."""
        import pytz
        tz = pytz.timezone("America/New_York")
        
        with patch('main.datetime') as mock_dt:
            # Saturday
            mock_now = datetime(2025, 1, 11, 10, 0, 0)
            mock_dt.now.return_value = tz.localize(mock_now)
            
            result = get_trading_day_open(tz, 'next')
            
            # Should be Monday
            self.assertNotEqual(result.weekday(), 5)  # Not Saturday
            self.assertNotEqual(result.weekday(), 6)  # Not Sunday


class TestContractBuilding(unittest.TestCase):
    """Test contract building functions."""

    def test_build_combo_contract(self):
        """Test building a combo contract (credit spread)."""
        lc_conid = 123
        sc_conid = 456
        
        contract = build_combo_contract(lc_conid, sc_conid)
        
        self.assertEqual(contract.secType, "BAG")
        self.assertEqual(contract.symbol, "SPX")
        self.assertEqual(len(contract.comboLegs), 2)
        self.assertEqual(contract.comboLegs[0].conId, lc_conid)
        self.assertEqual(contract.comboLegs[0].action, "BUY")
        self.assertEqual(contract.comboLegs[1].conId, sc_conid)
        self.assertEqual(contract.comboLegs[1].action, "SELL")

    def test_build_option_contract(self):
        """Test that combo contracts have correct structure."""
        contract = build_combo_contract(111, 222)
        
        # Verify combo legs are properly configured
        self.assertEqual(contract.comboLegs[0].ratio, 1)
        self.assertEqual(contract.comboLegs[1].ratio, 1)
        self.assertEqual(contract.comboLegs[0].exchange, "SMART")
        self.assertEqual(contract.comboLegs[1].exchange, "SMART")


class TestOrderBuilding(unittest.TestCase):
    """Test order building with different order types."""

    def test_build_staged_order_snap_mid(self):
        """Test building a SNAP MID order."""
        signal = Signal(
            expiry="20251231",
            lc_strike=5900.0,
            sc_strike=5905.0,
            trigger_price=6000.0,
            order_type="SNAP MID",
            snapmid_offset=0.1,
            allowed_duplicates=1
        )
        
        order = build_staged_order(signal, trigger_conid=999)
        
        self.assertEqual(order.orderType, "SNAP MID")
        self.assertEqual(order.action, "BUY")
        self.assertEqual(order.totalQuantity, 1)
        self.assertEqual(order.tif, "DAY")
        self.assertFalse(order.transmit)
        self.assertEqual(len(order.conditions), 1)

    def test_build_staged_order_lmt(self):
        """Test building a LMT order."""
        signal = Signal(
            expiry="20251231",
            lc_strike=5900.0,
            sc_strike=5905.0,
            trigger_price=6000.0,
            order_type="LMT",
            lmt_price=20.0,
            allowed_duplicates=1
        )
        
        order = build_staged_order(signal, trigger_conid=999)
        
        self.assertEqual(order.orderType, "LMT")
        self.assertEqual(order.lmtPrice, 20.0)

    def test_build_staged_order_peg_mid_converted_to_rel(self):
        """Test that PEG MID is converted to REL order type."""
        signal = Signal(
            expiry="20251231",
            lc_strike=5900.0,
            sc_strike=5905.0,
            trigger_price=6000.0,
            order_type="PEG MID",
            lmt_price=25.0,
            allowed_duplicates=1
        )
        
        order = build_staged_order(signal, trigger_conid=999)
        
        # PEG MID should be converted to REL
        self.assertEqual(order.orderType, "REL")


class TestConidRetryLogic(unittest.TestCase):
    """Test retry logic for fetching contract IDs."""

    @patch('main.time.sleep')
    def test_retry_succeeds_on_second_attempt(self, mock_sleep):
        """Test that retry logic succeeds after initial failure."""
        app = MagicMock()
        app.get_contract_details = MagicMock(side_effect=[Exception("Network error"), 12345])
        
        from main import get_contract_conid_with_retry, build_option_contract
        
        contract = build_option_contract("20251231", 5900.0, "C")
        result = get_contract_conid_with_retry(app, contract, attempts=3)
        
        self.assertEqual(result, 12345)
        self.assertEqual(app.get_contract_details.call_count, 2)

    @patch('main.time.sleep')
    def test_retry_fails_after_max_attempts(self, mock_sleep):
        """Test that retry logic raises exception after max attempts."""
        app = MagicMock()
        app.get_contract_details = MagicMock(side_effect=Exception("Persistent error"))
        
        from main import get_contract_conid_with_retry, build_option_contract
        
        contract = build_option_contract("20251231", 5900.0, "C")
        
        with self.assertRaises(Exception):
            get_contract_conid_with_retry(app, contract, attempts=3)
        
        self.assertEqual(app.get_contract_details.call_count, 3)

    def test_retry_succeeds_immediately(self):
        """Test successful operation on first attempt."""
        app = MagicMock()
        app.get_contract_details = MagicMock(return_value=99999)
        
        from main import get_contract_conid_with_retry, build_option_contract
        
        contract = build_option_contract("20251231", 5900.0, "C")
        result = get_contract_conid_with_retry(app, contract, attempts=3)
        
        self.assertEqual(result, 99999)
        self.assertEqual(app.get_contract_details.call_count, 1)


class TestManagedOrderDataclass(unittest.TestCase):
    """Test the ManagedOrder dataclass."""

    def test_managed_order_creation(self):
        """Test creating a ManagedOrder instance."""
        contract = MagicMock(spec=Contract)
        order = MagicMock(spec=Order)
        
        managed = ManagedOrder(
            id=123,
            trigger=6000.0,
            lc_strike=5900.0,
            sc_strike=5905.0,
            contract=contract,
            order_obj=order,
            hash="abc123"
        )
        
        self.assertEqual(managed.id, 123)
        self.assertEqual(managed.trigger, 6000.0)
        self.assertEqual(managed.lc_strike, 5900.0)
        self.assertEqual(managed.sc_strike, 5905.0)
        self.assertEqual(managed.hash, "abc123")


if __name__ == "__main__":
    unittest.main()
