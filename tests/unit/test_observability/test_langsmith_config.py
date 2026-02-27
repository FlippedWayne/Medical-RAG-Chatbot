"""
Unit tests for src/observability/langsmith_config.py
"""

import os
from unittest.mock import patch, MagicMock


class TestConfigureLangsmith:
    def test_configure_langsmith_no_key(self, monkeypatch):
        """Returns False when no API key is present"""
        monkeypatch.delenv("LANGSMITH_API_KEY", raising=False)

        # Reload to reset module global
        import importlib
        import src.observability.langsmith_config as cfg_mod

        importlib.reload(cfg_mod)

        result = cfg_mod.configure_langsmith(api_key=None)
        assert result is False

    def test_configure_langsmith_success(self, monkeypatch):
        """Returns True, sets env vars, creates Client"""
        mock_client = MagicMock()

        with patch(
            "src.observability.langsmith_config.Client", return_value=mock_client
        ):
            import importlib
            import src.observability.langsmith_config as cfg_mod

            importlib.reload(cfg_mod)

            result = cfg_mod.configure_langsmith(
                api_key="test-key",
                project_name="test-project",
            )

        assert result is True
        assert os.environ.get("LANGCHAIN_TRACING_V2") == "true"
        assert os.environ.get("LANGCHAIN_PROJECT") == "test-project"
        assert os.environ.get("LANGCHAIN_API_KEY") == "test-key"

    def test_configure_langsmith_with_endpoint(self):
        """Sets LANGCHAIN_ENDPOINT when endpoint is provided"""
        with patch("src.observability.langsmith_config.Client", MagicMock()):
            import importlib
            import src.observability.langsmith_config as cfg_mod

            importlib.reload(cfg_mod)

            cfg_mod.configure_langsmith(
                api_key="test-key",
                endpoint="https://custom.langsmith.io",
            )

        assert os.environ.get("LANGCHAIN_ENDPOINT") == "https://custom.langsmith.io"

    def test_configure_langsmith_client_error(self):
        """Returns False when Client instantiation raises an exception"""
        with patch(
            "src.observability.langsmith_config.Client",
            side_effect=Exception("Connection error"),
        ):
            import importlib
            import src.observability.langsmith_config as cfg_mod

            importlib.reload(cfg_mod)

            result = cfg_mod.configure_langsmith(api_key="test-key")

        assert result is False


class TestIsLangsmithEnabled:
    def test_is_langsmith_enabled_true(self, monkeypatch):
        """Returns True when tracing env vars are set"""
        monkeypatch.setenv("LANGCHAIN_TRACING_V2", "true")
        monkeypatch.setenv("LANGCHAIN_API_KEY", "test-key")

        import importlib
        import src.observability.langsmith_config as cfg_mod

        importlib.reload(cfg_mod)

        assert cfg_mod.is_langsmith_enabled() is True

    def test_is_langsmith_enabled_false(self, monkeypatch):
        """Returns False when tracing is disabled"""
        monkeypatch.setenv("LANGCHAIN_TRACING_V2", "false")
        monkeypatch.delenv("LANGCHAIN_API_KEY", raising=False)

        import importlib
        import src.observability.langsmith_config as cfg_mod

        importlib.reload(cfg_mod)

        assert cfg_mod.is_langsmith_enabled() is False


class TestGetLangsmithClient:
    def test_get_langsmith_client_none(self):
        """Returns None when not configured"""
        import importlib
        import src.observability.langsmith_config as cfg_mod

        importlib.reload(cfg_mod)
        # _langsmith_client starts as None after reload
        assert cfg_mod.get_langsmith_client() is None


class TestTracingToggle:
    def test_disable_tracing(self):
        """disable_tracing sets LANGCHAIN_TRACING_V2=false"""
        from src.observability.langsmith_config import disable_tracing

        disable_tracing()
        assert os.environ.get("LANGCHAIN_TRACING_V2") == "false"

    def test_enable_tracing_with_key(self, monkeypatch):
        """enable_tracing sets LANGCHAIN_TRACING_V2=true when API key present"""
        monkeypatch.setenv("LANGCHAIN_API_KEY", "test-key")
        from src.observability.langsmith_config import enable_tracing

        enable_tracing()
        assert os.environ.get("LANGCHAIN_TRACING_V2") == "true"

    def test_enable_tracing_no_key(self, monkeypatch):
        """enable_tracing does not set true when API key absent"""
        monkeypatch.delenv("LANGCHAIN_API_KEY", raising=False)
        monkeypatch.setenv("LANGCHAIN_TRACING_V2", "false")
        from src.observability.langsmith_config import enable_tracing

        enable_tracing()
        assert os.environ.get("LANGCHAIN_TRACING_V2") == "false"


class TestGetTraceUrl:
    def test_get_trace_url_enabled(self, monkeypatch):
        """Returns formatted URL when LangSmith is enabled"""
        monkeypatch.setenv("LANGCHAIN_TRACING_V2", "true")
        monkeypatch.setenv("LANGCHAIN_API_KEY", "test-key")
        monkeypatch.setenv("LANGCHAIN_PROJECT", "my-project")

        import importlib
        import src.observability.langsmith_config as cfg_mod

        importlib.reload(cfg_mod)

        url = cfg_mod.get_trace_url("run-abc-123")
        assert url is not None
        assert "my-project" in url
        assert "run-abc-123" in url

    def test_get_trace_url_disabled(self, monkeypatch):
        """Returns None when LangSmith is disabled"""
        monkeypatch.setenv("LANGCHAIN_TRACING_V2", "false")
        monkeypatch.delenv("LANGCHAIN_API_KEY", raising=False)

        import importlib
        import src.observability.langsmith_config as cfg_mod

        importlib.reload(cfg_mod)

        assert cfg_mod.get_trace_url("run-abc-123") is None
