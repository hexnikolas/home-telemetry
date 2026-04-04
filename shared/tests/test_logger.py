import pytest
import sys
from io import StringIO
from logger.logging_config import setup_logging_json, setup_logging_colored


class TestLoggingSetup:
    """Test logging configuration"""

    def test_logging_json_setup(self):
        """Test JSON logging setup"""
        logger = setup_logging_json("test-service")
        assert logger is not None
        # Logger should be configured
        assert hasattr(logger, 'info')
        assert hasattr(logger, 'debug')
        assert hasattr(logger, 'error')
        assert hasattr(logger, 'warning')

    def test_logging_colored_setup(self):
        """Test colored logging setup"""
        logger = setup_logging_colored("test-service")
        assert logger is not None
        # Logger should be configured
        assert hasattr(logger, 'info')
        assert hasattr(logger, 'debug')
        assert hasattr(logger, 'error')
        assert hasattr(logger, 'warning')

    def test_logging_different_services(self):
        """Test creating loggers for different services"""
        logger1 = setup_logging_json("service-1")
        logger2 = setup_logging_json("service-2")
        
        assert logger1 is not None
        assert logger2 is not None

    def test_logging_with_different_levels(self):
        """Test setting different log levels"""
        # This would typically be tested by checking output
        logger_debug = setup_logging_json("test-debug", level="DEBUG")
        logger_info = setup_logging_json("test-info", level="INFO")
        logger_error = setup_logging_json("test-error", level="ERROR")
        
        assert logger_debug is not None
        assert logger_info is not None
        assert logger_error is not None


class TestLoggerBasicUsage:
    """Test basic logger usage"""

    def test_logger_info_message(self):
        """Test logging info message"""
        logger = setup_logging_json("test")
        # This would log to stdout/stderr, just verify it doesn't crash
        logger.info("Test info message")

    def test_logger_debug_message(self):
        """Test logging debug message"""
        logger = setup_logging_json("test")
        logger.debug("Test debug message")

    def test_logger_error_message(self):
        """Test logging error message"""
        logger = setup_logging_json("test")
        logger.error("Test error message")

    def test_logger_warning_message(self):
        """Test logging warning message"""
        logger = setup_logging_json("test")
        logger.warning("Test warning message")
