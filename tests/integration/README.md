# Integration Tests

This folder contains integration tests for the Medical RAG Chatbot.

## Test Files

### `test_observability.py`
**Purpose:** Verify observability integration

**What it tests:**
- ✅ Observability module imports
- ✅ LangSmith configuration
- ✅ Trace decorator functionality
- ✅ Main app imports
- ✅ Logger integration

**How to run:**
```powershell
python tests/integration/test_observability.py
```

**Expected output:**
```
🔍 Testing Observability Integration...

1. Testing observability imports...
   ✅ All observability imports successful

2. Checking LangSmith configuration...
   ✅ LangSmith is ENABLED
   📊 Tracing is active

3. Testing trace decorator...
   ✅ Trace decorator works correctly

4. Testing main app imports...
   ✅ All main app imports successful

5. Testing logger integration...
   ✅ Logger works correctly

============================================================
✅ OBSERVABILITY INTEGRATION TEST PASSED!
============================================================
```

---

### `test_fixes.py`
**Purpose:** Verify bug fixes are working

**What it tests:**
- ✅ Unicode/Emoji logging (no UnicodeEncodeError)
- ✅ Duplicate log prevention
- ✅ Config validation
- ✅ LangSmith CLI availability

**How to run:**
```powershell
python tests/integration/test_fixes.py
```

**Expected output:**
```
============================================================
🧪 Testing All Fixes
============================================================

Test 1: Unicode/Emoji Logging
----------------------------------------
✅ Testing emoji support in logs
📊 Testing chart emoji
🚀 Testing rocket emoji
🎉 All emojis should display correctly!
✅ Test 1 PASSED - No UnicodeEncodeError!

Test 2: Duplicate Log Messages
----------------------------------------
This message should appear ONLY ONCE
This message should also appear ONLY ONCE
✅ Test 2 PASSED - No duplicates!

Test 3: Config Validation
----------------------------------------
Config loaded successfully
✅ Test 3 PASSED - No false warnings!

============================================================
🎉 All Automated Tests Passed!
============================================================
```

---

## When to Run These Tests

### **After Initial Setup:**
Run `test_observability.py` to verify:
- LangSmith is configured correctly
- All imports work
- Tracing is functional

### **After Applying Fixes:**
Run `test_fixes.py` to verify:
- Logging works without errors
- No duplicate logs
- Config is valid

### **Before Deployment:**
Run both tests to ensure:
- All components are working
- No regressions introduced
- System is ready for production

---

## Running All Integration Tests

### **Run individually:**
```powershell
python tests/integration/test_observability.py
python tests/integration/test_fixes.py
```

### **Run with pytest (if installed):**
```powershell
pytest tests/integration/
```

---

## Test Types

| Test Type | Location | Purpose |
|-----------|----------|---------|
| **Integration Tests** | `tests/integration/` | Verify component interactions |
| **Security Tests** | `tests/giskard/` | Validate security guardrails |
| **Prompt Tests** | `tests/promptfoo/` | Evaluate prompt quality |

---

## Adding New Integration Tests

1. Create new test file: `tests/integration/test_<feature>.py`
2. Follow the existing pattern:
   ```python
   """
   Test script for <feature>
   """
   import sys
   from pathlib import Path
   
   # Add project root to path
   project_root = Path(__file__).parent.parent.parent
   sys.path.insert(0, str(project_root))
   
   # Your tests here
   ```
3. Update this README with the new test

---

## Troubleshooting

### **Import Errors:**
```python
# Make sure project root is in path
import sys
from pathlib import Path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))
```

### **LangSmith Not Enabled:**
```bash
# Add to .env file:
LANGSMITH_API_KEY=your_api_key_here
LANGCHAIN_TRACING_V2=true
LANGCHAIN_PROJECT=medical-chatbot
```

### **Module Not Found:**
```powershell
# Activate virtual environment first:
.venv\Scripts\Activate.ps1

# Then run tests:
python tests/integration/test_observability.py
```

---

## Related Documentation

- **Observability Setup:** `docs/OBSERVABILITY_QUICKSTART.md`
- **Testing Guide:** `docs/TESTING_GUIDE.md`
- **Project Structure:** `docs/PROJECT_STRUCTURE.md`

---

**All integration tests should pass before deployment!** ✅
