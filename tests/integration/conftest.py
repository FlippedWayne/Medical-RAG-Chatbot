"""
Shared fixtures for integration tests.

All external dependencies (LLM APIs, FAISS disk I/O) are mocked so that
integration tests run offline without real API keys or a built vector store.
"""
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch

from langchain_core.documents import Document


# ---------------------------------------------------------------------------
# Path fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def project_root() -> Path:
    """Return the repository root directory."""
    return Path(__file__).parent.parent.parent


# ---------------------------------------------------------------------------
# Config fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def sample_config() -> dict:
    """Full in-memory config dict — mirrors structure of config.yaml."""
    return {
        "active_llm": "groq",
        "evaluation_llm": "groq",
        "max_retries": 3,
        "llms": {
            "groq": {
                "provider": "groq",
                "model": "llama-3.1-8b-instant",
                "temperature": 0.5,
                "max_tokens": 512,
                "api_key_env": "GROQ_API_KEY",
                "description": "Groq Llama (integration test)",
            },
            "openai": {
                "provider": "openai",
                "model": "gpt-4o-mini",
                "temperature": 0.5,
                "max_tokens": 512,
                "api_key_env": "OPENAI_API_KEY",
                "description": "OpenAI GPT-4o mini (integration test)",
            },
        },
        "embedding": {
            "strategy": "single",
            "model": "sentence-transformers/all-MiniLM-L6-v2",
            "primary": {"model": "sentence-transformers/all-MiniLM-L6-v2"},
        },
        "vectorstore": {
            "path": "vectorstore/db_faiss",
            "search_k": 3,
            "chunk_size": 500,
            "chunk_overlap": 50,
        },
    }


# ---------------------------------------------------------------------------
# LLM fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_llm():
    """
    MagicMock LLM that returns a clean medical answer.
    Simulates what ChatGroq / ChatGoogleGenerativeAI returns.
    """
    llm = MagicMock()
    response = MagicMock()
    response.content = (
        "Diabetes is a chronic condition where the body cannot properly regulate blood sugar. "
        "It is managed through diet, exercise, medication, and regular monitoring. "
        "Please consult a healthcare professional for personalised advice."
    )
    llm.invoke.return_value = response
    return llm


@pytest.fixture
def mock_llm_pii_response():
    """MagicMock LLM whose response contains PII — triggers guardrails."""
    llm = MagicMock()
    response = MagicMock()
    response.content = (
        "Patient John Doe (john.doe@example.com, phone: 555-123-4567, "
        "SSN: 123-45-6789) has been diagnosed with Type 2 Diabetes."
    )
    llm.invoke.return_value = response
    return llm


# ---------------------------------------------------------------------------
# Vector store fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def fake_documents():
    """Two fake Document objects that represent retrieved medical context."""
    return [
        Document(
            page_content=(
                "Diabetes mellitus is a group of metabolic diseases characterised "
                "by hyperglycaemia resulting from defects in insulin secretion."
            ),
            metadata={"source": "medical_textbook.pdf", "page": 42},
        ),
        Document(
            page_content=(
                "Type 2 diabetes is managed with lifestyle changes, oral medications, "
                "and sometimes insulin therapy."
            ),
            metadata={"source": "medical_textbook.pdf", "page": 43},
        ),
    ]


@pytest.fixture
def mock_vectorstore(fake_documents):
    """
    MagicMock FAISS vectorstore.
    as_retriever().invoke() returns the two fake documents above.
    """
    retriever = MagicMock()
    retriever.invoke.return_value = fake_documents

    vs = MagicMock()
    vs.as_retriever.return_value = retriever
    return vs


# ---------------------------------------------------------------------------
# Content Analyzer fixture
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def content_validator():
    """
    Real ContentValidator instance using regex-only mode.
    Avoids heavy ML dependencies (Presidio, Detoxify, spaCy).
    """
    from src.content_analyzer import ContentValidator, ValidationConfig
    from src.content_analyzer.config import PIIDetectionMode, ToxicDetectionMode

    config = ValidationConfig(
        enable_pii_detection=True,
        enable_toxic_detection=True,
        pii_detection_mode=PIIDetectionMode.REGEX,
        toxic_detection_mode=ToxicDetectionMode.WORDLIST,
        pii_block_on_critical=True,
        pii_block_on_high=False,
        toxic_block_on_critical=True,
        toxic_block_on_high=False,
        log_issues=False,
        verbose=False,
    )
    return ContentValidator(config)
