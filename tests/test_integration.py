# tests/test_integration.py
import unittest
from unittest.mock import MagicMock, patch, call
from datetime import datetime
import threading

from main import (
    process_and_stage_new_signals,
    ManagedOrder
)
from signal_utils import Signal
from ibkr_app import IBKRApp


class TestProcessAndStageNewSignals(unittest.TestCase):
    """Test the end-to-end signal processing and order staging."""

    def setUp(self):
        """Set up mock app and common test data."""
        self.mock_app = MagicMock(spec=IBKRApp)
        self.mock_app.nextOrderId = 1
        self.mock_app.placeOrder = MagicMock()
        self.mock_app.open_orders = []
        self.mock_app.error_order_ids = []
        
        self.signal = Signal(
            expiry="20251231",
            lc_strike=5900.0,
            sc_strike=5905.0,
            trigger_price=6000.0,
            order_type="SNAP MID",
            snapmid_offset=0.1,
            allowed_duplicates=1
        )

    @patch('main.get_contract_conid_with_retry')
    @patch('main.build_option_contract')
    @patch('main.build_combo_contract')
    @patch('main.build_staged_order')
    def test_process_signal_successfully(self, mock_build_order, mock_build_contract, mock_build_option, mock_get_conid):
        """Test successful signal processing and order staging."""
        # Setup mocks
        mock_lc_contract = MagicMock()
        mock_sc_contract = MagicMock()
        mock_build_option.side_effect = [mock_lc_contract, mock_sc_contract]
        mock_get_conid.side_effect = [123, 456]  # LC and SC conids
        mock_combo_contract = MagicMock()
        mock_build_contract.return_value = mock_combo_contract
        mock_order = MagicMock()
        mock_build_order.return_value = mock_order
        
        managed_orders = []
        existing_orders = []
        
        process_and_stage_new_signals(
            self.mock_app,
            [self.signal],
            managed_orders,
            existing_orders,
            trigger_conid=999
        )
        
        # Verify order was placed
        self.mock_app.placeOrder.assert_called_once()
        self.assertEqual(len(managed_orders), 1)
        self.assertEqual(managed_orders[0].lc_strike, 5900.0)
        self.assertEqual(managed_orders[0].sc_strike, 5905.0)

    @patch('main.get_contract_conid_with_retry')
    @patch('main.build_option_contract')
    def test_process_signal_skips_duplicate(self, mock_build_option, mock_get_conid):
        """Test that duplicate signals are skipped."""
        mock_lc_contract = MagicMock()
        mock_sc_contract = MagicMock()
        mock_build_option.side_effect = [mock_lc_contract, mock_sc_contract]
        mock_get_conid.side_effect = [123, 456]
        
        managed_orders = []
        existing_orders = [{
            "secType": "BAG",
            "leg_conIds": [123, 456],
            "trigger_price": 6000.0
        }]
        
        process_and_stage_new_signals(
            self.mock_app,
            [self.signal],
            managed_orders,
            existing_orders,
            trigger_conid=999
        )
        
        # Should not place order
        self.mock_app.placeOrder.assert_not_called()
        self.assertEqual(len(managed_orders), 0)

    @patch('main.get_contract_conid_with_retry')
    @patch('main.build_option_contract')
    @patch('main.build_combo_contract')
    @patch('main.build_staged_order')
    def test_process_multiple_signals(self, mock_build_order, mock_build_contract, mock_build_option, mock_get_conid):
        """Test processing multiple signals."""
        signal2 = Signal(
            expiry="20260115",
            lc_strike=6000.0,
            sc_strike=6005.0,
            trigger_price=6100.0,
            order_type="LMT",
            lmt_price=25.0,
            allowed_duplicates=1
        )
        
        # Build option contracts for both signals
        mock_build_option.side_effect = [MagicMock(), MagicMock(), MagicMock(), MagicMock()]
        mock_get_conid.side_effect = [123, 456, 789, 101]
        mock_build_contract.return_value = MagicMock()
        mock_build_order.return_value = MagicMock()
        
        managed_orders = []
        existing_orders = []
        
        process_and_stage_new_signals(
            self.mock_app,
            [self.signal, signal2],
            managed_orders,
            existing_orders,
            trigger_conid=999
        )
        
        # Should place 2 orders
        self.assertEqual(self.mock_app.placeOrder.call_count, 2)
        self.assertEqual(len(managed_orders), 2)

    @patch('main.get_contract_conid_with_retry')
    @patch('main.build_option_contract')
    def test_process_signal_with_conid_error(self, mock_build_option, mock_get_conid):
        """Test handling when conid fetch fails."""
        # Simulate failure on LC conid fetch
        mock_build_option.return_value = MagicMock()
        mock_get_conid.side_effect = Exception("Failed to get conid")
        
        managed_orders = []
        existing_orders = []
        
        # Should not raise exception, just skip the signal
        process_and_stage_new_signals(
            self.mock_app,
            [self.signal],
            managed_orders,
            existing_orders,
            trigger_conid=999
        )
        
        self.mock_app.placeOrder.assert_not_called()
        self.assertEqual(len(managed_orders), 0)


class TestOrderWorkflow(unittest.TestCase):
    """Test complete order workflow from signal to placement."""

    @patch('main.get_contract_conid_with_retry')
    @patch('main.build_option_contract')
    @patch('main.build_combo_contract')
    @patch('main.build_staged_order')
    @patch('main.stage_order')
    def test_complete_order_workflow(self, mock_stage, mock_build_order, mock_build_contract, mock_build_option, mock_get_conid):
        """Test complete workflow from signal parsing to order staging."""
        # Setup
        mock_app = MagicMock(spec=IBKRApp)
        mock_app.nextOrderId = 100
        
        signal = Signal(
            expiry="20251231",
            lc_strike=5900.0,
            sc_strike=5905.0,
            trigger_price=6000.0,
            order_type="SNAP MID",
            allowed_duplicates=1
        )
        
        mock_lc_contract = MagicMock()
        mock_sc_contract = MagicMock()
        mock_build_option.side_effect = [mock_lc_contract, mock_sc_contract]
        mock_get_conid.side_effect = [123, 456]
        mock_contract = MagicMock()
        mock_build_contract.return_value = mock_contract
        mock_order = MagicMock()
        mock_build_order.return_value = mock_order
        mock_managed_order = MagicMock()
        mock_stage.return_value = mock_managed_order
        
        # Execute
        from main import process_and_stage_new_signals
        managed_orders = []
        existing_orders = []
        
        process_and_stage_new_signals(
            mock_app,
            [signal],
            managed_orders,
            existing_orders,
            trigger_conid=999
        )
        
        # Verify all steps called
        self.assertEqual(mock_build_option.call_count, 2)
        self.assertEqual(mock_get_conid.call_count, 2)
        mock_build_contract.assert_called_once_with(123, 456)
        mock_build_order.assert_called_once()
        mock_stage.assert_called_once()


class TestErrorRecovery(unittest.TestCase):
    """Test error recovery mechanisms."""

    @patch('main.get_contract_conid_with_retry')
    @patch('main.build_option_contract')
    @patch('main.build_combo_contract')
    @patch('main.build_staged_order')
    def test_partial_failure_recovery(self, mock_build_order, mock_build_contract, mock_build_option, mock_get_conid):
        """Test that one signal failure doesn't prevent processing others."""
        signal1 = Signal(
            expiry="20251231",
            lc_strike=5900.0,
            sc_strike=5905.0,
            trigger_price=6000.0,
            order_type="SNAP MID",
            allowed_duplicates=1
        )
        
        signal2 = Signal(
            expiry="20260115",
            lc_strike=6000.0,
            sc_strike=6005.0,
            trigger_price=6100.0,
            order_type="LMT",
            lmt_price=25.0,
            allowed_duplicates=1
        )
        
        # Build option contracts (4 total - 2 for each signal)
        mock_build_option.side_effect = [
            MagicMock(),  # LC for signal1
            MagicMock(),  # SC for signal1 (not needed since LC fails)
            MagicMock(),  # LC for signal2
            MagicMock()   # SC for signal2
        ]
        
        # First signal's LC fails, second signal succeeds completely
        mock_get_conid.side_effect = [
            Exception("Network error"),  # LC for signal1 fails
            789,  # LC for signal2 succeeds
            101   # SC for signal2 succeeds
        ]
        
        mock_app = MagicMock(spec=IBKRApp)
        mock_app.nextOrderId = 1
        mock_app.placeOrder = MagicMock()
        mock_app.open_orders = []  # Add required attribute
        mock_app.error_order_ids = []  # Add required attribute
        
        mock_build_contract.return_value = MagicMock()
        mock_build_order.return_value = MagicMock()
        
        managed_orders = []
        existing_orders = []
        
        # Don't mock stage_order - let it call placeOrder
        process_and_stage_new_signals(
            mock_app,
            [signal1, signal2],
            managed_orders,
            existing_orders,
            trigger_conid=999
        )
        
        # Only signal2 should be placed
        self.assertEqual(mock_app.placeOrder.call_count, 1)
        self.assertEqual(len(managed_orders), 1)


if __name__ == "__main__":
    unittest.main()
