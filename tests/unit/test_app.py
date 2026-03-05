"""
Unit tests for app.py
Tests are focused on pure functions (validate_environment, initialize_llm,
get_rag_prompt, prepare_rag_context, validate_response) that can be exercised without launching Streamlit.
Streamlit, LangChain, and all heavy dependencies are mocked.
"""

import pytest
import sys
from unittest.mock import patch, MagicMock, mock_open

# ---------------------------------------------------------------------------
# Streamlit must be mocked BEFORE any app import
# ---------------------------------------------------------------------------
streamlit_mock = MagicMock()
streamlit_mock.cache_resource = lambda func: func  # passthrough decorator
sys.modules.setdefault("streamlit", streamlit_mock)

# Also mock streamlit_authenticator which depends on streamlit internals
stauth_mock = MagicMock()
sys.modules.setdefault("streamlit_authenticator", stauth_mock)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_settings_mock(config_data):
    m = MagicMock()
    m.config = config_data
    m.vectorstore_path = config_data.get("vectorstore", {}).get("path", "vs/db")
    m.default_llm_model = "llama-3.1-8b-instant"
    m.embedding_model = "BAAI/bge-base-en-v1.5"
    m.max_retries = 3
    return m


def _groq_config():
    return {
        "active_llm": "groq",
        "llms": {
            "groq": {
                "provider": "groq",
                "model": "llama-3.1-8b-instant",
                "api_key_env": "GROQ_API_KEY",
            }
        },
        "vectorstore": {"path": "vectorstore/db_faiss"},
    }


# ---------------------------------------------------------------------------
# validate_environment
# ---------------------------------------------------------------------------


class TestValidateEnvironment:
    def test_validate_environment_success(self, monkeypatch):
        """Returns config dict when settings are valid and API key present"""
        monkeypatch.setenv("GROQ_API_KEY", "test-key")
        cfg = _groq_config()
        mock_settings = _make_settings_mock(cfg)

        with patch("app.settings", mock_settings):
            from app import validate_environment

            result = validate_environment()

        assert result["active_llm"] == "groq"
        assert result["model_name"] == "llama-3.1-8b-instant"

    def test_validate_environment_no_settings(self):
        """Raises ConfigurationError when settings is None"""
        with patch("app.settings", None):
            from app import validate_environment
            from src.utils.exceptions import ConfigurationError

            with pytest.raises(ConfigurationError):
                validate_environment()

    def test_validate_environment_no_config(self):
        """Raises ConfigurationError when settings.config is None"""
        mock_settings = MagicMock()
        mock_settings.config = None
        with patch("app.settings", mock_settings):
            from app import validate_environment
            from src.utils.exceptions import ConfigurationError

            with pytest.raises(ConfigurationError):
                validate_environment()

    def test_validate_environment_missing_api_key(self, monkeypatch):
        """Raises ConfigurationError when required API key not in env"""
        monkeypatch.delenv("GROQ_API_KEY", raising=False)
        cfg = _groq_config()
        mock_settings = _make_settings_mock(cfg)

        with patch("app.settings", mock_settings):
            from app import validate_environment
            from src.utils.exceptions import ConfigurationError

            with pytest.raises(ConfigurationError):
                validate_environment()

    def test_validate_environment_unknown_llm(self):
        """Raises ConfigurationError when active_llm not in llms config"""
        cfg = {
            "active_llm": "nonexistent_llm",
            "llms": {"groq": {"provider": "groq", "model": "llama"}},
            "vectorstore": {"path": "vs/db"},
        }
        mock_settings = _make_settings_mock(cfg)

        with patch("app.settings", mock_settings):
            from app import validate_environment
            from src.utils.exceptions import ConfigurationError

            with pytest.raises(ConfigurationError):
                validate_environment()


# ---------------------------------------------------------------------------
# initialize_llm
# ---------------------------------------------------------------------------


class TestInitializeLlm:
    def test_initialize_llm_success(self):
        """Calls create_llm and returns the mock LLM"""
        mock_llm_instance = MagicMock()
        config = {
            "active_llm": "groq",
            "model_name": "llama-3.1-8b-instant",
            "provider": "groq",
        }

        with patch("app.create_llm", return_value=mock_llm_instance) as mock_create:
            from app import initialize_llm

            result = initialize_llm(config)

        assert result is mock_llm_instance
        mock_create.assert_called_once_with(llm_name="groq")

    def test_initialize_llm_failure(self):
        """Raises LLMError when create_llm raises an exception"""
        config = {
            "active_llm": "groq",
            "model_name": "llama-3.1-8b-instant",
            "provider": "groq",
        }

        with patch("app.create_llm", side_effect=Exception("API error")):
            from app import initialize_llm
            from src.utils.exceptions import LLMError

            with pytest.raises(LLMError, match="Failed to initialize LLM"):
                initialize_llm(config)


# ---------------------------------------------------------------------------
# get_rag_prompt / create_fallback_prompt
# ---------------------------------------------------------------------------


class TestGetRagPrompt:
    def test_get_rag_prompt_from_file(self, tmp_path):
        """Loads prompt from file when file exists"""
        prompt_file = tmp_path / "medical_assistant.txt"
        prompt_file.write_text(
            "You are a medical assistant.\nContext: {context}\nQuestion: {input}"
        )

        with patch("app.Path") as mock_path_cls:
            mock_path_instance = MagicMock()
            mock_path_instance.exists.return_value = True
            mock_path_instance.__str__ = lambda s: str(prompt_file)
            mock_path_cls.return_value = mock_path_instance

            with patch(
                "builtins.open",
                mock_open(
                    read_data="You are a medical assistant.\nContext: {context}\nQuestion: {input}"
                ),
            ):
                from app import get_rag_prompt

                prompt = get_rag_prompt()

        assert prompt is not None

    def test_get_rag_prompt_fallback_when_file_missing(self):
        """Falls back to create_fallback_prompt when prompt file not found"""
        with patch("app.Path") as mock_path_cls:
            mock_path_instance = MagicMock()
            mock_path_instance.exists.return_value = False
            mock_path_cls.return_value = mock_path_instance

            from app import get_rag_prompt

            prompt = get_rag_prompt()

        assert prompt is not None

    def test_create_fallback_prompt_returns_template(self):
        """create_fallback_prompt returns a usable ChatPromptTemplate"""
        from app import create_fallback_prompt

        prompt = create_fallback_prompt()
        assert prompt is not None
        # The fallback template must have {context} and {input} variables
        assert "context" in prompt.input_variables
        assert "input" in prompt.input_variables


# ---------------------------------------------------------------------------
# prepare_rag_context / validate_response (was: process_query)
# ---------------------------------------------------------------------------


class TestPrepareRagContext:
    def _mock_vectorstore(self):
        vs = MagicMock()
        retriever = MagicMock()
        doc = MagicMock()
        doc.page_content = "Diabetes is managed through diet and exercise."
        doc.metadata = {"source": "medical_book.pdf"}
        retriever.invoke.return_value = [doc]
        vs.as_retriever.return_value = retriever
        return vs

    def _mock_prompt(self):
        prompt = MagicMock()
        prompt.format.return_value = "formatted prompt"
        return prompt

    def test_prepare_rag_context_success(self):
        """Returns (formatted_prompt, retrieved_docs) for a valid query"""
        vs = self._mock_vectorstore()
        prompt = self._mock_prompt()

        with patch("app.is_langsmith_enabled", return_value=False):
            from app import prepare_rag_context

            formatted_prompt, docs = prepare_rag_context(
                "What is diabetes?", vs, prompt
            )

        assert formatted_prompt == "formatted prompt"
        assert len(docs) == 1

    def test_prepare_rag_context_empty_query(self):
        """Raises LLMError for empty query string"""
        vs = self._mock_vectorstore()
        prompt = self._mock_prompt()

        with patch("app.is_langsmith_enabled", return_value=False):
            from app import prepare_rag_context
            from src.utils.exceptions import LLMError

            with pytest.raises((LLMError, ValueError)):
                prepare_rag_context("   ", vs, prompt)


class TestValidateResponse:
    def test_validate_response_safe(self):
        """Returns (True, output) for safe content"""
        mock_guardrails = MagicMock()
        mock_guardrails.validate_output.return_value = (
            True,
            [],
            "This is a safe medical answer.",
        )

        with (
            patch("app.guardrails", mock_guardrails),
            patch("app.is_langsmith_enabled", return_value=False),
        ):
            from app import validate_response

            is_safe, output = validate_response(
                "This is a safe medical answer.",
                "What is diabetes?",
                [],
            )

        assert is_safe is True
        assert "safe medical answer" in output

    def test_validate_response_blocked_by_guardrails(self):
        """Returns (False, fallback) when guardrails block the output"""
        from src.content_analyzer.config import ValidationIssue, ValidationSeverity

        pii_issue = ValidationIssue(
            issue_type="PII_SSN",
            severity=ValidationSeverity.CRITICAL,
            description="SSN detected",
            matched_text="12***89",
            position=8,
        )
        mock_guardrails = MagicMock()
        mock_guardrails.validate_output.return_value = (False, [pii_issue], "")
        mock_guardrails.get_fallback_response.return_value = (
            "I apologize, but the response contained sensitive information."
        )

        with (
            patch("app.guardrails", mock_guardrails),
            patch("app.is_langsmith_enabled", return_value=False),
        ):
            from app import validate_response

            is_safe, output = validate_response(
                "Patient SSN: 123-45-6789",
                "Tell me about SSN 123-45-6789",
                [],
            )

        assert is_safe is False
        assert "sensitive information" in output or "apologize" in output


# ---------------------------------------------------------------------------
# get_vectorstore
# ---------------------------------------------------------------------------


class TestGetVectorstore:
    def test_get_vectorstore_path_not_found(self, tmp_path):
        """Raises VectorStoreError when vectorstore path does not exist"""
        non_existent_path = str(tmp_path / "missing_db")

        with patch("app.DB_FAISS_PATH", non_existent_path):
            from app import get_vectorstore
            from src.utils.exceptions import VectorStoreError

            with pytest.raises(VectorStoreError):
                get_vectorstore()
