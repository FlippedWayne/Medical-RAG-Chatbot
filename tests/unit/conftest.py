import pytest
import os
from pathlib import Path
from unittest.mock import MagicMock


# ---------------------------------------------------------------------------
# Environment fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_env_vars(monkeypatch):
    """Mock environment variables for testing"""
    monkeypatch.setenv("GROQ_API_KEY", "test_groq_key")
    monkeypatch.setenv("LANGSMITH_API_KEY", "test_langsmith_key")
    monkeypatch.setenv("LANGCHAIN_TRACING_V2", "false")
    monkeypatch.setenv("LANGCHAIN_PROJECT", "test-project")


# ---------------------------------------------------------------------------
# Config fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def sample_config_data():
    """Minimal configuration data dictionary (for settings tests)"""
    return {
        "active_llm": "groq",
        "embedding": {
            "strategy": "single",
            "model": "BAAI/bge-base-en-v1.5",
            "primary": {
                "model": "BAAI/bge-base-en-v1.5"
            }
        },
        "vectorstore": {
            "path": "vectorstore/db_faiss",
            "chunk_size": 500,
            "chunk_overlap": 50
        }
    }


@pytest.fixture
def full_config_data():
    """Full configuration dict with all LLM providers (for llm_factory / app tests)"""
    return {
        "active_llm": "groq",
        "evaluation_llm": "openai",
        "max_retries": 3,
        "llms": {
            "groq": {
                "provider": "groq",
                "model": "llama-3.1-8b-instant",
                "temperature": 0.5,
                "max_tokens": 512,
                "api_key_env": "GROQ_API_KEY",
                "description": "Groq Llama",
            },
            "openai": {
                "provider": "openai",
                "model": "gpt-4o-mini",
                "temperature": 0.5,
                "max_tokens": 512,
                "api_key_env": "OPENAI_API_KEY",
                "description": "OpenAI GPT-4o mini",
            },
            "gemini": {
                "provider": "google",
                "model": "gemini-pro",
                "temperature": 0.5,
                "max_tokens": 512,
                "api_key_env": "GEMINI_API_KEY",
                "description": "Gemini Pro",
            },
            "claude": {
                "provider": "anthropic",
                "model": "claude-3-5-sonnet-20241022",
                "temperature": 0.5,
                "max_tokens": 512,
                "api_key_env": "ANTHROPIC_API_KEY",
                "description": "Claude 3.5 Sonnet",
            },
            "ollama": {
                "provider": "ollama",
                "model": "llama3:latest",
                "temperature": 0.5,
                "max_tokens": 512,
                "api_key_env": None,
                "description": "Local Ollama",
            },
            "bad_provider": {
                "provider": "unknown_xyz",
                "model": "some-model",
                "temperature": 0.5,
                "max_tokens": 512,
                "api_key_env": None,
                "description": "Unsupported provider",
            },
        },
        "embedding": {
            "strategy": "single",
            "model": "BAAI/bge-base-en-v1.5",
            "primary": {"model": "BAAI/bge-base-en-v1.5"},
        },
        "vectorstore": {
            "path": "vectorstore/db_faiss",
            "search_k": 3,
        },
    }


# ---------------------------------------------------------------------------
# LLM fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_llm():
    """A simple MagicMock that pretends to be an LLM"""
    llm = MagicMock()
    response = MagicMock()
    response.content = "This is a test medical answer."
    llm.invoke.return_value = response
    return llm


# ---------------------------------------------------------------------------
# Content text fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def clean_text():
    return "Diabetes is managed through diet, exercise, and regular monitoring."


@pytest.fixture
def pii_text():
    return (
        "Patient John Doe, email: john.doe@email.com, "
        "phone: 555-123-4567, SSN: 123-45-6789"
    )


@pytest.fixture
def toxic_text():
    return "You are a stupid idiot and I hate you!"
