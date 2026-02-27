"""
Centralized logging configuration for Medical Chatbot
"""

import logging
import sys
from pathlib import Path
from datetime import datetime
from typing import Optional


def setup_logger(
    name: str, log_file: Optional[str] = None, level: int = logging.INFO
) -> logging.Logger:
    """
    Set up a logger with console and file handlers

    Args:
        name: Logger name (usually __name__)
        log_file: Optional log file path
        level: Logging level

    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)

    # Clear existing handlers to prevent duplicates
    if logger.handlers:
        logger.handlers.clear()

    # Prevent propagation to avoid duplicate logs from parent loggers
    logger.propagate = False

    # Console handler with UTF-8 encoding for emoji support
    # Detect if running in Streamlit (which redirects stdout)
    import io

    is_streamlit = "streamlit" in sys.modules
    is_pytest = "pytest" in sys.modules

    if is_streamlit or is_pytest:
        # In Streamlit or pytest, use stdout directly
        utf8_stdout = sys.stdout
    else:
        # In regular Python, try to create UTF-8 wrapper for Windows console
        try:
            if (
                hasattr(sys.stdout, "buffer")
                and hasattr(sys.stdout.buffer, "closed")
                and not sys.stdout.buffer.closed
            ):
                utf8_stdout = io.TextIOWrapper(
                    sys.stdout.buffer,
                    encoding="utf-8",
                    errors="replace",
                    line_buffering=True,
                )
            else:
                utf8_stdout = sys.stdout
        except (AttributeError, ValueError):
            utf8_stdout = sys.stdout

    console_handler = logging.StreamHandler(utf8_stdout)
    console_handler.setLevel(level)
    console_format = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    console_handler.setFormatter(console_format)
    logger.addHandler(console_handler)

    # File handler (if specified)
    if log_file:
        log_path = Path("logs") / log_file
        log_path.parent.mkdir(parents=True, exist_ok=True)

        file_handler = logging.FileHandler(log_path, encoding="utf-8")
        file_handler.setLevel(level)
        file_format = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s"
        )
        file_handler.setFormatter(file_format)
        logger.addHandler(file_handler)

    return logger


def get_logger(
    name: str, log_to_file: bool = True, custom_log_file: str = None
) -> logging.Logger:
    """
    Get a logger with default configuration

    Args:
        name: Logger name (usually __name__)
        log_to_file: Whether to log to file
        custom_log_file: Optional custom log filename (e.g., "vector_creation.log")

    Returns:
        Configured logger instance
    """
    log_file = None
    if log_to_file:
        if custom_log_file:
            log_file = custom_log_file
        else:
            log_file = f"medical_chatbot_{datetime.now().strftime('%Y%m%d')}.log"

    return setup_logger(name=name, log_file=log_file, level=logging.INFO)


# Example usage
if __name__ == "__main__":
    logger = get_logger(__name__)
    logger.info("Logger initialized successfully")
    logger.debug("This is a debug message")
    logger.warning("This is a warning message")
    logger.error("This is an error message")
