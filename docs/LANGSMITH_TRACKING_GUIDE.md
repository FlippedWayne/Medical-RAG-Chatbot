# 🔍 LangSmith Observability - Complete Tracking Guide

**Date:** 2026-02-09  
**Status:** ✅ Fully Configured

---

## 🎯 **What's Tracked in LangSmith**

Your Medical RAG Chatbot now tracks **EVERYTHING** in LangSmith, including all security guardrails!

---

## 📊 **Complete Tracking Overview**

### **1. RAG Query Processing** ✅

**Trace Name:** `medical_rag_query`

**What's Tracked:**
- ✅ Query input
- ✅ Query length
- ✅ Timestamp
- ✅ Model used (llama-3.1-8b-instant)
- ✅ Retriever K value (3 documents)

**Metadata:**
```json
{
  "query_length": 45,
  "query_preview": "What are the symptoms of diabetes?",
  "timestamp": "2026-02-09 12:38:33",
  "model": "llama-3.1-8b-instant",
  "retriever_k": 3
}
```

---

### **2. Document Retrieval** ✅

**What's Tracked:**
- ✅ Number of documents retrieved
- ✅ Document sources
- ✅ Retrieval K parameter

**Metadata:**
```json
{
  "num_docs_retrieved": 3,
  "doc_sources": ["medical_encyclopedia.pdf", "medical_encyclopedia.pdf", "medical_encyclopedia.pdf"],
  "retrieval_k": 3
}
```

---

### **3. Prompt Generation** ✅

**What's Tracked:**
- ✅ Prompt length
- ✅ Context length
- ✅ Formatted prompt

**Metadata:**
```json
{
  "prompt_length": 1250,
  "context_length": 1000
}
```

---

### **4. Guardrails Validation** ✅ **NEW!**

**Trace Name:** `guardrails_validation`

**What's Tracked:**
- ✅ All PII checks (Pattern + NER + Presidio)
- ✅ Toxic content detection
- ✅ Hallucination checks
- ✅ Medical disclaimer validation
- ✅ Safety decisions (block/allow)
- ✅ Issue counts and types

**Metadata:**
```json
{
  "component": "output_guardrails",
  "checks": ["pii", "toxic", "hallucination", "medical_disclaimer"],
  "guardrails_safe": true,
  "guardrails_issues_count": 1,
  "guardrails_issue_types": ["MEDICAL_DISCLAIMER_MISSING"]
}
```

**Tags:** `security`, `guardrails`, `validation`

---

## 🛡️ **Security Tracking Details**

### **PII Detection Tracking:**

| Detector | Tracked | Details |
|----------|---------|---------|
| **Pattern-based** | ✅ Yes | SSN, email, phone, credit cards |
| **NER-based** | ⚠️ Disabled | Names, organizations (spaCy not installed) |
| **Presidio ML** | ✅ Yes | 50+ PII types |

**Example Trace:**
```json
{
  "guardrails_validation": {
    "pii_pattern_detected": 0,
    "pii_presidio_detected": 1,
    "pii_types": ["PERSON"],
    "blocked": false
  }
}
```

---

### **Toxic Content Tracking:**

**Tracked:**
- ✅ Toxicity score
- ✅ Toxic categories (toxicity, severe_toxicity, obscene, threat, insult, identity_attack)
- ✅ Block decision

**Example Trace:**
```json
{
  "toxic_content": {
    "toxicity_score": 0.15,
    "categories": {
      "toxicity": 0.15,
      "severe_toxicity": 0.01,
      "obscene": 0.02
    },
    "blocked": false
  }
}
```

---

### **Hallucination Tracking:**

**Tracked:**
- ✅ Hallucination patterns detected
- ✅ Context comparison
- ✅ Confidence scores

**Example Trace:**
```json
{
  "hallucination_check": {
    "patterns_found": 0,
    "context_match": true,
    "issues": []
  }
}
```

---

### **Medical Disclaimer Tracking:**

**Tracked:**
- ✅ Disclaimer presence
- ✅ Disclaimer added (yes/no)
- ✅ Medical advice detected

**Example Trace:**
```json
{
  "medical_disclaimer": {
    "disclaimer_present": false,
    "disclaimer_added": true,
    "medical_advice_detected": true
  }
}
```

---

## 📈 **What You'll See in LangSmith**

### **Trace Structure:**

```
medical_rag_query (Root Trace)
├── Document Retrieval
│   ├── Retrieved 3 documents
│   └── Sources: [medical_encyclopedia.pdf]
│
├── Prompt Generation
│   ├── Prompt length: 1250 chars
│   └── Context length: 1000 chars
│
├── LLM Invocation
│   ├── Model: llama-3.1-8b-instant
│   ├── Input tokens: 350
│   ├── Output tokens: 150
│   └── Response time: 2.5s
│
└── guardrails_validation ← NEW!
    ├── PII Check
    │   ├── Pattern: 0 issues
    │   └── Presidio: 0 issues
    │
    ├── Toxic Check
    │   └── Score: 0.05 (safe)
    │
    ├── Hallucination Check
    │   └── 0 issues
    │
    └── Medical Disclaimer
        └── Added ✅
```

---

## 🔍 **How to View in LangSmith**

### **Step 1: Access LangSmith**
1. Go to: https://smith.langchain.com
2. Login with your account
3. Select project: **medical-chatbot**

### **Step 2: View Traces**
1. Click on "Traces" tab
2. You'll see all queries with timestamps
3. Click any trace to see details

### **Step 3: View Guardrails**
1. Open any trace
2. Look for **"guardrails_validation"** step
3. Click to see:
   - All checks performed
   - Issues found
   - Safety decisions
   - Metadata

### **Step 4: Filter by Security**
1. Use tags filter: `security`, `guardrails`
2. See only security-related traces
3. Analyze patterns

---

## 📊 **Metrics You Can Track**

### **Performance Metrics:**
- ✅ Average response time
- ✅ Token usage (input/output)
- ✅ Retrieval time
- ✅ LLM latency

### **Security Metrics:**
- ✅ PII detection rate
- ✅ Toxic content rate
- ✅ Hallucination rate
- ✅ Blocked responses count
- ✅ Disclaimer addition rate

### **Quality Metrics:**
- ✅ Documents retrieved per query
- ✅ Context relevance
- ✅ Answer quality
- ✅ Error rates

---

## 🎯 **Example Queries to Test**

### **Test 1: Normal Query**
```
Query: "What are the symptoms of diabetes?"

Expected Trace:
✅ Retrieval: 3 docs
✅ Guardrails: All pass
✅ Disclaimer: Added
✅ Output: Safe
```

### **Test 2: PII Query**
```
Query: "My SSN is 123-45-6789"

Expected Trace:
✅ Retrieval: 3 docs
❌ Guardrails: PII detected
❌ Output: Blocked
```

### **Test 3: Toxic Query**
```
Query: "Why are doctors useless?"

Expected Trace:
✅ Retrieval: 3 docs
⚠️ Guardrails: Toxic detected
⚠️ Output: Sanitized or blocked
```

---

## ✅ **What's Tracked vs Not Tracked**

### **✅ Tracked in LangSmith:**

| Component | Tracked | Details |
|-----------|---------|---------|
| **RAG Query** | ✅ Yes | Full trace |
| **Document Retrieval** | ✅ Yes | Docs + sources |
| **LLM Generation** | ✅ Yes | Tokens + latency |
| **Guardrails** | ✅ Yes | All checks |
| **PII Detection** | ✅ Yes | Pattern + Presidio |
| **Toxic Detection** | ✅ Yes | Detoxify scores |
| **Hallucination** | ✅ Yes | Pattern matching |
| **Medical Disclaimer** | ✅ Yes | Added/not added |
| **Safety Decisions** | ✅ Yes | Block/allow |

### **❌ NOT Tracked (External Tools):**

| Tool | Tracked | Reason |
|------|---------|--------|
| **Promptfoo** | ❌ No | Separate testing tool |
| **Giskard** | ❌ No | Separate testing tool |

**Note:** Promptfoo and Giskard are **testing tools**, not runtime components. They run separately and have their own reporting.

---

## 🚀 **How to Use This**

### **1. Monitor Production:**
- Check LangSmith daily
- Look for blocked responses
- Analyze PII/toxic patterns

### **2. Debug Issues:**
- Find failed queries
- See exact guardrail failures
- Understand why responses were blocked

### **3. Improve Quality:**
- Analyze retrieval quality
- Check disclaimer addition rate
- Monitor hallucination patterns

### **4. Security Audits:**
- Export security traces
- Review PII detections
- Validate guardrail effectiveness

---

## 📝 **Summary**

**What's Tracked:**
- ✅ RAG query processing
- ✅ Document retrieval
- ✅ LLM generation
- ✅ **Guardrails validation** (NEW!)
- ✅ PII detection (Pattern + Presidio)
- ✅ Toxic content detection
- ✅ Hallucination checks
- ✅ Medical disclaimer
- ✅ Safety decisions

**What's NOT Tracked:**
- ❌ Promptfoo tests (separate tool)
- ❌ Giskard tests (separate tool)

**How to View:**
1. Go to https://smith.langchain.com
2. Select project: "medical-chatbot"
3. View traces → Look for "guardrails_validation"

**Your complete RAG pipeline is now fully observable in LangSmith!** 🎉

---

## 🔧 **Files Modified**

| File | Change | Status |
|------|--------|--------|
| `src/content_analyzer/output_guardrails.py` | Added `@traceable` decorator | ✅ Done |
| `app.py` | Already has metadata logging | ✅ Done |

**All guardrails are now tracked in LangSmith!** 🛡️📊
