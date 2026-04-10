import pytest
import pytest_asyncio
import asyncio
import time
from unittest.mock import AsyncMock, MagicMock, patch
import redis.asyncio as aioredis


@pytest_asyncio.fixture
async def mock_redis():
    """Create a mock Redis async client."""
    mock = AsyncMock(spec=aioredis.Redis)
    mock.ping = AsyncMock(return_value=True)
    mock.hset = AsyncMock(return_value=1)
    mock.hkeys = AsyncMock(return_value=[])
    mock.hdel = AsyncMock(return_value=0)
    mock.close = AsyncMock()
    return mock


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


@pytest.fixture
def mock_api_context():
    """Create a mock context object for handlers."""
    return {
        "redis": AsyncMock(),
        "job_id": "test-job-123",
    }


@pytest.fixture
def sample_systems():
    """Sample system data from API."""
    return [
        {
            "id": "system-1",
            "name": "Sensor A",
            "external_id": "sensor_a",
            "model": "SHT40",
            "system_type": "SENSOR",
        },
        {
            "id": "system-2",
            "name": "Sensor B",
            "external_id": "sensor_b",
            "model": "NOUS A1T",
            "system_type": "SENSOR",
        },
    ]


@pytest.fixture
def sample_datastreams():
    """Sample datastream data from API."""
    return [
        {
            "id": "ds-1",
            "name": "Temperature",
            "system_id": "system-1",
            "properties": {
                "mqtt_key": "temp",
                "unit": "C",
            },
        },
        {
            "id": "ds-2",
            "name": "Humidity",
            "system_id": "system-1",
            "properties": {
                "mqtt_key": "humidity",
                "unit": "%",
            },
        },
        {
            "id": "ds-3",
            "name": "Power",
            "system_id": "system-2",
            "properties": {
                "mqtt_key": "power",
                "unit": "W",
            },
        },
    ]


@pytest.fixture
def sample_weather_data():
    """Sample Open Meteo API response."""
    return {
        "latitude": 37.7749,
        "longitude": -122.4194,
        "current": {
            "temperature": 22.5,
            "relative_humidity": 65,
            "dew_point": 14.2,
        }
    }


@pytest.fixture
def mock_httpx_client():
    """Create a mock httpx async client."""
    mock = AsyncMock()
    mock.get = AsyncMock()
    mock.post = AsyncMock()
    mock.__aenter__ = AsyncMock(return_value=mock)
    mock.__aexit__ = AsyncMock(return_value=None)
    return mock


@pytest.fixture
def mock_token_manager():
    """Create a mock TokenManager."""
    manager = MagicMock()
    manager.get_token = AsyncMock(return_value="test-token")
    manager._fetch = AsyncMock()
    return manager
