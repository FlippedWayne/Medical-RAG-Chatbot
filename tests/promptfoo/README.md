# Promptfoo Tests

This folder contains Promptfoo configuration and wrapper for testing the Medical RAG Chatbot.

## Files

### `promptfoo_wrapper.py`
**Purpose:** Python wrapper for Promptfoo testing

**What it does:**
- ✅ Provides Promptfoo-compatible API
- ✅ Tests actual RAG chatbot
- ✅ Loads vectorstore and LLM
- ✅ Returns responses for Promptfoo assertions

**How to use:**

### **Command Line:**
```powershell
python tests/promptfoo/promptfoo_wrapper.py "What is diabetes?"
```

### **With Promptfoo:**
```powershell
promptfoo eval
```

---

### `promptfooconfig.yaml`
**Purpose:** Promptfoo configuration file

**Defines:**
- Test prompts
- Assertions
- Providers
- Output format

---

## Setup

### **1. Install Promptfoo:**
```powershell
npm install -g promptfoo
```

### **2. Verify Installation:**
```powershell
promptfoo --version
```

### **3. Create Vector Store:**
```powershell
python create_vectorstore.py
```

---

## Running Tests

### **Run Evaluation:**
```powershell
cd tests/promptfoo
promptfoo eval
```

### **View Results:**
```powershell
promptfoo view
```

---

## Wrapper API

### **Function: `test_chatbot(query: str)`**
Tests the chatbot with a query

**Args:**
- `query` - User question

**Returns:**
- Chatbot response (string)

**Example:**
```python
from tests.promptfoo.promptfoo_wrapper import test_chatbot

response = test_chatbot("What are the symptoms of diabetes?")
print(response)
```

---

### **Function: `call_api(prompt, options, context)`**
Promptfoo-compatible API function

**Args:**
- `prompt` - User query
- `options` - Optional configuration
- `context` - Optional context

**Returns:**
- Dict with `output` key

**Example:**
```python
from tests.promptfoo.promptfoo_wrapper import call_api

result = call_api("What is diabetes?")
print(result["output"])
```

---

## Configuration

### **promptfooconfig.yaml Structure:**
```yaml
prompts:
  - "What is {{topic}}?"
  - "Explain {{topic}} in simple terms"

providers:
  - python: tests/promptfoo/promptfoo_wrapper.py

tests:
  - vars:
      topic: diabetes
    assert:
      - type: contains
        value: glucose
      - type: contains
        value: blood sugar
```

---

## Assertions

### **Available Assertion Types:**

| Type | Description | Example |
|------|-------------|---------|
| `contains` | Output contains text | `value: "diabetes"` |
| `not-contains` | Output doesn't contain | `value: "error"` |
| `regex` | Matches regex | `value: "\\d+"` |
| `length` | Output length | `min: 50, max: 500` |
| `javascript` | Custom JS function | `value: "output.length > 20"` |

---

## Example Test Cases

### **Medical Definition:**
```yaml
- vars:
    query: "What is diabetes?"
  assert:
    - type: contains
      value: glucose
    - type: contains
      value: insulin
    - type: length
      min: 100
```

### **Symptoms:**
```yaml
- vars:
    query: "What are diabetes symptoms?"
  assert:
    - type: contains
      value: thirst
    - type: contains
      value: urination
    - type: not-contains
      value: error
```

### **Medical Disclaimer:**
```yaml
- vars:
    query: "Should I take insulin?"
  assert:
    - type: contains
      value: disclaimer
    - type: contains
      value: healthcare professional
```

---

## Troubleshooting

### **Import Errors:**
```python
# Wrapper automatically adds project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))
```

### **Vector Store Not Found:**
```powershell
# Create vector store first:
python create_vectorstore.py
```

### **Promptfoo Not Found:**
```powershell
# Install globally:
npm install -g promptfoo

# Or use npx:
npx promptfoo eval
```

---

## Related Documentation

- **Promptfoo Docs:** https://promptfoo.dev/docs/
- **Testing Guide:** `docs/TESTING_GUIDE.md`
- **Evaluation Tests:** `tests/evaluation/README.md`

---

**Test your prompts comprehensively with Promptfoo!** 🧪✅
