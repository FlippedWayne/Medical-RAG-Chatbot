# 🏥 Medical RAG Chatbot

A production-grade **Retrieval-Augmented Generation (RAG)** chatbot for medical Q&A, built with LangChain, FAISS, and Streamlit. Supports 15+ LLM providers and includes content safety guardrails, LangSmith observability, and RAGAS evaluation.

---

## ✨ Features

- 🧠 **RAG Pipeline** — Answers grounded in your medical PDF documents via FAISS semantic search
- 🤖 **Multi-Provider LLM** — Switch between Groq, OpenAI, Gemini, Claude, Mistral, Cohere, Ollama, and more via one config line
- 🛡️ **Content Safety** — Dual-mode PII detection (Regex + Presidio) and toxic content filtering (Word-list + Detoxify ML)
- 📊 **Observability** — LangSmith tracing, user feedback collection, and RAGAS evaluation metrics
- 🔍 **Advanced Embeddings** — BGE primary model with optional ensemble/hybrid strategies

---

## 🚀 Quick Start

### 1. Prerequisites

- Python 3.13+
- [`uv`](https://github.com/astral-sh/uv) package manager

### 2. Install Dependencies

```bash
uv sync
```

### 3. Configure Environment

```bash
cp .env.example .env
```

Edit `.env` and set your API keys:

```env
GROQ_API_KEY=your_groq_api_key_here

# Optional: for LangSmith observability
LANGSMITH_API_KEY=ls_your_api_key_here
LANGCHAIN_TRACING_V2=true
LANGCHAIN_PROJECT=medical-chatbot
```

### 4. Add Your Medical PDFs

Place PDF files in the `data/` directory.

### 5. Create the Vector Store

```bash
uv run python create_vectorstore.py
```

### 6. Run the Chatbot

```bash
uv run streamlit run app.py
```

Open [http://localhost:8501](http://localhost:8501) in your browser.

---

## ⚙️ Configuration

All settings live in **`src/config/config.yaml`**.

### Switch LLM Provider

Change the `active_llm` field to any supported provider:

```yaml
active_llm: "groq"   # Change to: openai, gemini, claude, mistral, ollama, etc.
```

### Supported LLM Providers

| Key | Provider | Model |
|-----|----------|-------|
| `groq` | Groq | llama-3.1-8b-instant |
| `groq_llama_70b` | Groq | llama-3.1-70b-versatile |
| `openai` | OpenAI | gpt-4o-mini |
| `openai_gpt4` | OpenAI | gpt-4o |
| `gemini` | Google | gemini-pro |
| `claude` | Anthropic | claude-3-5-sonnet |
| `mistral` | Mistral AI | mistral-large |
| `cohere` | Cohere | command-r-plus |
| `ollama` | Local Ollama | llama3 |
| `huggingface` | HuggingFace | gpt2 |

Add the corresponding API key in `.env` for the chosen provider.

### Embedding Strategy

```yaml
embedding:
  strategy: "single"    # Options: single | ensemble | hybrid
```

---

## 🗂️ Project Structure

```
Medical-chatbot/
├── app.py                      # Streamlit UI & RAG pipeline
├── create_vectorstore.py       # One-time PDF ingestion → FAISS
├── data/                       # Place your PDF documents here
├── vectorstore/                # Generated FAISS vector store
├── src/
│   ├── config/
│   │   ├── config.yaml         # All configuration (LLMs, embeddings, vectorstore)
│   │   └── settings.py         # Settings singleton
│   ├── model/
│   │   └── llm_factory.py      # Multi-provider LLM factory
│   ├── content_analyzer/
│   │   ├── validator.py        # Content validation orchestrator
│   │   ├── pii_detector.py     # Regex-based PII detection
│   │   ├── pii_detector_presidio.py  # ML-based PII detection
│   │   ├── toxic_detector.py   # Word-list toxic content detection
│   │   ├── toxic_detector_ml.py      # Detoxify ML toxic detection
│   │   └── output_guardrails.py      # LLM output safety wrapper
│   ├── observability/
│   │   ├── langsmith_config.py # LangSmith setup
│   │   ├── tracing.py          # @trace_chain decorator & feedback
│   │   ├── evaluation.py       # LangSmith dataset evaluation
│   │   └── monitoring.py       # Monitoring utilities
│   ├── prompts/
│   │   └── medical_assistant.txt  # System prompt (9 medical + 5 security rules)
│   └── utils/
│       ├── logger.py           # Centralized logging
│       └── exceptions.py       # Custom exception hierarchy
├── tests/
│   ├── unit/                   # Unit tests (pytest)
│   ├── integration/            # Integration tests
│   ├── evaluation/             # RAGAS evaluation tests
│   ├── giskard/                # Giskard AI safety tests
│   └── promptfoo/              # Promptfoo LLM tests
├── evaluation/                 # Evaluation results
├── pyproject.toml              # Project metadata & dependencies
└── pytest.ini                  # Test configuration
```

---

## 🧪 Running Tests

```bash
# Run all unit tests with coverage
uv run pytest tests/unit/ -v --cov=src

# Run a specific test module
uv run pytest tests/unit/test_config/ -v
```

---

## 🛡️ Content Safety

Every LLM response is validated by `OutputGuardrails` before being shown to the user:

| Check | Method | Action |
|-------|--------|--------|
| PII Detection | Regex + Presidio ML | Block response |
| Toxic Content | Word-list + Detoxify ML | Block response |
| Hallucination | Context grounding check | Warn / block |
| Medical Disclaimer | Rule-based | Auto-inject |
| NER Check | spaCy `en_core_web_sm` | Warn (disabled by default) |

To enable spaCy NER:
```bash
uv run python -m spacy download en_core_web_sm
```
Then set `enable_ner_check=True` in `app.py`.

---

## 📊 Observability (LangSmith)

Set `LANGSMITH_API_KEY` in `.env` to enable:
- Full request tracing (retrieval → generation → guardrails)
- User 👍 / 👎 feedback collection
- Vector store creation pipeline tracing

View traces at [https://smith.langchain.com](https://smith.langchain.com).

---

## 📝 Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `GROQ_API_KEY` | If using Groq | Groq API key |
| `OPENAI_API_KEY` | If using OpenAI | OpenAI API key |
| `GEMINI_API_KEY` | If using Gemini | Google AI API key |
| `ANTHROPIC_API_KEY` | If using Claude | Anthropic API key |
| `MISTRAL_API_KEY` | If using Mistral | Mistral API key |
| `COHERE_API_KEY` | If using Cohere | Cohere API key |
| `LANGSMITH_API_KEY` | No (optional) | LangSmith observability |

---

## 📄 License

[MIT](LICENSE)
