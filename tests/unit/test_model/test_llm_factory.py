"""
Unit tests for src/model/llm_factory.py
"""

import pytest
from unittest.mock import patch, MagicMock

from src.utils.exceptions import ConfigurationError, LLMError


class TestLoadConfig:
    def test_load_config_success(self, full_config_data):
        """load_config() returns dict from settings"""
        mock_settings = MagicMock()
        mock_settings.config = full_config_data

        with patch("src.model.llm_factory.settings", mock_settings):
            from src.model.llm_factory import load_config

            config = load_config()

        assert config["active_llm"] == "groq"
        assert "llms" in config

    def test_load_config_no_settings(self):
        """load_config() raises ConfigurationError when settings is None"""
        with patch("src.model.llm_factory.settings", None):
            from src.model.llm_factory import load_config

            with pytest.raises(ConfigurationError):
                load_config()

    def test_load_config_empty_config(self):
        """load_config() raises ConfigurationError when settings.config is empty/None"""
        mock_settings = MagicMock()
        mock_settings.config = None

        with patch("src.model.llm_factory.settings", mock_settings):
            from src.model.llm_factory import load_config

            with pytest.raises(ConfigurationError):
                load_config()


class TestCreateLLM:
    def _run_create_llm(
        self,
        llm_name,
        full_config_data,
        env_vars=None,
        provider_mock_path=None,
        mock_env=None,
    ):
        """Helper to run create_llm with mocked settings and provider."""
        mock_settings = MagicMock()
        mock_settings.config = full_config_data

        env_vars = env_vars or {}
        patches = [patch("src.model.llm_factory.settings", mock_settings)]

        mock_llm_cls = MagicMock()
        if provider_mock_path:
            patches.append(patch(provider_mock_path, mock_llm_cls))

        if env_vars:
            patches.append(patch.dict("os.environ", env_vars))

        with patches[0]:
            if len(patches) > 1:
                with patches[1]:
                    if len(patches) > 2:
                        with patches[2]:
                            from src.model.llm_factory import create_llm

                            return create_llm(
                                llm_name=llm_name, config=full_config_data
                            ), mock_llm_cls
                    else:
                        from src.model.llm_factory import create_llm

                        return create_llm(
                            llm_name=llm_name, config=full_config_data
                        ), mock_llm_cls
            else:
                from src.model.llm_factory import create_llm

                return create_llm(
                    llm_name=llm_name, config=full_config_data
                ), mock_llm_cls

    def test_create_llm_groq(self, full_config_data, monkeypatch):
        """Creates a Groq LLM instance"""
        monkeypatch.setenv("GROQ_API_KEY", "test-groq-key")
        mock_chat_groq = MagicMock()

        with (
            patch("src.model.llm_factory.settings") as ms,
            patch("langchain_groq.ChatGroq", mock_chat_groq),
        ):
            ms.config = full_config_data
            from src.model.llm_factory import create_llm

            create_llm(llm_name="groq", config=full_config_data)

        mock_chat_groq.assert_called_once()
        call_kwargs = mock_chat_groq.call_args.kwargs
        assert call_kwargs["model"] == "llama-3.1-8b-instant"

    def test_create_llm_openai(self, full_config_data, monkeypatch):
        """Creates an OpenAI LLM instance"""
        monkeypatch.setenv("OPENAI_API_KEY", "test-openai-key")
        mock_cls = MagicMock()

        with (
            patch("src.model.llm_factory.settings") as ms,
            patch("langchain_openai.ChatOpenAI", mock_cls),
        ):
            ms.config = full_config_data
            from src.model.llm_factory import create_llm

            create_llm(llm_name="openai", config=full_config_data)

        mock_cls.assert_called_once()

    def test_create_llm_google(self, full_config_data, monkeypatch):
        """Creates a Google Gemini LLM instance"""
        monkeypatch.setenv("GEMINI_API_KEY", "test-gemini-key")
        mock_cls = MagicMock()

        with (
            patch("src.model.llm_factory.settings") as ms,
            patch("langchain_google_genai.ChatGoogleGenerativeAI", mock_cls),
        ):
            ms.config = full_config_data
            from src.model.llm_factory import create_llm

            create_llm(llm_name="gemini", config=full_config_data)

        mock_cls.assert_called_once()

    def test_create_llm_anthropic(self, full_config_data, monkeypatch):
        """Creates an Anthropic Claude LLM instance"""
        monkeypatch.setenv("ANTHROPIC_API_KEY", "test-anthropic-key")
        mock_cls = MagicMock()

        with (
            patch("src.model.llm_factory.settings") as ms,
            patch("langchain_anthropic.ChatAnthropic", mock_cls),
        ):
            ms.config = full_config_data
            from src.model.llm_factory import create_llm

            create_llm(llm_name="claude", config=full_config_data)

        mock_cls.assert_called_once()

    def test_create_llm_ollama(self, full_config_data):
        """Creates Ollama LLM without requiring an API key"""
        mock_cls = MagicMock()

        with (
            patch("src.model.llm_factory.settings") as ms,
            patch("langchain_community.llms.Ollama", mock_cls),
        ):
            ms.config = full_config_data
            from src.model.llm_factory import create_llm

            create_llm(llm_name="ollama", config=full_config_data)

        mock_cls.assert_called_once()

    def test_create_llm_unsupported_provider(self, full_config_data):
        """Raises ConfigurationError for unknown provider"""
        with patch("src.model.llm_factory.settings") as ms:
            ms.config = full_config_data
            from src.model.llm_factory import create_llm

            with pytest.raises((ConfigurationError, LLMError)):
                create_llm(llm_name="bad_provider", config=full_config_data)

    def test_create_llm_missing_api_key(self, full_config_data, monkeypatch):
        """Raises ConfigurationError when required API key is missing"""
        monkeypatch.delenv("GROQ_API_KEY", raising=False)

        with (
            patch("src.model.llm_factory.settings") as ms,
            patch.dict("os.environ", {}, clear=False),
        ):
            ms.config = full_config_data
            from src.model.llm_factory import create_llm

            with pytest.raises(ConfigurationError, match="API key not found"):
                create_llm(llm_name="groq", config=full_config_data)

    def test_create_llm_unknown_name(self, full_config_data):
        """Raises ConfigurationError when llm_name not in config"""
        with patch("src.model.llm_factory.settings") as ms:
            ms.config = full_config_data
            from src.model.llm_factory import create_llm

            with pytest.raises(ConfigurationError):
                create_llm(llm_name="nonexistent_llm", config=full_config_data)


class TestHelperFunctions:
    def test_get_evaluation_llm(self, full_config_data, monkeypatch):
        """get_evaluation_llm returns LLM for evaluation_llm config key"""
        monkeypatch.setenv("OPENAI_API_KEY", "test-openai-key")
        mock_cls = MagicMock()

        with (
            patch("src.model.llm_factory.settings") as ms,
            patch("langchain_openai.ChatOpenAI", mock_cls),
        ):
            ms.config = full_config_data
            from src.model.llm_factory import get_evaluation_llm

            get_evaluation_llm(config=full_config_data)

        mock_cls.assert_called_once()

    def test_get_generation_llm(self, full_config_data, monkeypatch):
        """get_generation_llm returns LLM for active_llm config key"""
        monkeypatch.setenv("GROQ_API_KEY", "test-groq-key")
        mock_cls = MagicMock()

        with (
            patch("src.model.llm_factory.settings") as ms,
            patch("langchain_groq.ChatGroq", mock_cls),
        ):
            ms.config = full_config_data
            from src.model.llm_factory import get_generation_llm

            get_generation_llm(config=full_config_data)

        mock_cls.assert_called_once()
