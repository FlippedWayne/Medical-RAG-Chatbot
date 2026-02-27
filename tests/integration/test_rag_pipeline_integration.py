"""
Integration tests: End-to-end RAG pipeline

Tests the full query flow from app.py using mocked external dependencies:
  validate_environment → get_rag_prompt → process_query → OutputGuardrails

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
# Tests: process_query
# ---------------------------------------------------------------------------


@pytest.mark.integration
class TestProcessQueryIntegration:
    """process_query() wires vectorstore + LLM + guardrails correctly."""

    def _get_prompt(self):
        import app as app_module

        return app_module.get_rag_prompt()

    def test_process_query_returns_string(self, mock_llm, mock_vectorstore):
        """A well-formed query returns a non-empty answer string."""
        import app as app_module

        passthrough_guardrails = _make_guardrails_passthrough()
        prompt = self._get_prompt()

        with patch("app.guardrails", passthrough_guardrails):
            with patch("app.is_langsmith_enabled", return_value=False):
                answer = app_module.process_query(
                    "What is diabetes?",
                    mock_vectorstore,
                    mock_llm,
                    prompt,
                )

        assert isinstance(answer, str)
        assert len(answer) > 0

    def test_process_query_calls_vectorstore_retriever(
        self, mock_llm, mock_vectorstore
    ):
        """Retriever is invoked once per query."""
        import app as app_module

        passthrough_guardrails = _make_guardrails_passthrough()
        prompt = self._get_prompt()

        with patch("app.guardrails", passthrough_guardrails):
            with patch("app.is_langsmith_enabled", return_value=False):
                app_module.process_query(
                    "What is hypertension?",
                    mock_vectorstore,
                    mock_llm,
                    prompt,
                )

        mock_vectorstore.as_retriever.assert_called_once()

    def test_process_query_calls_llm_invoke(self, mock_llm, mock_vectorstore):
        """LLM.invoke() is called exactly once per query."""
        import app as app_module

        passthrough_guardrails = _make_guardrails_passthrough()
        prompt = self._get_prompt()

        with patch("app.guardrails", passthrough_guardrails):
            with patch("app.is_langsmith_enabled", return_value=False):
                app_module.process_query(
                    "Explain insulin resistance.",
                    mock_vectorstore,
                    mock_llm,
                    prompt,
                )

        mock_llm.invoke.assert_called_once()

    def test_process_query_empty_query_raises(self, mock_llm, mock_vectorstore):
        """Empty query raises LLMError."""
        from src.utils.exceptions import LLMError
        import app as app_module

        passthrough_guardrails = _make_guardrails_passthrough()
        prompt = self._get_prompt()

        with patch("app.guardrails", passthrough_guardrails):
            with patch("app.is_langsmith_enabled", return_value=False):
                with pytest.raises(LLMError):
                    app_module.process_query(
                        "",
                        mock_vectorstore,
                        mock_llm,
                        prompt,
                    )

    def test_process_query_whitespace_only_raises(self, mock_llm, mock_vectorstore):
        """Whitespace-only query raises LLMError."""
        from src.utils.exceptions import LLMError
        import app as app_module

        passthrough_guardrails = _make_guardrails_passthrough()
        prompt = self._get_prompt()

        with patch("app.guardrails", passthrough_guardrails):
            with patch("app.is_langsmith_enabled", return_value=False):
                with pytest.raises(LLMError):
                    app_module.process_query(
                        "   ",
                        mock_vectorstore,
                        mock_llm,
                        prompt,
                    )

    def test_process_query_validates_output_via_guardrails(
        self, mock_llm, mock_vectorstore
    ):
        """guardrails.validate_output is called once per query."""
        import app as app_module

        passthrough_guardrails = _make_guardrails_passthrough()
        prompt = self._get_prompt()

        with patch("app.guardrails", passthrough_guardrails):
            with patch("app.is_langsmith_enabled", return_value=False):
                app_module.process_query(
                    "What is cholesterol?",
                    mock_vectorstore,
                    mock_llm,
                    prompt,
                )

        passthrough_guardrails.validate_output.assert_called_once()

    def test_process_query_unsafe_output_returns_fallback(
        self, mock_llm_pii_response, mock_vectorstore
    ):
        """When guardrails block the LLM response, a fallback message is returned."""
        import app as app_module

        blocking_guardrails = _make_guardrails_blocking()
        prompt = self._get_prompt()

        with patch("app.guardrails", blocking_guardrails):
            with patch("app.is_langsmith_enabled", return_value=False):
                answer = app_module.process_query(
                    "Tell me about the patient.",
                    mock_vectorstore,
                    mock_llm_pii_response,
                    prompt,
                )

        assert "sorry" in answer.lower() or "cannot" in answer.lower()

    def test_process_query_clean_output_is_returned_unchanged(
        self, mock_llm, mock_vectorstore
    ):
        """Safe LLM output is returned as-is (no modification by guardrails)."""
        import app as app_module

        passthrough_guardrails = _make_guardrails_passthrough()
        prompt = self._get_prompt()

        with patch("app.guardrails", passthrough_guardrails):
            with patch("app.is_langsmith_enabled", return_value=False):
                answer = app_module.process_query(
                    "What is diabetes?",
                    mock_vectorstore,
                    mock_llm,
                    prompt,
                )

        # The mock LLM response should be returned unchanged
        expected = mock_llm.invoke.return_value.content
        assert answer == expected
