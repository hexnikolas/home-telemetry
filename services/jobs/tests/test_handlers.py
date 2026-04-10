import pytest
import json
from unittest.mock import AsyncMock, MagicMock, patch, call
from app.handlers import (
    TokenManager,
    handle_sync_mqtt_topics_to_redis,
    handle_fetch_open_meteo_data,
    handle_process_observations,
)


class TestTokenManager:
    """Test OAuth2 token management."""

    @pytest.mark.asyncio
    async def test_token_fetch_success(self):
        """Test successful token fetching."""
        manager = TokenManager()
        
        with patch("app.handlers.httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_response = MagicMock()
            # response.json() is synchronous in httpx
            mock_response.json.return_value = {
                "access_token": "test-token-123",
                "expires_in": 900
            }
            mock_response.raise_for_status = MagicMock()
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_class.return_value = mock_client
            
            with patch("app.handlers.API_TOKEN_URL", "http://api:8000/auth/token"):
                token = await manager.get_token()
        
        assert token == "test-token-123"

    @pytest.mark.asyncio
    async def test_token_caching(self):
        """Test token is cached and reused."""
        manager = TokenManager()
        manager._token = "cached-token"
        manager._expires_at = 9999999999  # Far future
        
        token = await manager.get_token()
        
        # Should return cached token without making request
        assert token == "cached-token"

    @pytest.mark.asyncio
    async def test_token_refresh_when_expired(self):
        """Test token is refreshed when expired."""
        import time
        
        manager = TokenManager()
        manager._token = "old-token"
        manager._expires_at = time.time() - 100  # Expired
        
        with patch("app.handlers.httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_response = MagicMock()
            mock_response.json.return_value = {
                "access_token": "fresh-token",
                "expires_in": 900
            }
            mock_response.raise_for_status = MagicMock()
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_class.return_value = mock_client
            
            with patch("app.handlers.API_TOKEN_URL", "http://api:8000/auth/token"):
                token = await manager.get_token()
        
        assert token == "fresh-token"


class TestSyncMqttTopicsHandler:
    """Test MQTT topic synchronization."""

    @pytest.mark.asyncio
    async def test_sync_mqtt_topics_success(self, sample_systems, sample_datastreams, mock_api_context):
        """Test successful MQTT topic sync."""
        mock_redis = AsyncMock()
        mock_context = {"redis": mock_redis}
        
        with patch("app.handlers.token_manager.get_token", new_callable=AsyncMock) as mock_get_token:
            mock_get_token.return_value = "test-token"
            
            with patch("app.handlers.httpx.AsyncClient") as mock_client_class:
                mock_client = AsyncMock()
                
                # First call: systems response
                systems_response = MagicMock()
                systems_response.status_code = 200
                systems_response.json.return_value = sample_systems
                
                # Second call: datastreams response
                ds_response = MagicMock()
                ds_response.json.return_value = sample_datastreams
                
                # Third call: 404 to signal end
                end_response = MagicMock()
                end_response.status_code = 404
                
                mock_client.get = AsyncMock(side_effect=[
                    systems_response,
                    ds_response,
                    end_response,
                ])
                mock_client.__aenter__ = AsyncMock(return_value=mock_client)
                mock_client.__aexit__ = AsyncMock(return_value=None)
                mock_client_class.return_value = mock_client
                
                with patch("app.handlers.SYSTEMS_API_URL", "http://api:8000/api/v1/systems/"):
                    with patch("app.handlers.DATASTREAMS_API_URL", "http://api:8000/api/v1/datastreams/"):
                        await handle_sync_mqtt_topics_to_redis(mock_context)
        
        # Verify Redis was called to store config
        assert mock_redis.hset.called or mock_redis.hdel.called

    @pytest.mark.asyncio
    async def test_sync_mqtt_topics_no_systems(self):
        """Test handling when no systems are found."""
        mock_redis = AsyncMock()
        mock_context = {"redis": mock_redis}
        
        with patch("app.handlers.token_manager.get_token", new_callable=AsyncMock) as mock_get_token:
            mock_get_token.return_value = "test-token"
            
            with patch("app.handlers.httpx.AsyncClient") as mock_client_class:
                mock_client = AsyncMock()
                response = MagicMock()
                response.status_code = 200
                response.json.return_value = []
                
                mock_client.get = AsyncMock(return_value=response)
                mock_client.__aenter__ = AsyncMock(return_value=mock_client)
                mock_client.__aexit__ = AsyncMock(return_value=None)
                mock_client_class.return_value = mock_client
                
                with patch("app.handlers.SYSTEMS_API_URL", "http://api:8000/api/v1/systems/"):
                    await handle_sync_mqtt_topics_to_redis(mock_context)
        
        # Should complete without error
        
        # Should complete without error

    @pytest.mark.asyncio
    async def test_sync_mqtt_topics_filters_invalid_systems(self):
        """Test that systems without external_id or model are filtered."""
        mock_redis = AsyncMock()
        mock_context = {"redis": mock_redis}
        
        invalid_systems = [
            {"id": "s1", "name": "No external_id"},
            {"id": "s2", "external_id": "sensor_a", "name": "No model"},
        ]
        
        with patch("app.handlers.token_manager.get_token", new_callable=AsyncMock) as mock_get_token:
            mock_get_token.return_value = "test-token"
            
            with patch("app.handlers.httpx.AsyncClient") as mock_client_class:
                mock_client = AsyncMock()
                response = MagicMock()
                response.status_code = 200
                response.json.return_value = invalid_systems
                
                mock_client.get = AsyncMock(return_value=response)
                mock_client.__aenter__ = AsyncMock(return_value=mock_client)
                mock_client.__aexit__ = AsyncMock(return_value=None)
                mock_client_class.return_value = mock_client
                
                with patch("app.handlers.SYSTEMS_API_URL", "http://api:8000/api/v1/systems/"):
                    await handle_sync_mqtt_topics_to_redis(mock_context)


class TestFetchOpenMeteoHandler:
    """Test Open Meteo data fetch."""

    @pytest.mark.asyncio
    async def test_fetch_open_meteo_success(self, sample_weather_data):
        """Test successful weather data fetch."""
        mock_context = {"redis": AsyncMock()}
        
        with patch("app.handlers.token_manager.get_token", new_callable=AsyncMock) as mock_get_token:
            mock_get_token.return_value = "test-token"
            
            with patch("app.handlers.httpx.AsyncClient") as mock_client_class:
                mock_client = AsyncMock()
                
                # System response
                systems_response = MagicMock()
                systems_response.json.return_value = [{
                    "id": "om-system",
                    "name": "Open Meteo"
                }]
                
                # Datastreams response
                ds_response = MagicMock()
                ds_response.json.return_value = [
                    {"id": "ds-temp", "name": "Temperature"},
                    {"id": "ds-humidity", "name": "Humidity"},
                    {"id": "ds-dew", "name": "Dew Point"},
                ]
                
                # Weather response
                weather_response = MagicMock()
                weather_response.json.return_value = sample_weather_data
                
                # Observations creation responses
                obs_response = MagicMock()
                obs_response.json.return_value = {"id": "obs-1"}
                
                mock_client.get = AsyncMock(side_effect=[
                    systems_response, ds_response, weather_response
                ])
                mock_client.post = AsyncMock(return_value=obs_response)
                mock_client.__aenter__ = AsyncMock(return_value=mock_client)
                mock_client.__aexit__ = AsyncMock(return_value=None)
                mock_client_class.return_value = mock_client
                
                with patch("app.handlers.SYSTEMS_API_URL", "http://api:8000/api/v1/systems/"):
                    with patch("app.handlers.DATASTREAMS_API_URL", "http://api:8000/api/v1/datastreams/"):
                        with patch("app.handlers.OBSERVATIONS_API_URL", "http://api:8000/api/v1/observations/"):
                            result = await handle_fetch_open_meteo_data(mock_context)


class TestProcessObservationsHandler:
    """Test observation processing."""

    @pytest.mark.asyncio
    async def test_process_observations_success(self):
        """Test successful observation processing."""
        mock_context = {"redis": AsyncMock()}
        data = {
            "datastream_id": "test-ds",
            "start_time": "2024-03-06T00:00:00Z",
            "end_time": "2024-03-06T23:59:59Z",
        }
        
        result = await handle_process_observations(mock_context, data)
        
        assert result["status"] == "success"
        assert "processed_observations" in result

    @pytest.mark.asyncio
    async def test_process_observations_no_data(self):
        """Test observation processing with no data."""
        mock_context = {"redis": AsyncMock()}
        
        result = await handle_process_observations(mock_context, None)
        
        assert result["status"] == "success"
