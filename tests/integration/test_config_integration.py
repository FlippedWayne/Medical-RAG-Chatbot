"""
Integration tests: Settings + config.yaml

Verifies that the Settings class correctly loads and parses the real
src/config/config.yaml file and exposes the expected properties.
"""

import pytest


@pytest.mark.integration
class TestSettingsConfigIntegration:
    """Settings loads and exposes values from the real config.yaml."""

    def test_settings_loads_real_config(self):
        """Settings initialises successfully using the real config.yaml."""
        from src.config.settings import Settings

        s = Settings()
        assert s.config is not None
        assert isinstance(s.config, dict)
        assert len(s.config) > 0

    def test_required_top_level_keys_present(self):
        """config.yaml contains all recommended top-level keys."""
        from src.config.settings import Settings

        s = Settings()
        for key in ("llms", "embedding", "vectorstore", "active_llm"):
            assert key in s.config, f"Missing expected key: '{key}'"

    def test_vectorstore_path_property(self):
        """vectorstore_path returns a non-empty string from config."""
        from src.config.settings import Settings

        s = Settings()
        path = s.vectorstore_path
        assert isinstance(path, str)
        assert len(path) > 0

    def test_embedding_model_property(self):
        """embedding_model returns a non-empty model name."""
        from src.config.settings import Settings

        s = Settings()
        model = s.embedding_model
        assert isinstance(model, str)
        assert len(model) > 0

    def test_default_llm_model_property(self):
        """default_llm_model resolves from the active_llm block."""
        from src.config.settings import Settings

        s = Settings()
        model = s.default_llm_model
        assert isinstance(model, str)
        assert len(model) > 0

    def test_search_k_property(self):
        """search_k returns a positive integer."""
        from src.config.settings import Settings

        s = Settings()
        k = s.search_k
        assert isinstance(k, int)
        assert k > 0

    def test_max_retries_property(self):
        """max_retries returns a positive integer."""
        from src.config.settings import Settings

        s = Settings()
        retries = s.max_retries
        assert isinstance(retries, int)
        assert retries > 0

    def test_active_llm_exists_in_llms_block(self):
        """The active_llm value is a key in the llms config block."""
        from src.config.settings import Settings

        s = Settings()
        active = s.config.get("active_llm")
        llms = s.config.get("llms", {})
        assert active in llms, (
            f"active_llm='{active}' is not defined under the 'llms' block"
        )

    def test_settings_bad_path_raises(self, tmp_path):
        """Settings raises ConfigurationError for a non-existent config path."""
        from src.config.settings import Settings
        from src.utils.exceptions import ConfigurationError

        bad_path = str(tmp_path / "nonexistent.yaml")
        with pytest.raises(ConfigurationError):
            Settings(config_path=bad_path)

    def test_settings_get_helper(self):
        """Settings.get() returns the value for an existing key."""
        from src.config.settings import Settings

        s = Settings()
        llms = s.get("llms")
        assert isinstance(llms, dict)
        assert len(llms) > 0

    def test_settings_get_default(self):
        """Settings.get() returns the default for a missing key."""
        from src.config.settings import Settings

        s = Settings()
        value = s.get("nonexistent_key_xyz", default="fallback")
        assert value == "fallback"

    def test_global_settings_singleton(self):
        """The module-level `settings` singleton is a Settings instance."""
        from src.config.settings import settings as global_settings
        from src.config.settings import Settings

        assert global_settings is not None
        assert isinstance(global_settings, Settings)
