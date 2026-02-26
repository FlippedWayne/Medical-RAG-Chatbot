# Evaluation Tests

This folder contains evaluation scripts for the Medical RAG Chatbot using LangSmith.

## Files

### `evaluate_chatbot.py`
**Purpose:** Comprehensive evaluation using LangSmith

**What it does:**
- ✅ Creates test datasets with medical examples
- ✅ Runs evaluations with custom evaluators
- ✅ Tracks results in LangSmith dashboard
- ✅ Generates evaluation reports

**Features:**
- **8 Medical Test Examples:**
  - Medical definitions (diabetes)
  - Symptoms queries
  - Treatment information
  - Policy queries
  - Personal data queries
  - Medical relationships
  - Complications

- **4 Custom Evaluators:**
  1. **Answer Relevance** - Checks if answer is substantial
  2. **Keyword Presence** - Verifies expected keywords
  3. **Response Length** - Ensures appropriate length (20-500 words)
  4. **No Error** - Confirms successful execution

**How to use:**

### **Create Dataset:**
```powershell
python tests/evaluation/evaluate_chatbot.py --create-dataset
```

### **Run Evaluation:**
```powershell
python tests/evaluation/evaluate_chatbot.py --run-eval
```

### **Custom Dataset Name:**
```powershell
python tests/evaluation/evaluate_chatbot.py --create-dataset --dataset-name my-test-dataset
python tests/evaluation/evaluate_chatbot.py --run-eval --dataset-name my-test-dataset
```

---

## Requirements

### **LangSmith API Key:**
```bash
# Add to .env file:
LANGSMITH_API_KEY=your_api_key_here
LANGCHAIN_TRACING_V2=true
LANGCHAIN_PROJECT=medical-chatbot-evaluators
```

### **Vector Store:**
Ensure vector store is created:
```powershell
python create_vectorstore.py
```

---

## Evaluation Process

### **1. Create Dataset**
```powershell
python tests/evaluation/evaluate_chatbot.py --create-dataset
```

**Output:**
```
📊 Creating dataset: medical-chatbot-test
✅ Dataset created successfully: <dataset_id>
📝 Total examples: 8
```

---

### **2. Run Evaluation**
```powershell
python tests/evaluation/evaluate_chatbot.py --run-eval
```

**What happens:**
1. Loads RAG chain (vectorstore + LLM + prompt)
2. Runs each test example through the chain
3. Applies 4 evaluators to each result
4. Tracks everything in LangSmith
5. Generates CSV report

**Output:**
```
🚀 Initializing RAG chain for evaluation...
🔬 Starting evaluation: medical_eval_groq
✅ Evaluation completed successfully
📊 View results at: https://smith.langchain.com/
```

---

## Evaluators Explained

### **1. Answer Relevance**
**Checks:** Answer is substantial (>20 characters)

**Score:**
- 1.0 = Relevant answer
- 0.0 = Too short or empty

---

### **2. Keyword Presence**
**Checks:** Expected keywords are in the answer

**Example:**
```python
Query: "What is diabetes?"
Expected keywords: ["blood sugar", "glucose", "insulin", "chronic"]
Score: (keywords found) / (total keywords)
```

**Score:**
- 1.0 = All keywords found
- 0.5 = Half keywords found
- 0.0 = No keywords found

---

### **3. Response Length**
**Checks:** Response is appropriate length

**Scoring:**
- 20-500 words = 1.0 (Good)
- <20 words = 0.3 (Too short)
- >500 words = 0.7 (Too long)

---

### **4. No Error**
**Checks:** Run completed without errors

**Score:**
- 1.0 = No errors
- 0.0 = Error occurred

---

## Results

### **Location:**
```
tests/evaluation/results/
├── eval_medical_eval_groq_<timestamp>.csv
└── .gitkeep
```

### **View in LangSmith:**
1. Go to: https://smith.langchain.com/
2. Select project: `medical-chatbot-evaluators`
3. View experiments and results

---

## Example Test Cases

### **Easy - Medical Definition:**
```python
{
    "inputs": {"query": "What is diabetes?"},
    "outputs": {
        "expected_keywords": ["blood sugar", "glucose", "insulin", "chronic"],
        "category": "medical_definition"
    }
}
```

### **Medium - Symptoms:**
```python
{
    "inputs": {"query": "What are the symptoms of diabetes?"},
    "outputs": {
        "expected_keywords": ["thirst", "urination", "hunger", "fatigue"],
        "category": "medical_symptoms"
    }
}
```

### **Hard - Medical Relationship:**
```python
{
    "inputs": {"query": "What is the relationship between diabetes and heart disease?"},
    "outputs": {
        "expected_keywords": ["diabetes", "heart", "cardiovascular", "risk"],
        "category": "medical_relationship"
    }
}
```

---

## Adding Custom Evaluators

### **Create evaluator function:**
```python
def my_custom_evaluator(run, example):
    """Custom evaluation logic"""
    output = run.outputs.get("output", "")
    
    # Your logic here
    score = 1.0 if condition else 0.0
    
    return {
        "key": "my_evaluator",
        "score": score,
        "comment": "Explanation"
    }
```

### **Add to evaluators list:**
```python
evaluators = [
    create_evaluator("my_evaluator", my_custom_evaluator),
    # ... other evaluators
]
```

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
# Check .env file has:
LANGSMITH_API_KEY=your_key
LANGCHAIN_TRACING_V2=true
```

### **Vector Store Not Found:**
```powershell
# Create vector store first:
python create_vectorstore.py
```

---

## Related Documentation

- **LangSmith Guide:** `docs/LANGSMITH_TRACKING_GUIDE.md`
- **Observability:** `docs/OBSERVABILITY_QUICKSTART.md`
- **Testing Guide:** `docs/TESTING_GUIDE.md`

---

**Evaluate your RAG system comprehensively with LangSmith!** 📊✅
