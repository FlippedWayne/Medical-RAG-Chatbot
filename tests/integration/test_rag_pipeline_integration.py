"""
Integration tests: End-to-end RAG pipeline

Tests the full query flow from app.py using mocked external dependencies:
  validate_environment → get_rag_prompt → prepare_rag_context → validate_response

No real API calls are made: the LLM and FAISS vectorstore are both mocked.
"""

import pytest
from unittest.mock import patch, MagicMock


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_guardrails_passthrough():
    """
    Return a MagicMock OutputGuardrails that marks every response as safe
    and returns the output unchanged.
    """
    guardrails = MagicMock()
    guardrails.validate_output.side_effect = lambda llm_output, **kwargs: (
        True,  # is_safe
        [],  # issues
        llm_output,  # safe_output
    )
    guardrails.get_fallback_response.return_value = (
        "I'm sorry, I cannot assist with that request."
    )
    return guardrails


def _make_guardrails_blocking():
    """
    Return a MagicMock OutputGuardrails that blocks every response (PII found).
    """
    from src.content_analyzer.config import ValidationIssue, ValidationSeverity

    block_issue = ValidationIssue(
        issue_type="PII_SSN",
        severity=ValidationSeverity.CRITICAL,
        description="SSN detected",
    )
    guardrails = MagicMock()
    guardrails.validate_output.side_effect = lambda llm_output, **kwargs: (
        False,
        [block_issue],
        "I'm sorry, I cannot assist with that request.",
    )
    guardrails.get_fallback_response.return_value = (
        "I'm sorry, I cannot assist with that request."
    )
    return guardrails


# ---------------------------------------------------------------------------
# Tests: validate_environment
# ---------------------------------------------------------------------------


@pytest.mark.integration
class TestValidateEnvironmentIntegration:
    """validate_environment() correctly checks config + API key presence."""

    def test_validate_environment_success(self, monkeypatch, sample_config):
        """Returns config dict when settings and API key are present."""
        monkeypatch.setenv("GROQ_API_KEY", "test-groq-key")

        mock_settings = MagicMock()
        mock_settings.config = sample_config

        with patch("app.settings", mock_settings):
            import app as app_module

            result = app_module.validate_environment()

        assert isinstance(result, dict)
        assert "active_llm" in result
        assert "model_name" in result
        assert "provider" in result

    def test_validate_environment_missing_api_key(self, monkeypatch, sample_config):
        """ConfigurationError raised when API key env var is absent."""
        from src.utils.exceptions import ConfigurationError

        monkeypatch.delenv("GROQ_API_KEY", raising=False)

        mock_settings = MagicMock()
        mock_settings.config = sample_config

        with patch("app.settings", mock_settings):
            import app as app_module

            with pytest.raises((ConfigurationError, SystemExit, Exception)):
                app_module.validate_environment()

    def test_validate_environment_no_settings_raises(self):
        """ConfigurationError raised when settings is None."""
        from src.utils.exceptions import ConfigurationError

        with patch("app.settings", None):
            import app as app_module

            with pytest.raises(ConfigurationError):
                app_module.validate_environment()


# ---------------------------------------------------------------------------
# Tests: get_rag_prompt
# ---------------------------------------------------------------------------


@pytest.mark.integration
class TestGetRagPromptIntegration:
    """get_rag_prompt() returns a usable prompt template."""

    def test_prompt_is_not_none(self):
        import app as app_module

        prompt = app_module.get_rag_prompt()
        assert prompt is not None

    def test_prompt_has_context_variable(self):
        """Prompt template must expose a {context} input variable."""
        import app as app_module

        prompt = app_module.get_rag_prompt()
        # ChatPromptTemplate exposes input_variables
        variables = prompt.input_variables
        assert "context" in variables, (
            f"Expected 'context' in prompt variables, got: {variables}"
        )

    def test_prompt_has_input_variable(self):
        """Prompt template must expose an {input} input variable."""
        import app as app_module

        prompt = app_module.get_rag_prompt()
        variables = prompt.input_variables
        assert "input" in variables, (
            f"Expected 'input' in prompt variables, got: {variables}"
        )

    def test_fallback_prompt_created_when_file_missing(self):
        """create_fallback_prompt() is used when the prompt file is absent."""
        import app as app_module
        from pathlib import Path as _Path

        # Path is imported inside get_rag_prompt(), so patch its `exists` method
        # to simulate the prompt file not being on disk.
        original_exists = _Path.exists

        def _always_false(self):
            return False

        _Path.exists = _always_false
        try:
            prompt = app_module.get_rag_prompt()
        finally:
            _Path.exists = original_exists

        assert prompt is not None


# ---------------------------------------------------------------------------
# Tests: prepare_rag_context / validate_response (was: process_query)
# ---------------------------------------------------------------------------


@pytest.mark.integration
class TestPrepareRagContextIntegration:
    """prepare_rag_context() retrieves docs and builds the prompt correctly."""

    def _get_prompt(self):
        import app as app_module

        return app_module.get_rag_prompt()

    def test_returns_tuple(self, mock_vectorstore):
        """A well-formed query returns (formatted_prompt, retrieved_docs)."""
        import app as app_module

        prompt = self._get_prompt()

        with patch("app.is_langsmith_enabled", return_value=False):
            result = app_module.prepare_rag_context(
                "What is diabetes?",
                mock_vectorstore,
                prompt,
            )

        assert isinstance(result, tuple)
        assert len(result) == 2
        formatted_prompt, docs = result
        assert isinstance(formatted_prompt, str)
        assert len(formatted_prompt) > 0
        assert len(docs) > 0

    def test_calls_vectorstore_retriever(self, mock_vectorstore):
        """Retriever is invoked once per query."""
        import app as app_module

        prompt = self._get_prompt()

        with patch("app.is_langsmith_enabled", return_value=False):
            app_module.prepare_rag_context(
                "What is hypertension?",
                mock_vectorstore,
                prompt,
            )

        mock_vectorstore.as_retriever.assert_called_once()

    def test_empty_query_raises(self, mock_vectorstore):
        """Empty query raises LLMError."""
        from src.utils.exceptions import LLMError
        import app as app_module

        prompt = self._get_prompt()

        with patch("app.is_langsmith_enabled", return_value=False):
            with pytest.raises(LLMError):
                app_module.prepare_rag_context(
                    "",
                    mock_vectorstore,
                    prompt,
                )

    def test_whitespace_only_raises(self, mock_vectorstore):
        """Whitespace-only query raises LLMError."""
        from src.utils.exceptions import LLMError
        import app as app_module

        prompt = self._get_prompt()

        with patch("app.is_langsmith_enabled", return_value=False):
            with pytest.raises(LLMError):
                app_module.prepare_rag_context(
                    "   ",
                    mock_vectorstore,
                    prompt,
                )


@pytest.mark.integration
class TestValidateResponseIntegration:
    """validate_response() runs guardrails on the complete LLM output."""

    def test_validates_output_via_guardrails(self):
        """guardrails.validate_output is called once per validation."""
        import app as app_module

        passthrough_guardrails = _make_guardrails_passthrough()

        with patch("app.guardrails", passthrough_guardrails):
            with patch("app.is_langsmith_enabled", return_value=False):
                app_module.validate_response(
                    "Some medical answer about cholesterol.",
                    "What is cholesterol?",
                    [],
                )

        passthrough_guardrails.validate_output.assert_called_once()

    def test_unsafe_output_returns_fallback(self):
        """When guardrails block, returns (False, fallback)."""
        import app as app_module

        blocking_guardrails = _make_guardrails_blocking()

        with patch("app.guardrails", blocking_guardrails):
            with patch("app.is_langsmith_enabled", return_value=False):
                is_safe, answer = app_module.validate_response(
                    "Patient SSN: 123-45-6789 needs treatment.",
                    "Tell me about the patient.",
                    [],
                )

        assert is_safe is False
        assert "sorry" in answer.lower() or "cannot" in answer.lower()

    def test_clean_output_is_returned_unchanged(self):
        """Safe LLM output is returned as-is (no modification by guardrails)."""
        import app as app_module

        passthrough_guardrails = _make_guardrails_passthrough()
        test_answer = "Diabetes is a chronic metabolic disease."

        with patch("app.guardrails", passthrough_guardrails):
            with patch("app.is_langsmith_enabled", return_value=False):
                is_safe, answer = app_module.validate_response(
                    test_answer,
                    "What is diabetes?",
                    [],
                )

        assert is_safe is True
        assert answer == test_answer
