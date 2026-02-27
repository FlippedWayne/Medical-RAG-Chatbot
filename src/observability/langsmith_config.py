"""
LangSmith configuration and setup.

This module handles the configuration and initialization of LangSmith
for tracing and monitoring LangChain applications.
"""

import os
from typing import Optional
from langsmith import Client

# Use centralized logger
try:
    from ..utils.logger import get_logger

    logger = get_logger(__name__)
except ImportError:
    import logging

    logger = logging.getLogger(__name__)

# Global client instance
_langsmith_client: Optional[Client] = None


def configure_langsmith(
    api_key: Optional[str] = None,
    project_name: str = "medical-chatbot",
    endpoint: Optional[str] = None,
    enable_tracing: bool = True,
) -> bool:
    """
    Configure LangSmith for the application.

    Args:
        api_key: LangSmith API key (defaults to LANGSMITH_API_KEY env var)
        project_name: Project name for organizing traces
        endpoint: LangSmith API endpoint (optional)
        enable_tracing: Whether to enable tracing

    Returns:
        bool: True if LangSmith is successfully configured, False otherwise
    """
    global _langsmith_client

    try:
        # Get API key from parameter or environment
        api_key = api_key or os.environ.get("LANGSMITH_API_KEY")

        if not api_key:
            logger.info("LangSmith API key not found. Tracing will be disabled.")
            return False

        # Set environment variables for LangChain automatic tracing
        os.environ["LANGCHAIN_TRACING_V2"] = "true" if enable_tracing else "false"
        os.environ["LANGCHAIN_API_KEY"] = api_key
        os.environ["LANGCHAIN_PROJECT"] = project_name

        if endpoint:
            os.environ["LANGCHAIN_ENDPOINT"] = endpoint

        # Initialize LangSmith client
        _langsmith_client = Client(api_key=api_key)

        logger.info(f"✅ LangSmith configured successfully for project: {project_name}")
        logger.info(f"📊 Tracing enabled: {enable_tracing}")

        return True

    except Exception as e:
        logger.warning(f"Failed to configure LangSmith: {str(e)}")
        logger.info("Application will continue without LangSmith tracing")
        return False


def is_langsmith_enabled() -> bool:
    """
    Check if LangSmith is enabled and configured.

    Returns:
        bool: True if LangSmith is enabled, False otherwise
    """
    return (
        os.environ.get("LANGCHAIN_TRACING_V2", "").lower() == "true"
        and os.environ.get("LANGCHAIN_API_KEY") is not None
    )


def get_langsmith_client() -> Optional[Client]:
    """
    Get the LangSmith client instance.

    Returns:
        Optional[Client]: LangSmith client if configured, None otherwise
    """
    return _langsmith_client


def disable_tracing():
    """Temporarily disable LangSmith tracing."""
    os.environ["LANGCHAIN_TRACING_V2"] = "false"
    logger.info("LangSmith tracing disabled")


def enable_tracing():
    """Re-enable LangSmith tracing."""
    if os.environ.get("LANGCHAIN_API_KEY"):
        os.environ["LANGCHAIN_TRACING_V2"] = "true"
        logger.info("LangSmith tracing enabled")
    else:
        logger.warning("Cannot enable tracing: LANGCHAIN_API_KEY not set")


def get_trace_url(run_id: str) -> Optional[str]:
    """
    Get the LangSmith trace URL for a specific run.

    Args:
        run_id: The run ID from LangChain

    Returns:
        Optional[str]: URL to view the trace in LangSmith
    """
    if not is_langsmith_enabled():
        return None

    project_name = os.environ.get("LANGCHAIN_PROJECT", "default")
    return f"https://smith.langchain.com/o/default/projects/p/{project_name}/r/{run_id}"
