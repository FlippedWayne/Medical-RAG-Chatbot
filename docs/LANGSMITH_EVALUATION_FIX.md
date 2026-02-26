# 🔧 LangSmith Evaluation Setup Fix

**Issue:** Evaluation script fails with "LangSmith not enabled"

**Error:**
```
2026-02-09 14:35:14 - src.observability.evaluation - WARNING - LangSmith not enabled, cannot create dataset
2026-02-09 14:35:14 - __main__ - ERROR - ❌ Failed to create dataset
```

---

## 🔍 **Root Cause**

The evaluation script requires:
1. ✅ `LANGSMITH_API_KEY` environment variable
2. ✅ `LANGCHAIN_TRACING_V2=true` environment variable
3. ✅ LangSmith client initialized

**Problem:** No `.env` file exists with these variables!

---

## ✅ **Solution**

### **Option 1: Create .env File** ⭐ **Recommended**

**Create `.env` file in project root:**

```bash
# LangSmith Configuration
LANGSMITH_API_KEY=your_langsmith_api_key_here
LANGCHAIN_TRACING_V2=true
LANGCHAIN_PROJECT=medical-chatbot

# Or use LANGCHAIN_API_KEY (alternative)
LANGCHAIN_API_KEY=your_langsmith_api_key_here
```

**Steps:**
1. Get your LangSmith API key from: https://smith.langchain.com/settings
2. Create `.env` file in project root
3. Add the variables above
4. Run evaluation again

---

### **Option 2: Set Environment Variables Manually**

**PowerShell:**
```powershell
$env:LANGSMITH_API_KEY = "your_api_key_here"
$env:LANGCHAIN_TRACING_V2 = "true"
$env:LANGCHAIN_PROJECT = "medical-chatbot"

# Then run evaluation
python tests/evaluation/evaluate_chatbot.py --create-dataset
```

---

### **Option 3: Fix evaluate_chatbot.py**

**Update the script to call `configure_langsmith()`:**

```python
# In evaluate_chatbot.py, add after imports:
from src.observability.langsmith_config import configure_langsmith

# Before creating dataset, add:
configure_langsmith(
    api_key=langsmith_api_key,
    project_name="medical-chatbot-evaluators",
    enable_tracing=True
)
```

---

## 🎯 **Quick Fix (Recommended)**

### **Step 1: Create .env file**

```powershell
# Create .env file
New-Item .env -ItemType File

# Add content (replace with your actual API key)
@"
# LangSmith Configuration
LANGSMITH_API_KEY=ls_your_actual_api_key_here
LANGCHAIN_TRACING_V2=true
LANGCHAIN_PROJECT=medical-chatbot
"@ | Set-Content .env
```

### **Step 2: Get your API key**

1. Go to: https://smith.langchain.com/settings
2. Click "Create API Key"
3. Copy the key
4. Replace `ls_your_actual_api_key_here` in `.env`

### **Step 3: Run evaluation**

```powershell
python tests/evaluation/evaluate_chatbot.py --create-dataset
```

---

## 🔧 **Alternative: Update evaluate_chatbot.py**

**Add configuration call at the beginning:**

```python
# After line 38 in evaluate_chatbot.py
if langsmith_api_key:
    logger.info("✅ LangSmith tracing enabled for evaluations")
    logger.info(f"📊 Project: medical-chatbot-evaluators")
    
    # ADD THIS:
    from src.observability.langsmith_config import configure_langsmith
    configure_langsmith(
        api_key=langsmith_api_key,
        project_name="medical-chatbot-evaluators",
        enable_tracing=True
    )
else:
    logger.warning("⚠️ LangSmith API key not found. Evaluation features may be limited.")
    logger.warning("💡 Make sure LANGSMITH_API_KEY is set in .env file")
```

---

## 📊 **Why This Happens**

### **Current Flow:**

```
1. evaluate_chatbot.py sets env vars
   ↓
2. Imports src.observability.evaluation
   ↓
3. evaluation.py calls is_langsmith_enabled()
   ↓
4. is_langsmith_enabled() checks env vars ✅
   BUT client is not initialized! ❌
   ↓
5. get_langsmith_client() returns None ❌
   ↓
6. Dataset creation fails ❌
```

### **Problem:**

The `_langsmith_client` global variable is `None` because `configure_langsmith()` was never called!

---

## ✅ **Proper Flow:**

```
1. Load .env file (or set env vars)
   ↓
2. Call configure_langsmith()
   ↓
3. Client initialized ✅
   ↓
4. is_langsmith_enabled() returns True ✅
   ↓
5. get_langsmith_client() returns client ✅
   ↓
6. Dataset creation works ✅
```

---

## 🚀 **Recommended Fix**

### **Update evaluate_chatbot.py:**

Add this after line 38:

```python
# Configure LangSmith
if langsmith_api_key:
    logger.info("✅ LangSmith tracing enabled for evaluations")
    logger.info(f"📊 Project: medical-chatbot-evaluators")
    
    # Initialize LangSmith client
    from src.observability.langsmith_config import configure_langsmith
    success = configure_langsmith(
        api_key=langsmith_api_key,
        project_name="medical-chatbot-evaluators",
        enable_tracing=True
    )
    
    if not success:
        logger.error("❌ Failed to configure LangSmith")
        logger.error("💡 Check your API key and try again")
        sys.exit(1)
else:
    logger.warning("⚠️ LangSmith API key not found. Evaluation features may be limited.")
    logger.warning("💡 Make sure LANGSMITH_API_KEY is set in .env file")
    sys.exit(1)
```

---

## ✅ **Summary**

**Problem:**
- ❌ No `.env` file
- ❌ `configure_langsmith()` never called
- ❌ Client not initialized

**Solution:**
1. ✅ Create `.env` file with `LANGSMITH_API_KEY`
2. ✅ Update `evaluate_chatbot.py` to call `configure_langsmith()`
3. ✅ Run evaluation again

**Quick Command:**
```powershell
# Set env var temporarily
$env:LANGSMITH_API_KEY = "your_api_key"
$env:LANGCHAIN_TRACING_V2 = "true"

# Run evaluation
python tests/evaluation/evaluate_chatbot.py --create-dataset
```

---

**Would you like me to:**
1. Create a `.env.example` file?
2. Update `evaluate_chatbot.py` to call `configure_langsmith()`?
3. Both?

Let me know! 🚀
