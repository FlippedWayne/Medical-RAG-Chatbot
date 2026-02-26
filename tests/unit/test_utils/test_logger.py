import pytest
import logging
import os
from src.utils.logger import get_logger

class TestLogger:
    def test_get_logger_basic(self):
        """Test basic logger creation"""
        logger = get_logger("test_module")
        assert isinstance(logger, logging.Logger)
        assert logger.name == "test_module"
        assert logger.level == logging.INFO

    def test_get_logger_with_file(self, tmp_path):
        """Test logger with file output"""
        log_file = tmp_path / "test.log"
        logger = get_logger("test_file_logger", log_to_file=True, custom_log_file=str(log_file))
        
        logger.info("Test message")
        
        # Verify file creation and content
        assert log_file.exists()
        content = log_file.read_text(encoding="utf-8")
        assert "Test message" in content

    def test_logger_emoji_support(self, caplog):
        """Test that logger handles emojis correctly"""
        logger = get_logger("test_emoji")
        logger.propagate = True  # Enable propagation for caplog
        
        with caplog.at_level(logging.INFO):
            logger.info("Testing emoji 🚀")
            
        assert "Testing emoji 🚀" in caplog.text

    def test_no_duplicate_handlers(self):
        """Test that getting logger multiple times doesn't duplicate handlers"""
        logger1 = get_logger("duplicate_test")
        initial_handlers = len(logger1.handlers)
        
        logger2 = get_logger("duplicate_test")
        assert len(logger2.handlers) == initial_handlers
        assert logger1 is logger2 
