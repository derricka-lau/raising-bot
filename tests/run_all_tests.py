#!/usr/bin/env python3
"""
Simple test runner for the RaisingBot test suite.
Runs all tests in the tests/ directory.
"""

import sys
import pytest

if __name__ == "__main__":
    # Run pytest with verbose output
    exit_code = pytest.main([
        "tests/",
        "-v",
        "--tb=short"
    ])
    sys.exit(exit_code)
