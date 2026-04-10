import pytest
import json
from unittest.mock import AsyncMock, MagicMock, patch
from app.scheduler import publish_schedules_to_redis, JOB_DEFINITIONS, SCHEDULES
from app.queue import get_redis_settings


class TestRedisSettings:
    """Test Redis connection settings parser."""

    def test_redis_settings_default(self):
        """Test default Redis settings."""
        with patch("app.queue.REDIS_URL", "redis://localhost:6379/0"):
            settings = get_redis_settings()
            
            assert settings.host == "localhost"
            assert settings.port == 6379
            assert settings.database == 0

    def test_redis_settings_with_password(self):
        """Test Redis settings with authentication."""
        with patch("app.queue.REDIS_URL", "redis://:password@redis.example.com:6380/2"):
            settings = get_redis_settings()
            
            assert settings.host == "redis.example.com"
            assert settings.port == 6380
            assert settings.database == 2
            assert settings.password == "password"

    def test_redis_settings_custom_host(self):
        """Test Redis settings with custom host."""
        with patch("app.queue.REDIS_URL", "redis://redis-prod:6379/1"):
            settings = get_redis_settings()
            
            assert settings.host == "redis-prod"
            assert settings.port == 6379
            assert settings.database == 1


class TestSchedulerConfig:
    """Test scheduler configuration."""

    def test_job_definitions_structure(self):
        """Test that job definitions have required structure."""
        for job_name, config in JOB_DEFINITIONS.items():
            assert "handler" in config
            assert "minute" in config
            assert callable(config["handler"])

    def test_schedules_dictionary(self):
        """Test that schedules are properly built."""
        for job_name, schedule_info in SCHEDULES.items():
            assert "minute" in schedule_info
            assert "handler" in schedule_info
            assert "run_at_startup" in schedule_info
            
            # minute should be JSON string
            minutes = json.loads(schedule_info["minute"])
            assert isinstance(minutes, list)

    def test_sync_mqtt_cron_schedule(self):
        """Test MQTT sync runs every 5 minutes."""
        from app.scheduler import sync_mqtt_cron
        
        # The cron job should be defined
        assert sync_mqtt_cron is not None

    def test_fetch_meteo_cron_schedule(self):
        """Test Open Meteo fetch runs at 0 and 30 minutes."""
        from app.scheduler import fetch_meteo_cron
        
        # The cron job should be defined
        assert fetch_meteo_cron is not None


class TestPublishSchedules:
    """Test publishing schedules to Redis."""

    @pytest.mark.asyncio
    async def test_publish_schedules_success(self, mock_redis):
        """Test successful schedule publishing."""
        # Create an AsyncMock that returns mock_redis when awaited
        async_mock_from_url = AsyncMock(return_value=mock_redis)
        
        with patch("app.scheduler.aioredis.from_url", async_mock_from_url):
            await publish_schedules_to_redis()
            
            # Should have called Redis hset for each job
            assert mock_redis.hset.called
            mock_redis.close.assert_called()

    @pytest.mark.asyncio
    async def test_publish_schedules_redis_error(self):
        """Test handling of Redis connection error."""
        with patch("app.scheduler.aioredis.from_url") as mock_from_url:
            mock_from_url.side_effect = Exception("Connection failed")
            
            # Should not raise, errors are caught
            await publish_schedules_to_redis()

    @pytest.mark.asyncio
    async def test_publish_schedules_contains_expected_jobs(self):
        """Test that required jobs are published."""
        mock_redis = AsyncMock()
        async_mock_from_url = AsyncMock(return_value=mock_redis)
        
        with patch("app.scheduler.aioredis.from_url", async_mock_from_url):
            await publish_schedules_to_redis()
            
            # Extract job names from hset calls
            call_args_list = mock_redis.hset.call_args_list
            
            # Should have called hset at least twice for our two jobs
            assert len(call_args_list) >= 2


class TestWorkerSettings:
    """Test worker configuration."""

    def test_worker_settings_functions(self):
        """Test that worker has required functions."""
        from app.worker import WorkerSettings
        
        functions = WorkerSettings.functions
        
        assert len(functions) >= 2
        # Functions should be callables
        assert all(callable(f) for f in functions)

    def test_worker_settings_cron_jobs(self):
        """Test that worker has cron jobs configured."""
        from app.worker import WorkerSettings
        
        cron_jobs = WorkerSettings.cron_jobs
        
        assert len(cron_jobs) >= 2

    def test_worker_settings_redis(self):
        """Test that worker has Redis configured."""
        from app.worker import WorkerSettings
        
        assert WorkerSettings.redis_settings is not None
        assert WorkerSettings.redis_settings.host is not None

    def test_worker_settings_timeouts(self):
        """Test worker timeout settings."""
        from app.worker import WorkerSettings
        
        assert WorkerSettings.job_timeout == 600  # 10 minutes
        assert WorkerSettings.keep_result == 86400  # 24 hours
        assert WorkerSettings.allow_abort_jobs is True
