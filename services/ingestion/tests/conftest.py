"""
Pytest fixtures and configuration for ingestion service tests
"""
import os
import sys
from pathlib import Path
from unittest.mock import MagicMock

# Set required environment variables BEFORE importing app modules
os.environ.setdefault("RABBITMQ_URL", "amqp://guest:guest@localhost/")
os.environ.setdefault("LOG_FORMAT", "json")
os.environ.setdefault("QUEUE_NAME", "observations")

# Mock the shared logger before any app imports
sys.modules['shared'] = MagicMock()
sys.modules['shared.logger'] = MagicMock()
sys.modules['shared.logger.logging_config'] = MagicMock()

import pytest
from uuid import uuid4


@pytest.fixture
def sample_datastreams():
    """Provide sample datastream IDs for testing handlers"""
    return {
        "Temperature": str(uuid4()),
        "Humidity": str(uuid4()),
        "DewPoint": str(uuid4()),
        "Power": str(uuid4()),
        "Voltage": str(uuid4()),
        "Total": str(uuid4()),
    }


@pytest.fixture
def sample_sht40_payload():
    """Provide sample SHT40 sensor payload"""
    return {
        "Time": "2026-04-04T12:00:00",
        "SHT4X": {
            "Temperature": 22.5,
            "Humidity": 65.0,
            "DewPoint": 14.2,
        }
    }


@pytest.fixture
def sample_a1t_payload():
    """Provide sample A1T power sensor payload"""
    return {
        "Time": "2026-04-04T12:00:00",
        "ENERGY": {
            "Power": 250.5,
            "Voltage": 230.0,
            "Total": 1234.56,
        }
    }
