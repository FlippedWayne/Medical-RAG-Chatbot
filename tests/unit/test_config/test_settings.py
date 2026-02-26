import pytest
import os
import yaml
import logging
from unittest.mock import patch, mock_open
from src.config.settings import Settings
from src.utils.exceptions import ConfigurationError

class TestSettings:
    
    @pytest.fixture
    def mock_settings_init(self, mock_env_vars, sample_config_data):
        """Mock settings initialization to avoid loading actual files"""
        with patch('src.config.settings.Settings._load_yaml_config', return_value=sample_config_data), \
             patch('src.config.settings.Settings._validate_config'):
             settings = Settings(config_path="dummy_path")
             return settings

    def test_settings_initialization(self, mock_settings_init):
        """Test basic settings initialization"""
        settings = mock_settings_init
        assert settings.config is not None
        assert settings.get("active_llm") == "groq"

    def test_load_yaml_config_success(self, tmp_path, sample_config_data):
        """Test loading configuration from a real (temp) YAML file"""
        config_file = tmp_path / "config.yaml"
        with open(config_file, 'w') as f:
            yaml.dump(sample_config_data, f)
        
        # Determine strict path to avoid searching in parents during test
        settings = Settings(config_path=str(config_file))
        assert settings.config["active_llm"] == "groq"
        assert settings.embedding_model == "BAAI/bge-base-en-v1.5"

    def test_load_yaml_config_not_found(self):
        """Test behavior when config file is missing"""
        # Should raise ConfigurationError if path is explicitly provided but missing
        with pytest.raises(ConfigurationError, match="Config file not found"):
            Settings(config_path="non_existent_config.yaml")

    def test_env_vars_properties(self, mock_settings_init, mock_env_vars):
        """Test property accessors for environment variables"""
        settings = mock_settings_init
        assert settings.groq_api_key == "test_groq_key"
        assert settings.langsmith_api_key == "test_langsmith_key"
        
    def test_config_properties(self, mock_settings_init):
         """Test property accessors for config values"""
         settings = mock_settings_init
         assert settings.vectorstore_path == "vectorstore/db_faiss"
         assert settings.embedding_model == "BAAI/bge-base-en-v1.5"
         assert settings.search_k == 3
         assert settings.max_retries == 3 

    def test_default_llm_model(self, mock_settings_init):
        """Test default LLM model selection logic"""
        settings = mock_settings_init
        # Mock config doesn't have llms section fully populated in sample_config_data for this test logic
        # Let's update the config for this specific test instance
        settings.config['llms'] = {
            'groq': {'model': 'llama-3.1-8b-instant'}
        }
        assert settings.default_llm_model == "llama-3.1-8b-instant"

    def test_validate_config_warning(self, caplog):
        """Test that validation logs warning for missing keys"""
        from src.config.settings import logger
        logger.propagate = True
        
        with caplog.at_level(logging.WARNING):
             with patch.object(Settings, '_load_yaml_config', return_value={'test': 'value'}): 
                Settings(config_path="dummy")
        
        assert "Recommended config keys missing" in caplog.text
