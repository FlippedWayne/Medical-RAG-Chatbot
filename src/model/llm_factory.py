"""
LLM Factory Module

This module provides a factory function to create LLM instances based on configuration.
Supports multiple providers: Groq, Google Gemini, OpenAI, HuggingFace, and Ollama.
"""

import os
from typing import Dict, Any
from dotenv import load_dotenv

# Import from new src structure
from ..utils.logger import get_logger
from ..utils.exceptions import ConfigurationError, LLMError
from ..config.settings import settings

load_dotenv()

# Initialize logger
logger = get_logger(__name__)


def load_config(config_path: str = None) -> Dict[str, Any]:
    """
    Load configuration from settings.

    Args:
        config_path: Path to config.yaml file (deprecated, uses settings now)

    Returns:
        Dict containing configuration
    """
    if config_path:
        logger.warning(
            "config_path parameter is deprecated. Using settings from src/config/"
        )

    if not settings or not settings.config:
        raise ConfigurationError(
            "Configuration not loaded. Check src/config/config.yaml"
        )

    return settings.config


def create_llm(llm_name: str = None, config: Dict[str, Any] = None):
    """
    Create an LLM instance based on configuration.

    Args:
        llm_name: Name of the LLM to use (e.g., 'groq', 'gemini', 'openai')
                 If None, uses active_llm from config
        config: Configuration dictionary. If None, loads from config.yaml

    Returns:
        LLM instance ready to use

    Raises:
        ValueError: If LLM provider is not supported or API key is missing
    """
    # Load config if not provided
    if config is None:
        config = load_config()

    # Use active_llm if llm_name not specified
    if llm_name is None:
        llm_name = config.get("active_llm", "groq")

    # Get LLM configuration
    llm_config = config["llms"].get(llm_name)
    if not llm_config:
        error_msg = f"LLM '{llm_name}' not found in config.yaml"
        logger.error(error_msg)
        raise ConfigurationError(error_msg)

    provider = llm_config["provider"]
    model = llm_config["model"]
    temperature = llm_config.get("temperature", 0.5)
    max_tokens = llm_config.get("max_tokens", 512)
    api_key_env = llm_config.get("api_key_env")

    logger.info(f"Creating LLM: {llm_name} (provider: {provider}, model: {model})")

    # Get API key from environment if required
    api_key = None
    if api_key_env:
        api_key = os.getenv(api_key_env)
        if not api_key:
            error_msg = (
                f"API key not found. Please set {api_key_env} environment variable."
            )
            logger.error(error_msg)
            raise ConfigurationError(error_msg)

    # Create LLM based on provider
    try:
        if provider == "groq":
            from langchain_groq import ChatGroq

            return ChatGroq(
                model=model,
                temperature=temperature,
                max_tokens=max_tokens,
                api_key=api_key,
            )

        elif provider == "google":
            from langchain_google_genai import ChatGoogleGenerativeAI

            return ChatGoogleGenerativeAI(
                model=model,
                temperature=temperature,
                max_output_tokens=max_tokens,
                google_api_key=api_key,
            )

        elif provider == "openai":
            from langchain_openai import ChatOpenAI

            return ChatOpenAI(
                model=model,
                temperature=temperature,
                max_tokens=max_tokens,
                api_key=api_key,
            )

        elif provider == "anthropic":
            from langchain_anthropic import ChatAnthropic

            return ChatAnthropic(
                model=model,
                temperature=temperature,
                max_tokens=max_tokens,
                api_key=api_key,
            )

        elif provider == "cohere":
            from langchain_cohere import ChatCohere

            return ChatCohere(
                model=model,
                temperature=temperature,
                max_tokens=max_tokens,
                cohere_api_key=api_key,
            )

        elif provider == "mistral":
            from langchain_mistralai import ChatMistralAI

            return ChatMistralAI(
                model=model,
                temperature=temperature,
                max_tokens=max_tokens,
                api_key=api_key,
            )

        elif provider == "together":
            from langchain_together import ChatTogether

            return ChatTogether(
                model=model,
                temperature=temperature,
                max_tokens=max_tokens,
                api_key=api_key,
            )

        elif provider == "perplexity":
            # Perplexity uses OpenAI-compatible API
            from langchain_openai import ChatOpenAI

            return ChatOpenAI(
                model=model,
                temperature=temperature,
                max_tokens=max_tokens,
                api_key=api_key,
                base_url="https://api.perplexity.ai",
            )

        elif provider == "huggingface":
            from langchain_huggingface import HuggingFaceEndpoint

            return HuggingFaceEndpoint(
                repo_id=model,
                temperature=temperature,
                max_new_tokens=max_tokens,
                huggingfacehub_api_token=api_key,
            )

        elif provider == "ollama":
            from langchain_community.llms import Ollama

            return Ollama(
                model=model,
                temperature=temperature,
                num_predict=max_tokens,
            )

        else:
            error_msg = f"Unsupported provider: {provider}"
            logger.error(error_msg)
            raise ConfigurationError(error_msg)

    except Exception as e:
        if isinstance(e, (ConfigurationError, LLMError)):
            raise
        error_msg = f"Failed to create LLM '{llm_name}': {str(e)}"
        logger.error(error_msg)
        raise LLMError(error_msg) from e


def get_evaluation_llm(config: Dict[str, Any] = None):
    """
    Get LLM instance for RAGAS evaluation.

    Args:
        config: Configuration dictionary. If None, loads from config.yaml

    Returns:
        LLM instance for evaluation
    """
    if config is None:
        config = load_config()

    eval_llm_name = config.get("evaluation_llm", config.get("active_llm", "groq"))
    return create_llm(eval_llm_name, config)


def get_generation_llm(config: Dict[str, Any] = None):
    """
    Get LLM instance for answer generation.

    Args:
        config: Configuration dictionary. If None, loads from config.yaml

    Returns:
        LLM instance for generation
    """
    if config is None:
        config = load_config()

    gen_llm_name = config.get("active_llm", "groq")
    return create_llm(gen_llm_name, config)


if __name__ == "__main__":
    # Test the factory
    print("Testing LLM Factory...")

    config = load_config()
    print(f"\nActive LLM: {config['active_llm']}")
    print(f"Evaluation LLM: {config['evaluation_llm']}")

    print("\nAvailable LLMs:")
    for llm_name, llm_config in config["llms"].items():
        print(f"  - {llm_name}: {llm_config['description']}")

    try:
        llm = get_generation_llm()
        print(f"\n✅ Successfully created generation LLM: {config['active_llm']}")
    except Exception as e:
        print(f"\n❌ Error creating LLM: {e}")
