# 📁 Evaluation Scripts Analysis

**Date:** 2026-02-09  
**Files:** `evaluate_chatbot.py`, `promptfoo_wrapper.py`  
**Current Location:** Root directory  
**Recommendation:** Move to appropriate test folders

---

## 🔍 **File Analysis**

### **1. evaluate_chatbot.py**

**Purpose:** LangSmith-based evaluation script

**What it does:**
```python
- Creates test datasets for evaluation
- Runs comprehensive evaluations using LangSmith
- Custom evaluators (relevance, keywords, length, errors)
- Tracks results in LangSmith dashboard
- Generates evaluation reports
```

**Key Features:**
- ✅ 8 medical test examples
- ✅ 4 custom evaluators
- ✅ LangSmith integration
- ✅ Traceable functions
- ✅ Command-line interface

**Type:** Evaluation/Testing script

**Size:** 367 lines, 12.6 KB

---

### **2. promptfoo_wrapper.py**

**Purpose:** Wrapper for Promptfoo testing

**What it does:**
```python
- Provides Promptfoo-compatible API
- Tests RAG chatbot with Promptfoo
- Loads vectorstore and LLM
- Returns responses for Promptfoo assertions
```

**Key Features:**
- ✅ Promptfoo integration
- ✅ RAG chain testing
- ✅ Command-line interface
- ✅ Stdin/stdout support

**Type:** Testing utility/wrapper

**Size:** 135 lines, 3.5 KB

---

## 📊 **Current vs Recommended Structure**

### **Current (Root):**
```
Medical-RAG-Chatbot/
├── evaluate_chatbot.py         ❌ In root
├── promptfoo_wrapper.py         ❌ In root
├── app.py
├── create_vectorstore.py
│
└── tests/
    ├── integration/
    ├── giskard/
    └── promptfoo/
```

**Issues:**
- ❌ Clutters root directory
- ❌ Not organized with related tests
- ❌ Inconsistent structure

---

### **Recommended Structure:**

```
Medical-RAG-Chatbot/
├── app.py                       ✅ Clean root
├── create_vectorstore.py
│
└── tests/
    ├── integration/
    │   ├── test_observability.py
    │   └── test_fixes.py
    │
    ├── evaluation/              ← NEW!
    │   ├── __init__.py
    │   ├── README.md
    │   ├── evaluate_chatbot.py      ✅ Move here
    │   └── results/                 ← Evaluation results
    │
    ├── giskard/
    │
    └── promptfoo/
        ├── promptfooconfig.yaml
        ├── promptfoo_wrapper.py     ✅ Move here
        └── ...
```

---

## 🎯 **Detailed Recommendations**

### **1. evaluate_chatbot.py → tests/evaluation/**

**Why:**
- ✅ It's an evaluation script (belongs with tests)
- ✅ Uses LangSmith for evaluation
- ✅ Creates datasets and runs evaluations
- ✅ Not production code

**Recommended location:**
```
tests/evaluation/evaluate_chatbot.py
```

**Benefits:**
- ✅ Groups all evaluation scripts together
- ✅ Separate from integration tests
- ✅ Clear purpose (evaluation)
- ✅ Results can go in `tests/evaluation/results/`

---

### **2. promptfoo_wrapper.py → tests/promptfoo/**

**Why:**
- ✅ It's specifically for Promptfoo testing
- ✅ Already have `tests/promptfoo/` folder
- ✅ Belongs with Promptfoo config
- ✅ Not production code

**Recommended location:**
```
tests/promptfoo/promptfoo_wrapper.py
```

**Benefits:**
- ✅ All Promptfoo files in one place
- ✅ Easy to find
- ✅ Logical organization
- ✅ Consistent with other test tools

---

## 📁 **Proposed Final Structure**

```
Medical-RAG-Chatbot/
├── app.py                           ✅ Main app
├── create_vectorstore.py            ✅ Main script
├── pyproject.toml                   ✅ Config
├── README.md                        ✅ Docs
│
├── src/                             ✅ Production code
│   ├── observability/
│   ├── content_analyzer/
│   ├── model/
│   └── utils/
│
├── tests/                           ✅ All tests
│   ├── integration/                 ✅ Integration tests
│   │   ├── __init__.py
│   │   ├── README.md
│   │   ├── test_observability.py
│   │   └── test_fixes.py
│   │
│   ├── evaluation/                  ← NEW!
│   │   ├── __init__.py
│   │   ├── README.md
│   │   ├── evaluate_chatbot.py      ✅ LangSmith evaluation
│   │   └── results/                 ← Evaluation results
│   │       └── .gitkeep
│   │
│   ├── giskard/                     ✅ Security testing
│   │   ├── run_tests.py
│   │   ├── security_tests.py
│   │   └── ...
│   │
│   └── promptfoo/                   ✅ Prompt testing
│       ├── promptfooconfig.yaml
│       ├── promptfoo_wrapper.py     ✅ Promptfoo wrapper
│       └── ...
│
└── docs/                            ✅ Documentation
```

---

## 🔧 **Implementation Steps**

### **Step 1: Create evaluation folder**
```powershell
mkdir tests\evaluation
mkdir tests\evaluation\results
New-Item tests\evaluation\__init__.py
New-Item tests\evaluation\results\.gitkeep
```

### **Step 2: Move evaluate_chatbot.py**
```powershell
Move-Item evaluate_chatbot.py tests\evaluation\evaluate_chatbot.py
```

### **Step 3: Move promptfoo_wrapper.py**
```powershell
Move-Item promptfoo_wrapper.py tests\promptfoo\promptfoo_wrapper.py
```

### **Step 4: Update imports (if needed)**

**evaluate_chatbot.py:**
```python
# Update path reference (line 12)
# Before:
project_root = Path(__file__).parent.parent.parent

# After:
project_root = Path(__file__).parent.parent.parent
# (Already correct! No change needed)
```

**promptfoo_wrapper.py:**
```python
# Update path reference (line 11)
# Before:
project_root = Path(__file__).parent

# After:
project_root = Path(__file__).parent.parent.parent
```

### **Step 5: Update .gitignore**
```gitignore
# Evaluation results
tests/evaluation/results/*.csv
tests/evaluation/results/*.json
!tests/evaluation/results/.gitkeep
```

---

## 📊 **File Categories**

### **Production Code (src/):**
```
src/
├── observability/      ← Runtime monitoring
├── content_analyzer/   ← Runtime guardrails
├── model/              ← Runtime LLM
└── utils/              ← Runtime utilities
```

### **Main Scripts (root):**
```
root/
├── app.py                      ← Main Streamlit app
├── create_vectorstore.py       ← Vector store creation
└── pyproject.toml              ← Project config
```

### **Test Code (tests/):**
```
tests/
├── integration/        ← Integration tests
├── evaluation/         ← Evaluation scripts ✅
├── giskard/            ← Security testing
└── promptfoo/          ← Prompt testing ✅
```

---

## ✅ **Benefits of Reorganization**

### **1. Clean Root Directory:**
```
Before: 2 evaluation files in root ❌
After:  0 evaluation files in root ✅
```

### **2. Logical Organization:**
```
tests/
├── integration/    ← Component interaction
├── evaluation/     ← LangSmith evaluation ✅
├── giskard/        ← Security testing
└── promptfoo/      ← Prompt testing ✅
```

### **3. Easy to Find:**
```
"Where's the LangSmith evaluation?"
→ tests/evaluation/evaluate_chatbot.py ✅

"Where's the Promptfoo wrapper?"
→ tests/promptfoo/promptfoo_wrapper.py ✅
```

### **4. Consistent Structure:**
```
All testing/evaluation tools in tests/ ✅
All production code in src/ ✅
Main scripts in root/ ✅
```

---

## 🎯 **Comparison**

| Aspect | evaluate_chatbot.py | promptfoo_wrapper.py |
|--------|---------------------|----------------------|
| **Purpose** | LangSmith evaluation | Promptfoo testing |
| **Current Location** | Root ❌ | Root ❌ |
| **Recommended** | tests/evaluation/ ✅ | tests/promptfoo/ ✅ |
| **Type** | Evaluation script | Test wrapper |
| **Related Folder** | None (create new) | tests/promptfoo/ (exists) |

---

## 📝 **Summary**

### **evaluate_chatbot.py:**
- **What:** LangSmith evaluation script
- **Current:** Root directory ❌
- **Move to:** `tests/evaluation/` ✅
- **Reason:** Evaluation/testing script, not production code

### **promptfoo_wrapper.py:**
- **What:** Promptfoo test wrapper
- **Current:** Root directory ❌
- **Move to:** `tests/promptfoo/` ✅
- **Reason:** Belongs with Promptfoo config and tests

---

## ✅ **Recommendation**

**Move both files:**
1. ✅ Create `tests/evaluation/` folder
2. ✅ Move `evaluate_chatbot.py` → `tests/evaluation/`
3. ✅ Move `promptfoo_wrapper.py` → `tests/promptfoo/`
4. ✅ Update imports in `promptfoo_wrapper.py`
5. ✅ Create README files
6. ✅ Update .gitignore

**Result:**
- ✅ Clean root directory
- ✅ Logical organization
- ✅ All tests/evaluations in `tests/`
- ✅ Professional structure

---

## 🚀 **Next Steps**

**Would you like me to:**
1. Create `tests/evaluation/` folder
2. Move both files
3. Update imports
4. Create README files
5. Update .gitignore

**Just say "yes" and I'll do it!** 🎯
