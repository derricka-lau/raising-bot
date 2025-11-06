# RaisingBot Test Suite

Comprehensive test coverage for the RaisingBot automated trading system.

## 📊 Test Coverage Overview

| Category | Test File | Test Cases | Purpose |
|----------|-----------|------------|---------|
| **Thread Safety** | `test_ibkr_app.py` | 10 | Validates thread-safe contract details fetching |
| **Business Logic** | `test_main.py` | 15 | Tests order processing, duplicate detection, retry logic |
| **Signal Parsing** | `test_signal_utils.py` | 8 | Validates Telegram message parsing and conversion |
| **Integration** | `test_integration.py` | 8 | End-to-end workflow validation |
| **TOTAL** | 4 files | **41 tests** | Complete system validation |

## 🚀 Quick Start

### Prerequisites

```bash
# Ensure you have pytest installed
pip install pytest

# Or install all test dependencies
pip install -r requirements.txt
pip install pytest
```

### Running Tests

```bash
# Run all tests
python -m pytest tests/ -v

# Run specific test file
python -m pytest tests/test_ibkr_app.py -v

# Run tests by category
python -m pytest tests/test_ibkr_app.py::TestContractDetailsThreadSafety -v

# Run with coverage
python -m pytest tests/ --cov=. --cov-report=html
```

## 📝 Test Scenarios Covered

### Thread Safety Tests (10 tests)

**Why**: The bot fetches contract details from multiple threads simultaneously. Without proper locking, request IDs could collide, causing orders to fail or target wrong contracts.

1. **Test Initialization** - Verifies `req_id_lock` exists and is a proper threading.Lock
2. **Test Request ID Thread Safety** - 500 concurrent threads request IDs, validates all unique
3. **Test Request ID Increments** - Sequential ID generation validation
4. **Test Multiple Concurrent Requests** - Simulates race conditions with mock callbacks
5. **Test Contract Details Success** - Validates successful contract detail retrieval
6. **Test Contract Details Timeout** - Ensures timeouts are handled gracefully
7. **Test No Details Found** - Handles case when IBKR returns no contract details
8. **Test Contract Details Updates Mappings** - Verifies strike/expiry dictionaries updated
9. **Test Fetch Contract Details for ConIDs** - Validates batch fetching with thread-safe IDs
10. **Test Error Callback Signals Event** - Error handling doesn't block operations

### Business Logic Tests (15 tests)

**Why**: Core trading logic must be bulletproof. Duplicate detection prevents placing the same order twice. Retry logic ensures transient failures don't lose orders.

1. **No Duplicates When Allowed One** - First order not considered duplicate
2. **Duplicate Detected in Existing Orders** - Matches orders already in TWS
3. **Duplicate Detected in Managed Orders** - Matches orders in current session
4. **Allowed Duplicates Two** - `allowed_duplicates=2` permits first duplicate
5. **Allowed Duplicates Exceeded** - Blocks when limit reached
6. **Get Trading Day Open Today Weekday** - Market open calculation on weekdays
7. **Get Trading Day Open Next Weekday** - Next trading day calculation
8. **Get Trading Day Open Skips Weekend** - Weekend handling to Monday
9. **Build Combo Contract** - Credit spread contract structure
10. **Build Option Contract** - Combo leg configuration
11. **Build Staged Order SNAP MID** - SNAP MID order type
12. **Build Staged Order LMT** - LMT order with price
13. **Build Staged Order PEG MID Converted to REL** - Order type conversion
14. **Retry Succeeds on Second Attempt** - Successful retry after failure
15. **Retry Fails After Max Attempts** - Exception after exhausting retries

### Signal Parsing Tests (8 tests)

**Why**: Signal parsing extracts trade parameters from Telegram messages. Incorrect parsing could result in wrong strikes, wrong expiry, or wrong trigger prices.

1. **Signal Creation Basic** - Basic Signal dataclass instantiation
2. **Signal Creation With All Fields** - All optional parameters
3. **Parse Multi-Signal Message Single Signal** - One signal extraction
4. **Parse Multi-Signal Message Multiple Signals** - Multiple signals from one message
5. **Parse Multi-Signal Message With Trigger** - Explicit trigger price parsing
6. **Parse Multi-Signal Message Invalid** - Handles invalid messages gracefully
7. **Parse Multi-Signal Message Rounds Strikes** - Strike rounding to nearest $5
8. **To Signal Conversion** - Dictionary to Signal object conversion

### Integration Tests (8 tests)

**Why**: Individual units may work correctly but fail when combined. Integration tests validate the complete workflow from signal to staged order.

1. **Process Signal Successfully** - End-to-end signal → staged order
2. **Process Signal Skips Duplicate** - Duplicate detection in full workflow
3. **Process Multiple Signals** - Batch signal processing
4. **Process Signal With ConID Error** - Graceful failure handling
5. **Complete Order Workflow** - Full workflow validation with mocks
6. **Partial Failure Recovery** - One signal failure doesn't block others
7. **Error Recovery Mechanisms** - Validates error handling doesn't crash system
8. **Order Staging and Transmission** - Staged orders ready for transmission

## 🎯 Critical Tests That Must Pass

These tests validate production-critical functionality:

- ✅ **test_get_new_reqid_thread_safety** - Prevents request ID collisions
- ✅ **test_multiple_concurrent_requests** - Race condition prevention
- ✅ **test_duplicate_detected_in_existing_orders** - Prevents duplicate orders
- ✅ **test_allowed_duplicates_exceeded** - Respects duplicate limits
- ✅ **test_parse_multi_signal_message_single_signal** - Correct signal extraction
- ✅ **test_process_signal_with_conid_error** - Graceful error handling

## 🔧 Troubleshooting

### Import Errors

If you see `ModuleNotFoundError: No module named 'ibapi'`:

```bash
# Install IBKR API
pip install ibapi
```

If you see `ModuleNotFoundError: No module named 'pytest'`:

```bash
# Install pytest
pip install pytest
```

### Test Failures

**Threading tests fail intermittently**: Increase timeout values in `test_ibkr_app.py`

**Signal parsing tests fail**: Check that `config.py` has correct `MULTI_SIGNAL_REGEX`

**Integration tests fail**: Ensure all mocks are properly configured

## 📚 Additional Documentation

- [TESTING_QUICK_START.md](../TESTING_QUICK_START.md) - Quick reference guide
- [TESTING_CHECKLIST.md](../TESTING_CHECKLIST.md) - Pre-production validation
- [TEST_SUITE_SUMMARY.md](../TEST_SUITE_SUMMARY.md) - Executive summary
- [TEST_INDEX.md](../TEST_INDEX.md) - Navigation guide

## 🔄 CI/CD Integration

Tests run automatically on every push via GitHub Actions:

```yaml
# .github/workflows/build.yml
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install pytest
      - name: Run tests
        run: python -m pytest tests/ -v
```

## 🎓 Test Philosophy

1. **No External Dependencies**: All IBKR API calls are mocked
2. **Fast Execution**: Full suite runs in ~3 seconds
3. **Deterministic**: Same input always produces same output
4. **Isolated**: Tests don't affect each other
5. **Clear Failures**: Test names and assertions clearly indicate what broke

## 📞 Support

If tests fail unexpectedly:

1. Check that code changes didn't break assumptions
2. Review test file comments for rationale
3. Ensure all dependencies installed: `pip install -r requirements.txt`
4. Check Python version compatibility (3.11+)

---

**Status**: All 41 tests passing ✅  
**Last Updated**: November 2025  
**Python Version**: 3.11+
