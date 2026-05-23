import pytest
import os
from unittest.mock import MagicMock, patch
from datetime import datetime, timezone


@pytest.fixture
def jobs_env(monkeypatch):
    """Set up Jobs service environment variables."""
    monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/0")
    monkeypatch.setenv("API_URL", "http://api:8000")
    monkeypatch.setenv("API_CLIENT_ID", "jobs")
    monkeypatch.setenv("API_CLIENT_SECRET", "jobs-secret")
    monkeypatch.setenv("OPEN_METEO_LATITUDE", "37.7749")
    monkeypatch.setenv("OPEN_METEO_LONGITUDE", "-122.4194")
    monkeypatch.setenv("LOG_LEVEL", "DEBUG")
    monkeypatch.setenv("OUTSIDE_TEMP_DATASTREAM_ID", "temp-ds-123")


@pytest.fixture
def sample_systems():
    """Sample system data from API."""
    return [
        {
            "id": "system-openmeteo",
            "name": "Open Meteo",
            "external_id": "openmeteo",
            "system_type": "WEATHER",
        },
        {
            "id": "system-sensor",
            "name": "Inside Sensor",
            "external_id": "sensor",
            "system_type": "SENSOR",
        },
    ]


@pytest.fixture
def sample_datastreams():
    """Sample datastream data from API."""
    return [
        {
            "id": "ds-temperature",
            "name": "Temperature",
            "system_id": "system-openmeteo",
            "properties": {"unit": "°C"},
        },
        {
            "id": "ds-humidity",
            "name": "Humidity",
            "system_id": "system-openmeteo",
            "properties": {"unit": "%"},
        },
        {
            "id": "ds-dew-point",
            "name": "Dew Point",
            "system_id": "system-openmeteo",
            "properties": {"unit": "°C"},
        },
    ]


@pytest.fixture
def sample_weather_current():
    """Sample Open Meteo current weather response."""
    return {
        "current": {
            "temperature_2m": 72.5,
            "relative_humidity_2m": 65,
            "dew_point_2m": 58.3,
            "time": "2026-05-24T14:30:00",
        },
        "timezone": "America/Los_Angeles",
    }


@pytest.fixture
def sample_weather_hourly():
    """Sample Open Meteo hourly weather response."""
    return {
        "hourly": {
            "time": [
                "2026-05-23T00:00",
                "2026-05-23T01:00",
                "2026-05-23T02:00",
                "2026-05-23T03:00",
                "2026-05-23T04:00",
                "2026-05-23T05:00",
                # ... more hours
            ],
            "temperature_2m": [
                62.1, 61.8, 61.5, 61.2, 60.9, 60.6, 60.3, 60.0, 61.5, 63.2, 65.1, 67.0,
                69.5, 71.2, 72.5, 73.1, 72.8, 71.5, 69.2, 67.5, 65.8, 64.5, 63.2, 61.9,
            ],
            "relative_humidity_2m": [
                75, 76, 77, 78, 78, 79, 80, 81, 80, 78, 75, 70,
                65, 62, 60, 58, 60, 63, 65, 68, 70, 72, 73, 74,
            ],
            "dew_point_2m": [
                55.2, 54.9, 54.8, 54.7, 54.5, 54.4, 54.5, 54.7, 54.8, 55.2, 55.8, 56.1,
                56.5, 56.8, 57.2, 57.5, 57.8, 57.9, 57.5, 57.2, 57.1, 57.2, 57.1, 56.9,
            ],
        },
        "timezone": "America/Los_Angeles",
    }


@pytest.fixture
def mock_httpx_client(sample_systems, sample_datastreams, sample_weather_current, sample_weather_hourly):
    """Mock httpx.Client for API calls."""
    mock_client = MagicMock()
    
    # Default responses
    mock_response_systems = MagicMock()
    mock_response_systems.json.return_value = sample_systems
    mock_response_systems.raise_for_status = MagicMock()
    
    mock_response_datastreams = MagicMock()
    mock_response_datastreams.json.return_value = sample_datastreams
    mock_response_datastreams.raise_for_status = MagicMock()
    
    mock_response_weather_current = MagicMock()
    mock_response_weather_current.json.return_value = sample_weather_current
    mock_response_weather_current.raise_for_status = MagicMock()
    
    mock_response_weather_hourly = MagicMock()
    mock_response_weather_hourly.json.return_value = sample_weather_hourly
    mock_response_weather_hourly.raise_for_status = MagicMock()
    
    mock_response_observations = MagicMock()
    mock_response_observations.json.return_value = {"success": True, "count": 3}
    mock_response_observations.raise_for_status = MagicMock()
    
    def mock_get(url, params=None, headers=None):
        if "systems" in url:
            return mock_response_systems
        elif "datastreams" in url:
            return mock_response_datastreams
        elif "open-meteo" in url:
            # Check if it's hourly or current request
            if params and "hourly" in params:
                return mock_response_weather_hourly
            else:
                return mock_response_weather_current
        return MagicMock()
    
    def mock_post(url, json=None, headers=None):
        if "observations" in url and "bulk" in url:
            return mock_response_observations
        return MagicMock()
    
    mock_client.get = mock_get
    mock_client.post = mock_post
    mock_client.__enter__ = lambda self: self
    mock_client.__exit__ = lambda self, *args: None
    
    return mock_client
