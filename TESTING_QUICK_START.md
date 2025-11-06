# RaisingBot Testing Quick Start

## Installation

```bash
# Install test dependencies
pip install pytest

# Or install all dependencies including pytest
pip install -r requirements.txt
pip install pytest
```

## Run All Tests

```bash
# From the raising-bot directory
python -m pytest tests/ -v
```

## Test Categories

### 1️⃣ Thread Safety Tests (Most Critical)
Tests that the thread-safe contract details fix works correctly:

```bash
# Run only thread safety tests
python -m pytest tests/test_ibkr_app.py::TestContractDetailsThreadSafety -v

# Specific test
python -m pytest tests/test_ibkr_app.py::TestContractDetailsThreadSafety::test_multiple_concurrent_requests -v
```

**What it tests:**
- ✅ Multiple concurrent contract requests don't interfere
- ✅ Each request gets unique request ID
- ✅ No race conditions in get_new_reqid()

**Why it matters:**
This validates the threading.Lock fix prevents request ID collisions.

---

### 2️⃣ Duplicate Order Detection (Business Logic)
Tests that the bot doesn't place duplicate orders:

```bash
python -m pytest tests/test_main.py::TestDuplicateOrderDetection -v
```

**Scenarios:**
- ✅ Order exists, allowed_duplicates=1 → Skip
- ✅ Order exists, allowed_duplicates=2 → Place
- ✅ Different strikes → Not a duplicate
- ✅ Count matches in both TWS and managed orders

---

### 3️⃣ Signal Processing (Integration)
Tests complete signal workflow:

```bash
python -m pytest tests/test_integration.py::TestProcessAndStageNewSignals -v
```

**Scenarios:**
- ✅ Single signal → Order placed
- ✅ Duplicate signal → Skipped
- ✅ Multiple signals → All processed
- ✅ ConID error → Handled gracefully

---

### 4️⃣ Order Building (Order Correctness)
Tests that orders are built with correct parameters:

```bash
python -m pytest tests/test_main.py::TestOrderBuilding -v
```

**Validates:**
- ✅ Combo legs assigned correctly (BUY LC, SELL SC)
- ✅ Price conditions set properly
- ✅ Order type correct (LMT, SNAP MID, PEG MID→REL)

---

### 5️⃣ Signal Parsing (Input Validation)
Tests that signals are parsed correctly from Telegram:

```bash
python -m pytest tests/test_signal_utils.py::TestSignalParsing -v
```

**Scenarios:**
- ✅ Single signal parsed with correct strikes
- ✅ Multiple signals in one message
- ✅ Trigger price calculated as midpoint
- ✅ Strikes rounded to nearest $5

---

## Quick Test Commands

```bash
# All tests
python -m pytest tests/ -v

# Specific test file
python -m pytest tests/test_ibkr_app.py -v

# Specific test class
python -m pytest tests/test_ibkr_app.py::TestContractDetailsThreadSafety -v

# Specific test case
python -m pytest tests/test_ibkr_app.py::TestIBKRAppInitialization::test_initialization -v

# Run with coverage
python -m pytest tests/ --cov=. --cov-report=html
```

## Expected Output

All tests passing:
```
=================== 41 passed in 2.5s ===================
```

## Troubleshooting

### "ModuleNotFoundError: No module named 'pytest'"
```bash
pip install pytest
```

### "ModuleNotFoundError: No module named 'ibapi'"
```bash
pip install ibapi
```

### Tests fail with import errors
Make sure you're in the correct directory:
```bash
cd raising-bot  # The directory with main.py, ibkr_app.py, etc.
python -m pytest tests/ -v
```

### Threading tests fail intermittently
This is normal for concurrency tests. Re-run:
```bash
python -m pytest tests/test_ibkr_app.py::TestContractDetailsThreadSafety -v --count=3
```

## Next Steps

✅ All tests passing? → Ready for paper trading validation  
❌ Tests failing? → Check error messages and fix issues  
📚 Want more details? → See [tests/README.md](tests/README.md)

---

**Quick Links:**
- [Full Test Documentation](tests/README.md)
- [Testing Checklist](TESTING_CHECKLIST.md)
- [Test Suite Summary](TEST_SUITE_SUMMARY.md)
