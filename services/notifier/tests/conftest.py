import pytest
import pytest_asyncio
import asyncio
import yaml
import os
from unittest.mock import AsyncMock, MagicMock, patch
import redis.asyncio as aioredis


@pytest_asyncio.fixture
async def mock_redis():
    """Create a mock Redis async client."""
    mock = AsyncMock(spec=aioredis.Redis)
    mock.ping = AsyncMock(return_value=True)
    mock.get = AsyncMock(return_value=None)
    mock.set = AsyncMock(return_value=True)
    mock.hkeys = AsyncMock(return_value=[])
    mock.hdel = AsyncMock(return_value=0)
    mock.hset = AsyncMock(return_value=1)
    mock.xgroup_create = AsyncMock()
    mock.xreadgroup = AsyncMock()
    mock.xlen = AsyncMock(return_value=0)
    return mock


@pytest.fixture
def mock_docker_client():
    """Create a mock Docker client."""
    mock = MagicMock()
    mock.ping = MagicMock()
    mock.containers.list = MagicMock(return_value=[])
    return mock


@pytest.fixture
def sample_rules():
    """Sample alert rules for testing."""
    return [
        {
            "datastream_id": "test-ds-1",
            "name": "High Temperature",
            "condition": ">",
            "threshold": 30.0,
            "priority": 8,
            "cooldown_minutes": 10,
        },
        {
            "datastream_id": "test-ds-2",
            "name": "Low Humidity",
            "condition": "<",
            "threshold": 20.0,
            "priority": 5,
            "cooldown_minutes": 30,
        },
        {
            "type": "system_metric",
            "metric": "rabbitmq_queue_size",
            "name": "RabbitMQ Queue Backlog",
            "condition": ">",
            "threshold": 100,
            "priority": 8,
            "cooldown_minutes": 30,
        },
    ]


@pytest.fixture
def mock_rules_file(tmp_path, sample_rules):
    """Create a temporary rules.yaml file for testing."""
    rules_file = tmp_path / "rules.yaml"
    rules_file.write_text(yaml.dump({"rules": sample_rules}))
    return str(rules_file)


@pytest.fixture
def mock_httpx_response():
    """Create a mock httpx response."""
    mock = AsyncMock()
    mock.status_code = 200
    mock.json = AsyncMock(return_value={})
    mock.raise_for_status = AsyncMock()
    return mock


@pytest.fixture
def mock_gotify_env(monkeypatch):
    """Set up mock Gotify environment variables."""
    monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/0")
    monkeypatch.setenv("GOTIFY_URL", "http://gotify:80")
    monkeypatch.setenv("GOTIFY_TOKEN", "test-token")
    monkeypatch.setenv("API_URL", "http://api:8000")
    monkeypatch.setenv("API_CLIENT_ID", "notifier")
    monkeypatch.setenv("API_CLIENT_SECRET", "notifier-secret")
    monkeypatch.setenv("LOG_LEVEL", "DEBUG")
    monkeypatch.setenv("LOG_FORMAT", "json")


@pytest.fixture
def notifier_env(monkeypatch):
    """Set up Notifier environment variables."""
    monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/0")
    monkeypatch.setenv("GOTIFY_URL", "http://gotify:80")
    monkeypatch.setenv("GOTIFY_TOKEN", "test-token")
    monkeypatch.setenv("API_URL", "http://api:8000")
    monkeypatch.setenv("API_CLIENT_ID", "notifier")
    monkeypatch.setenv("API_CLIENT_SECRET", "notifier-secret")
    monkeypatch.setenv("RABBITMQ_MANAGEMENT_URL", "http://rabbitmq:15672")
    monkeypatch.setenv("RABBITMQ_MANAGEMENT_USER", "guest")
    monkeypatch.setenv("RABBITMQ_MANAGEMENT_PASS", "guest")
    monkeypatch.setenv("RABBITMQ_QUEUE_NAME", "observations")
    monkeypatch.setenv("CHECK_INTERVAL_HEALTH", "5")
    monkeypatch.setenv("CHECK_INTERVAL_HEARTBEAT", "10")
    monkeypatch.setenv("CHECK_INTERVAL_QUEUE", "10")
    monkeypatch.setenv("LOG_LEVEL", "DEBUG")
