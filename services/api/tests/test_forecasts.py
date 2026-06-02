import pytest
import json
import pickle
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone, timedelta
import pandas as pd
from fastapi import HTTPException

from app.routers.forecasts import (
    get_temperature_forecast,
    get_model_info,
    validate_service_api_key,
    retrain_temperature_model,
    ModelInfo,
)
from schemas.forecast_schemas import TemperatureForecast


class TestValidateServiceApiKey:
    """Test service API key validation."""
    
    @pytest.mark.asyncio
    async def test_validate_valid_key(self):
        """Test validation of correct API key."""
        with patch("app.routers.forecasts.SERVICE_API_KEY", "secret-key-123"):
            result = await validate_service_api_key(x_api_key="secret-key-123")
            assert result == "secret-key-123"
    
    @pytest.mark.asyncio
    async def test_validate_missing_key(self):
        """Test validation fails when API key header is missing."""
        with pytest.raises(HTTPException) as exc_info:
            await validate_service_api_key(x_api_key=None)
        
        assert exc_info.value.status_code == 401
        assert "Missing X-API-Key" in exc_info.value.detail
    
    @pytest.mark.asyncio
    async def test_validate_invalid_key(self):
        """Test validation fails when API key is incorrect."""
        with patch("app.routers.forecasts.SERVICE_API_KEY", "secret-key-123"):
            with pytest.raises(HTTPException) as exc_info:
                await validate_service_api_key(x_api_key="wrong-key")
            
            assert exc_info.value.status_code == 401
            assert "Invalid API key" in exc_info.value.detail
    
    @pytest.mark.asyncio
    async def test_validate_no_service_key_configured(self):
        """Test validation fails when SERVICE_API_KEY is not configured."""
        with patch("app.routers.forecasts.SERVICE_API_KEY", ""):
            with pytest.raises(HTTPException) as exc_info:
                await validate_service_api_key(x_api_key="any-key")
            
            assert exc_info.value.status_code == 500
            assert "not properly configured" in exc_info.value.detail


class TestGetTemperatureForecast:
    """Test temperature forecast generation."""
    
    def _create_mock_model(self, base_temp=22.0):
        """Create a mock Prophet model for testing."""
        mock_model = MagicMock()
        
        # Create sample forecast data
        now = datetime.now(timezone.utc)
        now_pd = pd.Timestamp(now).tz_localize(None)
        
        forecast_data = {
            "ds": pd.date_range(start=now_pd, periods=24, freq="30min"),
            "yhat": [base_temp + i*0.1 for i in range(24)],
            "yhat_lower": [base_temp + i*0.1 - 1.5 for i in range(24)],
            "yhat_upper": [base_temp + i*0.1 + 1.5 for i in range(24)],
        }
        forecast_df = pd.DataFrame(forecast_data)
        
        mock_model.predict = MagicMock(return_value=forecast_df)
        return mock_model
    
    @pytest.mark.asyncio
    async def test_get_forecast_success(self):
        """Test successful forecast generation."""
        mock_model = self._create_mock_model(base_temp=22.0)
        
        mock_redis = AsyncMock()
        mock_redis.get = AsyncMock(return_value=b"mock_model_bytes")
        mock_redis.close = AsyncMock()
        
        async_mock_from_url = AsyncMock(return_value=mock_redis)
        
        with patch("app.routers.forecasts.aioredis.from_url", async_mock_from_url):
            with patch("app.routers.forecasts.pickle.loads", return_value=mock_model):
                with patch("app.routers.forecasts.os.getenv") as mock_getenv:
                    def getenv_side_effect(key, default=None):
                        if key == "OUTSIDE_TEMP_DATASTREAM_ID":
                            return "test-datastream-uuid"
                        elif key == "REDIS_URL":
                            return "redis://redis:6379/0"
                        return default
                    
                    mock_getenv.side_effect = getenv_side_effect
                    
                    mock_request = MagicMock()
                    result = await get_temperature_forecast(mock_request)
        
        assert isinstance(result, TemperatureForecast)
        assert result.datastream_id == "test-datastream-uuid"
        assert len(result.forecast_points) == 24
        assert result.forecast_points[0].forecast >= 22.0
    
    @pytest.mark.asyncio
    async def test_get_forecast_no_datastream_configured(self):
        """Test forecast fails when datastream ID not configured."""
        with patch("app.routers.forecasts.os.getenv", return_value=None):
            mock_request = MagicMock()
            
            with pytest.raises(HTTPException) as exc_info:
                await get_temperature_forecast(mock_request)
            
            assert exc_info.value.status_code == 500
            assert "not configured" in exc_info.value.detail
    
    @pytest.mark.asyncio
    async def test_get_forecast_model_not_trained(self):
        """Test forecast fails when model is not trained yet."""
        mock_redis = AsyncMock()
        mock_redis.get = AsyncMock(return_value=None)  # No model in Redis
        mock_redis.close = AsyncMock()
        
        async_mock_from_url = AsyncMock(return_value=mock_redis)
        
        with patch("app.routers.forecasts.aioredis.from_url", async_mock_from_url):
            with patch("app.routers.forecasts.os.getenv") as mock_getenv:
                def getenv_side_effect(key, default=None):
                    if key == "OUTSIDE_TEMP_DATASTREAM_ID":
                        return "test-datastream-uuid"
                    elif key == "REDIS_URL":
                        return "redis://redis:6379/0"
                    return default
                
                mock_getenv.side_effect = getenv_side_effect
                
                mock_request = MagicMock()
                
                with pytest.raises(HTTPException) as exc_info:
                    await get_temperature_forecast(mock_request)
                
                assert exc_info.value.status_code == 404
                assert "not trained yet" in exc_info.value.detail
    
    @pytest.mark.asyncio
    async def test_get_forecast_model_error(self):
        """Test forecast handles prediction errors gracefully."""
        mock_model = MagicMock()
        mock_model.predict = MagicMock(side_effect=Exception("Prediction failed"))
        
        mock_redis = AsyncMock()
        mock_redis.get = AsyncMock(return_value=b"mock_model_bytes")
        mock_redis.close = AsyncMock()
        
        async_mock_from_url = AsyncMock(return_value=mock_redis)
        
        with patch("app.routers.forecasts.aioredis.from_url", async_mock_from_url):
            with patch("app.routers.forecasts.pickle.loads", return_value=mock_model):
                with patch("app.routers.forecasts.os.getenv") as mock_getenv:
                    def getenv_side_effect(key, default=None):
                        if key == "OUTSIDE_TEMP_DATASTREAM_ID":
                            return "test-datastream-uuid"
                        elif key == "REDIS_URL":
                            return "redis://redis:6379/0"
                        return default
                    
                    mock_getenv.side_effect = getenv_side_effect
                    
                    mock_request = MagicMock()
                    
                    with pytest.raises(HTTPException) as exc_info:
                        await get_temperature_forecast(mock_request)
                    
                    assert exc_info.value.status_code == 500
                    assert "Failed to generate forecast" in exc_info.value.detail


class TestGetModelInfo:
    """Test model information endpoint."""
    
    @pytest.mark.asyncio
    async def test_get_model_info_exists(self):
        """Test getting info for existing model."""
        now = datetime.now(timezone.utc)
        trained_at = now - timedelta(hours=2)
        
        metadata = {
            "trained_at": trained_at.isoformat()
        }
        
        mock_redis = AsyncMock()
        mock_redis.get = AsyncMock(return_value=json.dumps(metadata))
        mock_redis.close = AsyncMock()
        
        async_mock_from_url = AsyncMock(return_value=mock_redis)
        
        with patch("app.routers.forecasts.aioredis.from_url", async_mock_from_url):
            with patch("app.routers.forecasts.os.getenv") as mock_getenv:
                def getenv_side_effect(key, default=None):
                    if key == "OUTSIDE_TEMP_DATASTREAM_ID":
                        return "test-datastream-uuid"
                    elif key == "REDIS_URL":
                        return "redis://redis:6379/0"
                    return default
                
                mock_getenv.side_effect = getenv_side_effect
                
                mock_request = MagicMock()
                result = await get_model_info(mock_request)
        
        assert isinstance(result, ModelInfo)
        assert result.model_exists is True
        assert result.model_age_hours >= 1.9  # Approximately 2 hours old
        assert result.model_age_seconds >= 7000
    
    @pytest.mark.asyncio
    async def test_get_model_info_not_exists(self):
        """Test getting info when model doesn't exist."""
        mock_redis = AsyncMock()
        mock_redis.get = AsyncMock(return_value=None)
        mock_redis.close = AsyncMock()
        
        async_mock_from_url = AsyncMock(return_value=mock_redis)
        
        with patch("app.routers.forecasts.aioredis.from_url", async_mock_from_url):
            with patch("app.routers.forecasts.os.getenv") as mock_getenv:
                def getenv_side_effect(key, default=None):
                    if key == "OUTSIDE_TEMP_DATASTREAM_ID":
                        return "test-datastream-uuid"
                    elif key == "REDIS_URL":
                        return "redis://redis:6379/0"
                    return default
                
                mock_getenv.side_effect = getenv_side_effect
                
                mock_request = MagicMock()
                result = await get_model_info(mock_request)
        
        assert isinstance(result, ModelInfo)
        assert result.model_exists is False
        assert result.training_data_end is None
    
    @pytest.mark.asyncio
    async def test_get_model_info_no_datastream_configured(self):
        """Test model info fails when datastream ID not configured."""
        with patch("app.routers.forecasts.os.getenv", return_value=None):
            mock_request = MagicMock()
            
            with pytest.raises(HTTPException) as exc_info:
                await get_model_info(mock_request)
            
            assert exc_info.value.status_code == 500
    
    @pytest.mark.asyncio
    async def test_get_model_info_invalid_metadata(self):
        """Test model info handles invalid metadata gracefully."""
        mock_redis = AsyncMock()
        mock_redis.get = AsyncMock(return_value="invalid-json-{]")
        mock_redis.close = AsyncMock()
        
        async_mock_from_url = AsyncMock(return_value=mock_redis)
        
        with patch("app.routers.forecasts.aioredis.from_url", async_mock_from_url):
            with patch("app.routers.forecasts.os.getenv") as mock_getenv:
                def getenv_side_effect(key, default=None):
                    if key == "OUTSIDE_TEMP_DATASTREAM_ID":
                        return "test-datastream-uuid"
                    elif key == "REDIS_URL":
                        return "redis://redis:6379/0"
                    return default
                
                mock_getenv.side_effect = getenv_side_effect
                
                mock_request = MagicMock()
                
                # Should handle gracefully instead of crashing
                with pytest.raises(HTTPException) as exc_info:
                    await get_model_info(mock_request)
                
                assert exc_info.value.status_code == 500


class TestRetrainTemperatureModel:
    """Test model retraining endpoint."""
    
    @pytest.mark.asyncio
    async def test_retrain_success(self):
        """Test successful retrain request."""
        # No existing model metadata, no retrain in progress
        mock_redis = AsyncMock()
        mock_redis.get = AsyncMock(return_value=None)
        mock_redis.set = AsyncMock()
        mock_redis.close = AsyncMock()
        
        mock_connection = AsyncMock()
        mock_channel = AsyncMock()
        mock_connection.channel = AsyncMock(return_value=mock_channel)
        mock_connection.close = AsyncMock()
        
        async_mock_from_url = AsyncMock(return_value=mock_redis)
        
        # Mock Dramatiq RedisBroker and Message
        mock_broker = MagicMock()
        mock_broker.declare_queue = MagicMock()
        mock_broker.enqueue = MagicMock()
        mock_message = MagicMock()
        mock_message.message_id = "test-message-id"
        
        with patch("app.routers.forecasts.aioredis.from_url", async_mock_from_url):
            with patch("aio_pika.connect", return_value=mock_connection):
                with patch("app.routers.forecasts.os.getenv") as mock_getenv:
                    with patch("dramatiq.brokers.redis.RedisBroker", return_value=mock_broker):
                        with patch("dramatiq.Message", return_value=mock_message):
                            def getenv_side_effect(key, default=None):
                                if key == "OUTSIDE_TEMP_DATASTREAM_ID":
                                    return "test-datastream-uuid"
                                elif key == "REDIS_URL":
                                    return "redis://redis:6379/0"
                                elif key == "RABBITMQ_URL":
                                    return "amqp://rabbitmq:5672"
                                elif key == "SERVICE_API_KEY":
                                    return "secret-key"
                                return default
                            
                            mock_getenv.side_effect = getenv_side_effect
                            
                            result = await retrain_temperature_model()
        
        assert result["status"] == "success"
        assert "enqueued" in result["message"].lower()
        assert result["datastream_id"] == "test-datastream-uuid"
    
    @pytest.mark.asyncio
    async def test_retrain_already_in_progress(self):
        """Test retrain fails when already in progress."""
        mock_redis = AsyncMock()
        # Simulate in-progress flag exists
        mock_redis.get = AsyncMock(return_value="true")
        mock_redis.close = AsyncMock()
        
        async_mock_from_url = AsyncMock(return_value=mock_redis)
        
        with patch("app.routers.forecasts.aioredis.from_url", async_mock_from_url):
            with patch("app.routers.forecasts.os.getenv") as mock_getenv:
                def getenv_side_effect(key, default=None):
                    if key == "OUTSIDE_TEMP_DATASTREAM_ID":
                        return "test-datastream-uuid"
                    elif key == "REDIS_URL":
                        return "redis://redis:6379/0"
                    return default
                
                mock_getenv.side_effect = getenv_side_effect
                
                with pytest.raises(HTTPException) as exc_info:
                    await retrain_temperature_model()
                
                assert exc_info.value.status_code == 409
                assert "already in progress" in exc_info.value.detail
    
    @pytest.mark.asyncio
    async def test_retrain_model_too_young(self):
        """Test retrain fails when model is less than 1 minute old."""
        now = datetime.now(timezone.utc)
        # Model trained 30 seconds ago (less than 1 minute)
        trained_at = now - timedelta(seconds=30)
        
        metadata = {
            "trained_at": trained_at.isoformat()
        }
        
        mock_redis = AsyncMock()
        # First call: no in-progress flag; second call: metadata
        mock_redis.get = AsyncMock(side_effect=[None, json.dumps(metadata)])
        mock_redis.close = AsyncMock()
        
        async_mock_from_url = AsyncMock(return_value=mock_redis)
        
        with patch("app.routers.forecasts.aioredis.from_url", async_mock_from_url):
            with patch("app.routers.forecasts.os.getenv") as mock_getenv:
                def getenv_side_effect(key, default=None):
                    if key == "OUTSIDE_TEMP_DATASTREAM_ID":
                        return "test-datastream-uuid"
                    elif key == "REDIS_URL":
                        return "redis://redis:6379/0"
                    return default
                
                mock_getenv.side_effect = getenv_side_effect
                
                with pytest.raises(HTTPException) as exc_info:
                    await retrain_temperature_model()
                
                assert exc_info.value.status_code == 400
                assert "only" in exc_info.value.detail or "cannot retrain" in exc_info.value.detail
    
    @pytest.mark.asyncio
    async def test_retrain_no_datastream_configured(self):
        """Test retrain fails when datastream not configured."""
        mock_redis = AsyncMock()
        mock_redis.close = AsyncMock()
        
        with patch("app.routers.forecasts.aioredis.from_url", return_value=mock_redis):
            with patch("app.routers.forecasts.os.getenv", return_value=None):
                with pytest.raises(HTTPException) as exc_info:
                    await retrain_temperature_model()
                
                assert exc_info.value.status_code == 500
                assert "not properly configured" in exc_info.value.detail
    
    @pytest.mark.asyncio
    async def test_retrain_rabbitmq_not_configured(self):
        """Test retrain fails when RabbitMQ URL not configured."""
        mock_redis = AsyncMock()
        mock_redis.get = AsyncMock(return_value=None)
        mock_redis.close = AsyncMock()
        
        async_mock_from_url = AsyncMock(return_value=mock_redis)
        
        with patch("app.routers.forecasts.aioredis.from_url", async_mock_from_url):
            with patch("app.routers.forecasts.os.getenv") as mock_getenv:
                def getenv_side_effect(key, default=None):
                    if key == "OUTSIDE_TEMP_DATASTREAM_ID":
                        return "test-datastream-uuid"
                    elif key == "REDIS_URL":
                        return "redis://redis:6379/0"
                    elif key == "RABBITMQ_URL":
                        return None
                    return default
                
                mock_getenv.side_effect = getenv_side_effect
                
                with pytest.raises(HTTPException) as exc_info:
                    await retrain_temperature_model()
                
                assert exc_info.value.status_code == 500
    
    @pytest.mark.asyncio
    async def test_retrain_rabbitmq_connection_error(self):
        """Test retrain handles RabbitMQ connection errors."""
        mock_redis = AsyncMock()
        mock_redis.get = AsyncMock(return_value=None)
        mock_redis.close = AsyncMock()
        
        async_mock_from_url = AsyncMock(return_value=mock_redis)
        
        with patch("app.routers.forecasts.aioredis.from_url", async_mock_from_url):
            with patch("aio_pika.connect") as mock_connect:
                mock_connect.side_effect = Exception("Connection refused")
                
                with patch("app.routers.forecasts.os.getenv") as mock_getenv:
                    def getenv_side_effect(key, default=None):
                        if key == "OUTSIDE_TEMP_DATASTREAM_ID":
                            return "test-datastream-uuid"
                        elif key == "REDIS_URL":
                            return "redis://redis:6379/0"
                        elif key == "RABBITMQ_URL":
                            return "amqp://rabbitmq:5672"
                        return default
                    
                    mock_getenv.side_effect = getenv_side_effect
                    
                    with pytest.raises(HTTPException) as exc_info:
                        await retrain_temperature_model()
                    
                    assert exc_info.value.status_code == 500
                    assert "Failed to enqueue" in exc_info.value.detail
    
    @pytest.mark.asyncio
    async def test_retrain_model_old_enough(self):
        """Test retrain succeeds when model is 1+ hour old."""
        now = datetime.now(timezone.utc)
        # Model trained 2 hours ago
        trained_at = now - timedelta(hours=2)
        
        metadata = {
            "trained_at": trained_at.isoformat()
        }
        
        mock_redis = AsyncMock()
        # First call: no in-progress flag; second call: metadata
        mock_redis.get = AsyncMock(side_effect=[None, json.dumps(metadata)])
        mock_redis.set = AsyncMock()
        mock_redis.close = AsyncMock()
        
        mock_connection = AsyncMock()
        mock_channel = AsyncMock()
        mock_connection.channel = AsyncMock(return_value=mock_channel)
        mock_connection.close = AsyncMock()
        
        async_mock_from_url = AsyncMock(return_value=mock_redis)
        
        # Mock Dramatiq RedisBroker and Message
        mock_broker = MagicMock()
        mock_broker.declare_queue = MagicMock()
        mock_broker.enqueue = MagicMock()
        mock_message = MagicMock()
        mock_message.message_id = "test-message-id"
        
        with patch("app.routers.forecasts.aioredis.from_url", async_mock_from_url):
            with patch("aio_pika.connect", return_value=mock_connection):
                with patch("app.routers.forecasts.os.getenv") as mock_getenv:
                    with patch("dramatiq.brokers.redis.RedisBroker", return_value=mock_broker):
                        with patch("dramatiq.Message", return_value=mock_message):
                            def getenv_side_effect(key, default=None):
                                if key == "OUTSIDE_TEMP_DATASTREAM_ID":
                                    return "test-datastream-uuid"
                                elif key == "REDIS_URL":
                                    return "redis://redis:6379/0"
                                elif key == "RABBITMQ_URL":
                                    return "amqp://rabbitmq:5672"
                                return default
                            
                            mock_getenv.side_effect = getenv_side_effect
                            
                            result = await retrain_temperature_model()
        
        assert result["status"] == "success"
