"""
Integration tests: LLM Factory + Settings

Verifies that create_llm(), load_config(), get_generation_llm(), and
get_evaluation_llm() correctly integrate with the Settings module.

All actual LLM provider constructors are patched so no real API calls are made.
"""

import pytest
from unittest.mock import patch, MagicMock


@pytest.mark.integration
class TestLoadConfigIntegration:
    """load_config() loads the real config correctly via Settings."""

    def test_load_config_returns_dict(self):
        from src.model.llm_factory import load_config

        config = load_config()
        assert isinstance(config, dict)

    def test_load_config_has_llms_key(self):
        from src.model.llm_factory import load_config

        config = load_config()
        assert "llms" in config

    def test_load_config_has_embedding_key(self):
        from src.model.llm_factory import load_config

        config = load_config()
        assert "embedding" in config

    def test_load_config_has_vectorstore_key(self):
        from src.model.llm_factory import load_config

        config = load_config()
        assert "vectorstore" in config

    def test_load_config_active_llm_present(self):
        from src.model.llm_factory import load_config

        config = load_config()
        active = config.get("active_llm")
        assert active is not None
        assert active in config.get("llms", {})


@pytest.mark.integration
class TestCreateLLMIntegration:
    """create_llm() wires settings + provider correctly."""

    def test_create_groq_llm_with_valid_key(self, monkeypatch, sample_config):
        """create_llm returns a ChatGroq instance when GROQ_API_KEY is set."""
        monkeypatch.setenv("GROQ_API_KEY", "test-groq-key-xyz")

        mock_groq_instance = MagicMock()

        with patch("src.model.llm_factory.load_config", return_value=sample_config):
            with patch("langchain_groq.ChatGroq", return_value=mock_groq_instance):
                from src.model.llm_factory import create_llm

                llm = create_llm("groq", sample_config)

        assert llm is not None

    def test_create_llm_missing_api_key_raises(self, monkeypatch, sample_config):
        """ConfigurationError raised when the required API key env var is absent."""
        from src.utils.exceptions import ConfigurationError

        monkeypatch.delenv("GROQ_API_KEY", raising=False)

        with pytest.raises(ConfigurationError, match="GROQ_API_KEY"):
            from src.model.llm_factory import create_llm

            create_llm("groq", sample_config)

    def test_create_llm_unknown_name_raises(self, sample_config):
        """ConfigurationError raised for an LLM name not in config."""
        from src.model.llm_factory import create_llm
        from src.utils.exceptions import ConfigurationError

        with pytest.raises(ConfigurationError):
            create_llm("nonexistent_llm_xyz", sample_config)

    def test_create_llm_unsupported_provider_raises(self, monkeypatch):
        """ConfigurationError raised when the provider value is unknown."""
        from src.model.llm_factory import create_llm
        from src.utils.exceptions import ConfigurationError

        bad_config = {
            "active_llm": "bad_provider",
            "llms": {
                "bad_provider": {
                    "provider": "unknown_provider_xyz",
                    "model": "some-model",
                    "temperature": 0.5,
                    "max_tokens": 512,
                    "api_key_env": None,
                }
            },
        }
        with pytest.raises((ConfigurationError, Exception)):
            create_llm("bad_provider", bad_config)

    def test_create_llm_uses_active_llm_when_name_is_none(
        self, monkeypatch, sample_config
    ):
        """create_llm(None) picks up active_llm from config."""
        monkeypatch.setenv("GROQ_API_KEY", "test-key")
        mock_groq = MagicMock()

        with patch("src.model.llm_factory.load_config", return_value=sample_config):
            with patch("langchain_groq.ChatGroq", return_value=mock_groq):
                from src.model.llm_factory import create_llm

                llm = create_llm(None, sample_config)

        assert llm is not None


@pytest.mark.integration
class TestGetGenerationLLMIntegration:
    """get_generation_llm() and get_evaluation_llm() defer to settings correctly."""

    def test_get_generation_llm_uses_active_llm(self, monkeypatch, sample_config):
        monkeypatch.setenv("GROQ_API_KEY", "test-key")
        mock_groq = MagicMock()

        with patch("src.model.llm_factory.load_config", return_value=sample_config):
            with patch("langchain_groq.ChatGroq", return_value=mock_groq):
                from src.model.llm_factory import get_generation_llm

                llm = get_generation_llm(sample_config)

        assert llm is not None

    def test_get_evaluation_llm_returns_llm(self, monkeypatch, sample_config):
        monkeypatch.setenv("GROQ_API_KEY", "test-key")
        mock_groq = MagicMock()

        with patch("src.model.llm_factory.load_config", return_value=sample_config):
            with patch("langchain_groq.ChatGroq", return_value=mock_groq):
                from src.model.llm_factory import get_evaluation_llm

                llm = get_evaluation_llm(sample_config)

        assert llm is not None
