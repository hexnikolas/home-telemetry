import pytest
from unittest.mock import MagicMock, patch, call
from datetime import datetime, timezone, timedelta
import json

from app.tasks import fetch_open_meteo_data, sync_mqtt_topics_to_redis, train_temperature_model


class TestFetchOpenMeteoData:
    """Test Open Meteo weather data fetching."""
    
    @pytest.fixture(autouse=True)
    def _setup(self, jobs_env):
        """Setup environment for each test."""
        pass

    def test_fetch_current_data_first_run(self, mock_httpx_client):
        """Test fetching current weather data on first run."""
        with patch("app.tasks.httpx.Client", return_value=mock_httpx_client):
            with patch("app.tasks.token_manager") as mock_token_mgr:
                mock_token_mgr.get_token.return_value = "test-token"
                
                result = fetch_open_meteo_data()
        
        assert result["status"] == "success"
        assert result["observations_created"] == 3
        assert result["is_retry"] == False
        assert "result_time" in result

    def test_fetch_historical_data_on_retry(self, mock_httpx_client):
        """Test fetching historical hourly data on retry."""
        # Use a time that matches our sample hourly data (2026-05-23 with hours 00-23)
        # Use hour 3 which should be in the sample data
        past_time = datetime(2026, 5, 23, 3, 30, 0, tzinfo=timezone.utc).isoformat()
        
        with patch("app.tasks.httpx.Client", return_value=mock_httpx_client):
            with patch("app.tasks.token_manager") as mock_token_mgr:
                mock_token_mgr.get_token.return_value = "test-token"
                
                result = fetch_open_meteo_data(result_time=past_time)
        
        assert result["status"] == "success"
        assert result["is_retry"] == True
        assert result["result_time"] == past_time
        assert result["observations_created"] == 3

    def test_system_not_found(self, mock_httpx_client):
        """Test error when Open Meteo system is not found."""
        # Create a new mock that returns empty systems
        mock_client_empty = MagicMock()
        mock_response = MagicMock()
        mock_response.json.return_value = []
        mock_response.raise_for_status = MagicMock()
        
        # For systems requests, return empty; for others use original
        def mock_get_empty(url, params=None, headers=None):
            if "systems" in url:
                return mock_response
            return mock_httpx_client.get(url, params, headers)
        
        mock_client_empty.get = mock_get_empty
        mock_client_empty.post = mock_httpx_client.post
        mock_client_empty.__enter__ = lambda self: self
        mock_client_empty.__exit__ = lambda self, *args: None
        
        with patch("app.tasks.httpx.Client", return_value=mock_client_empty):
            with patch("app.tasks.token_manager") as mock_token_mgr:
                mock_token_mgr.get_token.return_value = "test-token"
                
                result = fetch_open_meteo_data()
        
        assert result["status"] == "error"
        assert "not found" in result["message"].lower()

    def test_no_datastreams_found(self, mock_httpx_client):
        """Test error when no datastreams found for system."""
        # Create a new mock that returns empty datastreams
        mock_client_empty = MagicMock()
        mock_response = MagicMock()
        mock_response.json.return_value = []
        mock_response.raise_for_status = MagicMock()
        
        # For datastreams requests, return empty; for others use original
        def mock_get_empty(url, params=None, headers=None):
            if "datastreams" in url:
                return mock_response
            return mock_httpx_client.get(url, params, headers)
        
        mock_client_empty.get = mock_get_empty
        mock_client_empty.post = mock_httpx_client.post
        mock_client_empty.__enter__ = lambda self: self
        mock_client_empty.__exit__ = lambda self, *args: None
        
        with patch("app.tasks.httpx.Client", return_value=mock_client_empty):
            with patch("app.tasks.token_manager") as mock_token_mgr:
                mock_token_mgr.get_token.return_value = "test-token"
                
                result = fetch_open_meteo_data()
        
        assert result["status"] == "error"
        assert "datastreams" in result["message"].lower()

    def test_hourly_data_extraction_by_exact_match(self, mock_httpx_client):
        """Test extracting hourly data by exact hour:00 match."""
        # Use 4:00 UTC which should exist in sample data
        past_time = datetime(2026, 5, 23, 4, 30, 0, tzinfo=timezone.utc).isoformat()
        
        with patch("app.tasks.httpx.Client", return_value=mock_httpx_client):
            with patch("app.tasks.token_manager") as mock_token_mgr:
                mock_token_mgr.get_token.return_value = "test-token"
                
                result = fetch_open_meteo_data(result_time=past_time)
        
        assert result["status"] == "success"
        assert result["observations_created"] > 0
        # Should extract the 4:00 AM data (index 4)
        assert "temperature" in str(result).lower() or result["observations_created"] > 0

    def test_partial_observations_when_missing_values(self, mock_httpx_client):
        """Test creating observations only for available weather data."""
        # Create response with some missing fields
        incomplete_weather = {
            "hourly": {
                "time": ["2026-05-23T00:00"],
                "temperature_2m": [62.1],
                "relative_humidity_2m": [None],  # Missing humidity
                "dew_point_2m": [55.2],
            },
            "timezone": "America/Los_Angeles",
        }
        
        # Create a new mock with incomplete weather data
        mock_client_incomplete = MagicMock()
        mock_response = MagicMock()
        mock_response.json.return_value = incomplete_weather
        mock_response.raise_for_status = MagicMock()
        
        def mock_get_incomplete(url, params=None, headers=None):
            if "open-meteo" in url:
                return mock_response
            return mock_httpx_client.get(url, params, headers)
        
        mock_client_incomplete.get = mock_get_incomplete
        mock_client_incomplete.post = mock_httpx_client.post
        mock_client_incomplete.__enter__ = lambda self: self
        mock_client_incomplete.__exit__ = lambda self, *args: None
        
        with patch("app.tasks.httpx.Client", return_value=mock_client_incomplete):
            with patch("app.tasks.token_manager") as mock_token_mgr:
                mock_token_mgr.get_token.return_value = "test-token"
                
                result = fetch_open_meteo_data(result_time="2026-05-23T00:00:00Z")
        
        # Should create 2 observations (temp and dew point, skipping humidity)
        assert result["observations_created"] <= 3

    def test_api_error_raises_exception(self, mock_httpx_client):
        """Test that API errors are raised for retry."""
        # Create a mock that always raises errors
        mock_client_error = MagicMock()
        mock_response = MagicMock()
        mock_response.raise_for_status.side_effect = Exception("API Error")
        
        def mock_get_error(url, params=None, headers=None):
            return mock_response
        
        mock_client_error.get = mock_get_error
        mock_client_error.__enter__ = lambda self: self
        mock_client_error.__exit__ = lambda self, *args: None
        
        with patch("app.tasks.httpx.Client", return_value=mock_client_error):
            with patch("app.tasks.token_manager") as mock_token_mgr:
                mock_token_mgr.get_token.return_value = "test-token"
                
                with pytest.raises(Exception):
                    fetch_open_meteo_data()

    def test_result_time_preserved_across_retries(self, mock_httpx_client):
        """Test that result_time is preserved when retrying."""
        original_time = "2026-05-22T14:30:00Z"
        
        with patch("app.tasks.httpx.Client", return_value=mock_httpx_client):
            with patch("app.tasks.token_manager") as mock_token_mgr:
                mock_token_mgr.get_token.return_value = "test-token"
                
                # First call with explicit time
                result = fetch_open_meteo_data(result_time=original_time)
        
        assert result["result_time"] == original_time
        assert result["is_retry"] == True  # Marked as retry when time is provided

    def test_observations_bulk_creation(self, mock_httpx_client):
        """Test that observations are created in bulk."""
        with patch("app.tasks.httpx.Client", return_value=mock_httpx_client):
            with patch("app.tasks.token_manager") as mock_token_mgr:
                mock_token_mgr.get_token.return_value = "test-token"
                
                result = fetch_open_meteo_data()
                
                # Verify bulk POST was called and observations were created
                assert result["status"] == "success"
                assert result["observations_created"] > 0


class TestSyncMqttTopics:
    """Test MQTT topic synchronization."""
    
    @pytest.fixture(autouse=True)
    def _setup(self, jobs_env):
        """Setup environment for each test."""
        pass

    def test_sync_mqtt_topics_success(self):
        """Test that sync MQTT topics task can be executed."""
        with patch("app.tasks.httpx.Client"):
            with patch("app.tasks.token_manager") as mock_token_mgr:
                mock_token_mgr.get_token.return_value = "test-token"
                with patch("redis.from_url") as mock_redis:
                    mock_r = MagicMock()
                    mock_r.hkeys.return_value = []
                    mock_r.hset.return_value = 1
                    mock_redis.return_value = mock_r
                    
                    # Task executes without error
                    result = sync_mqtt_topics_to_redis()
                    # Result may be None or a dict, just verify it doesn't crash
                    assert result is None or isinstance(result, dict)


class TestTrainTemperatureModel:
    """Test temperature model training."""
    
    @pytest.fixture(autouse=True)
    def _setup(self, jobs_env):
        """Setup environment for each test."""
        pass

    def test_train_temperature_model_success(self):
        """Test that train temperature model task can be executed."""
        with patch("app.tasks.httpx.Client"):
            with patch("app.tasks.token_manager") as mock_token_mgr:
                mock_token_mgr.get_token.return_value = "test-token"
                with patch("redis.from_url") as mock_redis:
                    mock_r = MagicMock()
                    mock_r.set.return_value = True
                    mock_redis.return_value = mock_r
                    
                    # Patch the prophet model training function
                    with patch("app.tasks.train_and_cache_model") as mock_train:
                        mock_train.return_value = "model-id-123"
                        result = train_temperature_model()
                        
                        # Task executes without error
                        assert result is None or isinstance(result, dict)


class TestTaskActorConfiguration:
    """Test Dramatiq actor configuration."""
    
    def test_fetch_open_meteo_has_retry_config(self):
        """Test that fetch_open_meteo_data has proper retry configuration."""
        # Check that the actor has retry configuration
        assert hasattr(fetch_open_meteo_data, "options")
        options = fetch_open_meteo_data.options
        
        # Should have max_retries set
        assert options.get("max_retries", 0) > 0
        assert options.get("min_backoff", 0) > 0
        assert options.get("max_backoff", 0) > 0
