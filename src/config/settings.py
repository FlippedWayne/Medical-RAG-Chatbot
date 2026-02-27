"""
Configuration management for Medical Chatbot
"""

import os
import yaml
from pathlib import Path
from typing import Dict, Any, Optional
from dotenv import load_dotenv

from ..utils.logger import get_logger
from ..utils.exceptions import ConfigurationError

logger = get_logger(__name__)


class Settings:
    """Application settings manager"""

    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize settings

        Args:
            config_path: Path to config.yaml file
        """
        # Load environment variables
        load_dotenv()

        # Load YAML config
        if config_path is None:
            # Try multiple locations
            possible_paths = [
                Path(__file__).parent / "config.yaml",  # src/config/config.yaml
                Path(__file__).parent.parent.parent / "config.yaml",  # root/config.yaml
            ]

            config_path = None
            for path in possible_paths:
                if path.exists():
                    config_path = path
                    break

            if config_path is None:
                logger.warning("config.yaml not found, using defaults")
                self.config = {}
                return

        self.config = self._load_yaml_config(config_path)
        self._validate_config()

    def _load_yaml_config(self, config_path: Path) -> Dict[str, Any]:
        """Load configuration from YAML file"""
        try:
            with open(config_path, "r") as f:
                config = yaml.safe_load(f)
                logger.info(f"Loaded configuration from {config_path}")
                return config or {}
        except FileNotFoundError:
            logger.error(f"Config file not found: {config_path}")
            raise ConfigurationError(f"Config file not found: {config_path}")
        except yaml.YAMLError as e:
            logger.error(f"Invalid YAML in config file: {e}")
            raise ConfigurationError(f"Invalid YAML: {e}")

    def _validate_config(self):
        """Validate required configuration"""
        if not self.config:
            return

        # Optional validation - only warn if keys are missing
        recommended_keys = ["llms", "embedding", "vectorstore"]
        missing = [key for key in recommended_keys if key not in self.config]

        if missing:
            logger.warning(f"Recommended config keys missing: {missing}")

    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value"""
        return self.config.get(key, default)

    @property
    def groq_api_key(self) -> str:
        """Get Groq API key from environment"""
        key = os.getenv("GROQ_API_KEY")
        if not key:
            logger.warning("GROQ_API_KEY not found in environment")
        return key

    @property
    def langsmith_api_key(self) -> Optional[str]:
        """Get LangSmith API key from environment (optional)"""
        return os.getenv("LANGSMITH_API_KEY")

    @property
    def google_api_key(self) -> Optional[str]:
        """Get Google API key from environment (optional)"""
        return os.getenv("GOOGLE_API_KEY")

    @property
    def vectorstore_path(self) -> str:
        """Get vector store path from config"""
        return self.config.get("vectorstore", {}).get("path", "vectorstore/db_faiss")

    @property
    def embedding_model(self) -> str:
        """Get embedding model from config"""
        return self.config.get("embedding", {}).get(
            "model", "sentence-transformers/all-MiniLM-L6-v2"
        )

    @property
    def default_llm_model(self) -> str:
        """Get default LLM model from config (based on active_llm)"""
        active_llm = self.config.get("active_llm", "groq")
        llm_config = self.config.get("llms", {}).get(active_llm, {})
        return llm_config.get("model", "llama-3.1-8b-instant")

    @property
    def search_k(self) -> int:
        """Get number of documents to retrieve"""
        return self.config.get("vectorstore", {}).get("search_k", 3)

    @property
    def max_retries(self) -> int:
        """Get max retries for operations"""
        return self.config.get("max_retries", 3)


# Global settings instance
try:
    settings = Settings()
except Exception as e:
    logger.error(f"Failed to initialize settings: {e}")
    settings = None
