# Test Documentation Index

Quick navigation guide for all testing documentation.

## 📚 Documentation Files

### For Developers

| Document | Purpose | When to Use |
|----------|---------|-------------|
| [tests/README.md](tests/README.md) | Complete test reference | Understanding test coverage, troubleshooting |
| [TESTING_QUICK_START.md](TESTING_QUICK_START.md) | Quick commands reference | Running tests, quick validation |
| [TEST_SUITE_SUMMARY.md](TEST_SUITE_SUMMARY.md) | Executive overview | Understanding what was built |

### For Production Deployment

| Document | Purpose | When to Use |
|----------|---------|-------------|
| [TESTING_CHECKLIST.md](TESTING_CHECKLIST.md) | Pre-production validation | Before deploying to production |

## 🎯 Quick Decision Tree

**I want to...**

### ...run the tests
→ [TESTING_QUICK_START.md](TESTING_QUICK_START.md)

### ...understand what tests cover
→ [tests/README.md](tests/README.md) → "Test Scenarios Covered"

### ...fix a failing test
→ [tests/README.md](tests/README.md) → "Troubleshooting"

### ...validate before production
→ [TESTING_CHECKLIST.md](TESTING_CHECKLIST.md)

### ...understand the thread-safety fix
→ [TEST_SUITE_SUMMARY.md](TEST_SUITE_SUMMARY.md) → "What Was Fixed"

## 📖 Test Files Reference

| Test File | Line Count | Focus Area |
|-----------|------------|------------|
| `tests/test_ibkr_app.py` | ~200 | Thread-safe IBKR operations |
| `tests/test_main.py` | ~300 | Business logic and workflows |
| `tests/test_signal_utils.py` | ~150 | Signal parsing and validation |
| `tests/test_integration.py` | ~180 | End-to-end integration |

## 🚀 Quick Commands

```bash
# Run all tests
python -m pytest tests/ -v

# Run critical thread safety tests
python -m pytest tests/test_ibkr_app.py::TestContractDetailsThreadSafety -v

# Run specific test
python -m pytest tests/test_main.py::TestDuplicateOrderDetection::test_no_duplicates_when_allowed_one -v
```

## ✅ Production Readiness Path

1. Read: [TEST_SUITE_SUMMARY.md](TEST_SUITE_SUMMARY.md)
2. Run: `python -m pytest tests/ -v`
3. Verify: All 41 tests pass
4. Follow: [TESTING_CHECKLIST.md](TESTING_CHECKLIST.md)
5. Deploy: After 5+ days successful paper trading

---

**Need Help?**
- Check [tests/README.md](tests/README.md) → Troubleshooting section
- Review test file comments for specific test rationale
- Ensure dependencies installed: `pip install pytest`
