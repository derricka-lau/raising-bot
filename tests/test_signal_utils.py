# tests/test_signal_utils.py
import unittest
from unittest.mock import MagicMock, patch
from datetime import datetime
import re

from signal_utils import (
    Signal,
    parse_multi_signal_message,
    to_signal,
    get_signal_hash,
    round_strike
)


class TestSignalDataclass(unittest.TestCase):
    """Test the Signal dataclass."""

    def test_signal_creation_basic(self):
        """Test creating a basic Signal instance."""
        signal = Signal(
            expiry="20251231",
            lc_strike=5900.0,
            sc_strike=5905.0,
            trigger_price=6000.0,
            order_type="SNAP MID"
        )
        
        self.assertEqual(signal.expiry, "20251231")
        self.assertEqual(signal.lc_strike, 5900.0)
        self.assertEqual(signal.sc_strike, 5905.0)
        self.assertEqual(signal.trigger_price, 6000.0)
        self.assertEqual(signal.order_type, "SNAP MID")
        self.assertEqual(signal.allowed_duplicates, 1)

    def test_signal_creation_with_all_fields(self):
        """Test creating a Signal with all optional fields."""
        signal = Signal(
            expiry="20251231",
            lc_strike=5900.0,
            sc_strike=5905.0,
            trigger_price=6000.0,
            order_type="LMT",
            lmt_price=20.0,
            stop_price=None,
            snapmid_offset=0.15,
            allowed_duplicates=3
        )
        
        self.assertEqual(signal.lmt_price, 20.0)
        self.assertIsNone(signal.stop_price)
        self.assertEqual(signal.snapmid_offset, 0.15)
        self.assertEqual(signal.allowed_duplicates, 3)


class TestSignalParsing(unittest.TestCase):
    """Test Telegram message parsing into Signal objects."""

    def test_parse_multi_signal_message_single_signal(self):
        """Test parsing a message with one signal."""
        message = "到期日: 2025-12-31 SC: 6500 LC: 6495 未觸發"
        
        signals = parse_multi_signal_message(message)
        
        self.assertIsNotNone(signals)
        self.assertEqual(len(signals), 1)
        self.assertEqual(signals[0]["expiry"], "20251231")
        self.assertEqual(float(signals[0]["lc_strike"]), 6495.0)
        self.assertEqual(float(signals[0]["sc_strike"]), 6500.0)
        # Trigger should be calculated as midpoint
        expected_trigger = (6495.0 + 6500.0) / 2
        self.assertEqual(float(signals[0]["trigger_price"]), expected_trigger)

    def test_parse_multi_signal_message_multiple_signals(self):
        """Test parsing a message with multiple signals."""
        message = """
        到期日: 2025-12-31 SC: 6500 LC: 6495 未觸發
        到期日: 2026-01-15 SC: 6600 LC: 6595 未觸發
        """
        
        signals = parse_multi_signal_message(message)
        
        self.assertIsNotNone(signals)
        self.assertEqual(len(signals), 2)
        self.assertEqual(signals[0]["expiry"], "20251231")
        self.assertEqual(signals[1]["expiry"], "20260115")

    def test_parse_multi_signal_message_with_trigger(self):
        """Test parsing a message with trigger calculation."""
        message = "到期日: 2025-12-31 SC: 6500 LC: 6495 未觸發"
        
        signals = parse_multi_signal_message(message)
        
        self.assertIsNotNone(signals)
        self.assertEqual(len(signals), 1)
        # Trigger price is calculated as midpoint: (6500 + 6495) / 2 = 6497.5
        expected_trigger = (6495.0 + 6500.0) / 2
        self.assertEqual(float(signals[0]["trigger_price"]), expected_trigger)

    def test_parse_multi_signal_message_invalid(self):
        """Test parsing an invalid message returns None."""
        message = "This is not a valid signal message"
        
        signals = parse_multi_signal_message(message)
        
        self.assertIsNone(signals)

    def test_parse_multi_signal_message_rounds_strikes(self):
        """Test that strike prices are rounded to nearest 5."""
        message = "到期日: 2025-12-31 SC: 6502 LC: 6497 未觸發"
        
        signals = parse_multi_signal_message(message)
        
        self.assertIsNotNone(signals)
        # 6502 rounds to 6500, 6497 rounds to 6495
        self.assertEqual(float(signals[0]["sc_strike"]), 6500.0)
        self.assertEqual(float(signals[0]["lc_strike"]), 6495.0)


class TestToSignal(unittest.TestCase):
    """Test converting dictionary to Signal object."""

    @patch('signal_utils.get_valid_trading_day')
    def test_to_signal_basic(self, mock_get_valid_day):
        """Test basic dictionary to Signal conversion."""
        mock_get_valid_day.return_value = "20251231"
        
        signal_dict = {
            "expiry": "20251231",
            "lc_strike": "5900",
            "sc_strike": "5905",
            "trigger_price": "6000",
            "order_type": "SNAP MID"
        }
        
        signal = to_signal(signal_dict)
        
        self.assertEqual(signal.expiry, "20251231")
        self.assertEqual(signal.lc_strike, 5900.0)
        self.assertEqual(signal.sc_strike, 5905.0)
        self.assertEqual(signal.trigger_price, 6000.0)
        self.assertEqual(signal.order_type, "SNAP MID")

    @patch('signal_utils.get_valid_trading_day')
    def test_to_signal_with_optional_fields(self, mock_get_valid_day):
        """Test conversion with optional fields."""
        mock_get_valid_day.return_value = "20251231"
        
        signal_dict = {
            "expiry": "20251231",
            "lc_strike": "5900",
            "sc_strike": "5905",
            "trigger_price": "6000",
            "order_type": "LMT",
            "lmt_price": "20.0",
            "stop_price": None,
            "snapmid_offset": "0.15",
            "allowed_duplicates": "2"
        }
        
        signal = to_signal(signal_dict)
        
        self.assertEqual(signal.lmt_price, 20.0)
        self.assertIsNone(signal.stop_price)
        self.assertEqual(signal.snapmid_offset, 0.15)
        self.assertEqual(signal.allowed_duplicates, 2)


class TestSignalValidation(unittest.TestCase):
    """Test signal validation functions."""

    def test_get_signal_hash(self):
        """Test generating hash from signal text."""
        text = "Test signal message"
        hash1 = get_signal_hash(text)
        hash2 = get_signal_hash(text)
        
        self.assertEqual(hash1, hash2)
        self.assertEqual(len(hash1), 64)  # SHA256 hash length

    def test_round_strike(self):
        """Test strike price rounding to nearest 5."""
        self.assertEqual(round_strike("5902"), "5900")
        self.assertEqual(round_strike("5903"), "5905")
        self.assertEqual(round_strike("5897"), "5895")
        self.assertEqual(round_strike("5900"), "5900")


if __name__ == "__main__":
    unittest.main()
