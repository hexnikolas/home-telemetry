import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch, call
from app.main import NotifierService, _evaluate_condition


class TestEvaluateCondition:
    """Test alert condition evaluation logic."""

    def test_greater_than(self):
        assert _evaluate_condition(25.0, ">", 20.0) is True
        assert _evaluate_condition(15.0, ">", 20.0) is False
        assert _evaluate_condition(20.0, ">", 20.0) is False

    def test_less_than(self):
        assert _evaluate_condition(15.0, "<", 20.0) is True
        assert _evaluate_condition(25.0, "<", 20.0) is False
        assert _evaluate_condition(20.0, "<", 20.0) is False

    def test_greater_equal(self):
        assert _evaluate_condition(25.0, ">=", 20.0) is True
        assert _evaluate_condition(20.0, ">=", 20.0) is True
        assert _evaluate_condition(15.0, ">=", 20.0) is False

    def test_less_equal(self):
        assert _evaluate_condition(15.0, "<=", 20.0) is True
        assert _evaluate_condition(20.0, "<=", 20.0) is True
        assert _evaluate_condition(25.0, "<=", 20.0) is False

    def test_equals(self):
        assert _evaluate_condition(20.0, "=", 20.0) is True
        assert _evaluate_condition(20.0, "==", 20.0) is True
        assert _evaluate_condition(25.0, "=", 20.0) is False

    def test_invalid_condition(self):
        assert _evaluate_condition(25.0, "invalid", 20.0) is False


class TestNotifierServiceInit:
    """Test NotifierService initialization."""

    def test_init_defaults(self):
        service = NotifierService()
        assert service.redis is None
        assert service.docker_client is None
        assert service.rules == []
        assert service.redis_healthy is True
        assert service.redis_recovery_ts == 0.0
        assert service.redis_grace_seconds == 60
        assert service.container_health == {}
        assert service.offline_systems == set()
        assert service.api_token is None
        assert service.api_token_expiry == 0.0


class TestNotifierServiceAlert:
    """Test alert sending functionality."""

    @pytest.mark.asyncio
    async def test_send_alert_success(self, mock_redis):
        """Test sending alert to Gotify successfully."""
        service = NotifierService()
        service.redis = mock_redis
        
        with patch("app.main.httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_response = MagicMock()
            mock_response.raise_for_status = MagicMock()
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_class.return_value = mock_client
            
            with patch("app.main.GOTIFY_TOKEN", "test-token"):
                with patch("app.main.GOTIFY_URL", "http://gotify:80"):
                    await service.send_alert("Test Alert", "Test message", priority=5)
            
            mock_client.post.assert_called_once()

    @pytest.mark.asyncio
    async def test_send_alert_no_token(self, mock_redis):
        """Test that alert is not sent without token."""
        service = NotifierService()
        service.redis = mock_redis
        
        with patch("app.main.GOTIFY_TOKEN", ""):
            with patch("app.main.GOTIFY_URL", "http://gotify:80"):
                # Should not raise error when token is empty
                await service.send_alert("Test", "Message")


class TestNotifierServiceCooldown:
    """Test alert cooldown functionality."""

    @pytest.mark.asyncio
    async def test_is_in_cooldown_true(self, mock_redis):
        """Test cooldown detection when key exists."""
        service = NotifierService()
        mock_redis.get = AsyncMock(return_value="1")
        service.redis = mock_redis
        
        result = await service._is_in_cooldown("test:key")
        assert result is True
        mock_redis.get.assert_called_once_with("test:key")

    @pytest.mark.asyncio
    async def test_is_in_cooldown_false(self, mock_redis):
        """Test cooldown detection when key doesn't exist."""
        service = NotifierService()
        mock_redis.get = AsyncMock(return_value=None)
        service.redis = mock_redis
        
        result = await service._is_in_cooldown("test:key")
        assert result is False

    @pytest.mark.asyncio
    async def test_set_cooldown(self, mock_redis):
        """Test setting cooldown timeout."""
        service = NotifierService()
        service.redis = mock_redis
        
        await service._set_cooldown("test:key", 30)
        mock_redis.set.assert_called_once_with("test:key", "1", ex=30 * 60)


class TestNotifierServiceRedisHealth:
    """Test Redis health monitoring."""

    @pytest.mark.asyncio
    async def test_redis_health_stable(self, mock_redis):
        """Test Redis health when stable."""
        service = NotifierService()
        service.redis = mock_redis
        mock_redis.ping = AsyncMock(return_value=True)
        
        # Run for just one iteration
        with patch("app.main.asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
            mock_sleep.side_effect = asyncio.CancelledError()
            
            try:
                await service.monitor_redis_health()
            except asyncio.CancelledError:
                pass
        
        assert service.redis_healthy is True

    @pytest.mark.asyncio
    async def test_redis_health_monitor_starts(self, mock_redis):
        """Test Redis health monitor starts properly."""
        service = NotifierService()
        service.redis = mock_redis
        mock_redis.ping = AsyncMock(return_value=True)
        
        with patch("app.main.asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
            mock_sleep.side_effect = asyncio.CancelledError()
            
            try:
                await service.monitor_redis_health()
            except asyncio.CancelledError:
                pass
        
        # Monitor should start and run without errors
        assert mock_redis.ping.called


class TestNotifierServiceAPIToken:
    """Test API token management."""

    @pytest.mark.asyncio
    async def test_get_api_token_success(self, mock_redis):
        """Test successful token retrieval."""
        service = NotifierService()
        service.redis = mock_redis
        
        with patch("app.main.httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_response = MagicMock()
            mock_response.json.return_value = {
                "access_token": "test-token",
                "expires_in": 300
            }
            mock_response.raise_for_status = MagicMock()
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_class.return_value = mock_client
            
            with patch("app.main.API_URL", "http://api:8000"):
                with patch("app.main.API_CLIENT_ID", "test-id"):
                    with patch("app.main.API_CLIENT_SECRET", "test-secret"):
                        token = await service._get_api_token()
            
            assert token == "test-token"
            assert service.api_token == "test-token"

    @pytest.mark.asyncio
    async def test_get_api_token_cached(self, mock_redis):
        """Test token caching."""
        import time
        
        service = NotifierService()
        service.redis = mock_redis
        service.api_token = "cached-token"
        service.api_token_expiry = time.time() + 600  # Far future
        
        token = await service._get_api_token()
        
        # Should return cached token without making request
        assert token == "cached-token"

    @pytest.mark.asyncio
    async def test_get_api_token_failure(self, mock_redis):
        """Test token retrieval failure."""
        service = NotifierService()
        service.redis = mock_redis
        
        with patch("app.main.httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.post = AsyncMock(side_effect=Exception("Connection error"))
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_class.return_value = mock_client
            
            with patch("app.main.API_URL", "http://api:8000"):
                token = await service._get_api_token()
        
        assert token is None


class TestNotifierServiceRedisGrace:
    """Test Redis grace period logic."""

    def test_redis_grace_when_unhealthy(self):
        """Test grace period active when Redis is unhealthy."""
        service = NotifierService()
        service.redis_healthy = False
        
        assert service._in_redis_grace() is True

    def test_redis_grace_during_recovery(self):
        """Test grace period active during recovery window."""
        import asyncio
        
        service = NotifierService()
        service.redis_healthy = True
        service.redis_recovery_ts = asyncio.get_event_loop().time()
        service.redis_grace_seconds = 60
        
        assert service._in_redis_grace() is True

    def test_redis_grace_after_recovery(self):
        """Test grace period inactive after recovery."""
        import asyncio
        
        service = NotifierService()
        service.redis_healthy = True
        service.redis_recovery_ts = asyncio.get_event_loop().time() - 120  # 2 minutes ago
        service.redis_grace_seconds = 60
        
        assert service._in_redis_grace() is False
