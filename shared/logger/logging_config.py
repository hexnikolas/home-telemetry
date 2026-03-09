"""
Centralized logging configuration for home-telemetry services.

This module provides structured JSON logging with correlation IDs and context binding.
Designed for log aggregation systems (Loki, ELK, Datadog, etc.).

Usage:
    from shared.logging_config import setup_logging, get_logger
    
    logger = setup_logging("my-service")
    logger.info("Application started", extra={"user_id": "123"})
"""

import sys
import json
import logging
from datetime import datetime
from typing import Optional
from contextlib import contextmanager
import contextvars
from loguru import logger as _base_logger


# Context variables for correlation/tracing
_correlation_id: contextvars.ContextVar[str] = contextvars.ContextVar(
    "correlation_id", default=""
)
_request_id: contextvars.ContextVar[str] = contextvars.ContextVar(
    "request_id", default=""
)
_user_id: contextvars.ContextVar[str] = contextvars.ContextVar(
    "user_id", default=""
)


def get_correlation_id() -> str:
    """Get the current correlation ID from context."""
    return _correlation_id.get()


def set_correlation_id(correlation_id: str) -> None:
    """Set the correlation ID in context."""
    _correlation_id.set(correlation_id)


def get_request_id() -> str:
    """Get the current request ID from context."""
    return _request_id.get()


def set_request_id(request_id: str) -> None:
    """Set the request ID in context."""
    _request_id.set(request_id)


def get_user_id() -> str:
    """Get the current user ID from context."""
    return _user_id.get()


def set_user_id(user_id: str) -> None:
    """Set the user ID in context."""
    _user_id.set(user_id)


@contextmanager
def log_context(correlation_id: Optional[str] = None, request_id: Optional[str] = None, user_id: Optional[str] = None):
    """
    Context manager to set logging context for a block of code.
    
    Usage:
        with log_context(correlation_id="abc123", user_id="user456"):
            logger.info("Processing request")
    """
    old_correlation_id = _correlation_id.get()
    old_request_id = _request_id.get()
    old_user_id = _user_id.get()
    
    try:
        if correlation_id:
            _correlation_id.set(correlation_id)
        if request_id:
            _request_id.set(request_id)
        if user_id:
            _user_id.set(user_id)
        yield
    finally:
        _correlation_id.set(old_correlation_id)
        _request_id.set(old_request_id)
        _user_id.set(old_user_id)


def json_formatter(record: dict) -> str:
    """
    Format a log record as JSON for structured logging.
    
    Includes:
    - timestamp (ISO 8601)
    - level, name, function, line number
    - message and extra fields
    - correlation/request/user IDs from context
    """
    log_data = {
        "timestamp": record["message"].split(" ")[0] if " " in record["message"] else datetime.utcnow().isoformat(),
        "level": record["level"].name,
        "logger": record["name"],
        "function": record["function"],
        "line": record["line"],
        "message": record["message"],
    }
    
    # Add context variables
    if corr_id := get_correlation_id():
        log_data["correlation_id"] = corr_id
    if req_id := get_request_id():
        log_data["request_id"] = req_id
    if user := get_user_id():
        log_data["user_id"] = user
    
    # Add extra fields
    if record["extra"]:
        log_data["extra"] = record["extra"]
    
    # Add exception info if present
    if record["exception"]:
        log_data["exception"] = {
            "type": record["exception"].type.__name__,
            "message": str(record["exception"].value),
            "traceback": record["exc_info"],
        }
    
    return json.dumps(log_data)


def setup_logging(
    service_name: str,
    level: str = "INFO",
    json_output: bool = True,
    use_stderr: bool = True,
) -> logging.Logger:
    """
    Configure structured logging for a service.
    
    Args:
        service_name: Name of the service (e.g., "api", "worker", "scheduler")
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        json_output: If True, output JSON; otherwise use colored output
        use_stderr: If True, log to stderr; otherwise use stdout
    
    Returns:
        Configured logger instance
    
    Example:
        logger = setup_logging("home-telemetry-api")
        logger.info("Starting service", extra={"version": "0.1.0"})
    """
    # Remove any existing handlers
    _base_logger.remove()
    
    # Configure output sink
    sink = sys.stderr if use_stderr else sys.stdout
    
    # Configure format
    if json_output:
        format_string = "{message}"
        formatter = json_formatter
    else:
        # Colored output for development
        format_string = (
            "<level>{level: <8}</level> | "
            "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
            "<level>{message}</level>"
        )
        formatter = None
    
    # Add handler
    _base_logger.add(
        sink,
        format=format_string,
        level=level.upper(),
        colorize=not json_output,
        serialize=json_output,  # Use built-in JSON serialization
    )
    
    # Convert loguru logger to stdlib format for FastAPI/integrations
    # Bind service name to all log records
    logger = _base_logger.bind(service=service_name)
    
    return logger


# Quick setup for common patterns
def setup_logging_json(service_name: str, level: str = "INFO") -> logging.Logger:
    """Setup logging with JSON output for production."""
    return setup_logging(service_name, level=level, json_output=True, use_stderr=True)


def setup_logging_colored(service_name: str, level: str = "DEBUG") -> logging.Logger:
    """Setup logging with colored output for development."""
    return setup_logging(service_name, level=level, json_output=False, use_stderr=True)


# Export for convenience
logger = _base_logger
