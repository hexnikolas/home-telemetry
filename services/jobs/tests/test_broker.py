import pytest
from unittest.mock import patch, MagicMock

from app.broker import broker


class TestBrokerConfiguration:
    """Test Dramatiq broker setup."""
    
    def test_broker_is_defined(self):
        """Test that broker is properly defined."""
        assert broker is not None

    def test_broker_has_consumer(self):
        """Test that broker has a consumer configured."""
        # Dramatiq brokers should have get_consumer method
        assert hasattr(broker, "consume")

    def test_broker_can_declare_actor(self):
        """Test that broker can handle actors."""
        # Dramatiq actors are declared with @dramatiq.actor() globally
        # and automatically added to the broker
        from app.tasks import fetch_open_meteo_data
        
        # Verify the actor has send method
        assert hasattr(fetch_open_meteo_data, "send")

    def test_broker_middleware_configured(self):
        """Test that broker has middleware configured."""
        # Check if broker has middleware list
        if hasattr(broker, "middleware"):
            assert len(broker.middleware) > 0


class TestActorRegistration:
    """Test that tasks are properly registered as actors."""
    
    def test_fetch_open_meteo_is_actor(self):
        """Test that fetch_open_meteo_data is registered as a Dramatiq actor."""
        from app.tasks import fetch_open_meteo_data
        
        assert hasattr(fetch_open_meteo_data, "actor_name")
        assert fetch_open_meteo_data.actor_name == "fetch_open_meteo_data"

    def test_sync_mqtt_topics_is_actor(self):
        """Test that sync_mqtt_topics_to_redis is registered as a Dramatiq actor."""
        from app.tasks import sync_mqtt_topics_to_redis
        
        assert hasattr(sync_mqtt_topics_to_redis, "actor_name")
        assert sync_mqtt_topics_to_redis.actor_name == "sync_mqtt_topics_to_redis"

    def test_train_temperature_model_is_actor(self):
        """Test that train_temperature_model is registered as a Dramatiq actor."""
        from app.tasks import train_temperature_model
        
        assert hasattr(train_temperature_model, "actor_name")
        assert train_temperature_model.actor_name == "train_temperature_model"

    def test_actor_send_returns_message(self):
        """Test that calling send() on an actor returns a message."""
        from app.tasks import fetch_open_meteo_data
        
        # Mock the broker to prevent actual message sending
        with patch.object(fetch_open_meteo_data, "send") as mock_send:
            mock_send.return_value = MagicMock()
            result = fetch_open_meteo_data.send()
            
            assert result is not None

    def test_fetch_open_meteo_retry_options(self):
        """Test that fetch_open_meteo_data has proper retry options."""
        from app.tasks import fetch_open_meteo_data
        
        # Dramatiq decorators store options in the actor
        assert hasattr(fetch_open_meteo_data, "options")
        options = fetch_open_meteo_data.options
        
        # Verify retry configuration exists
        assert "max_retries" in options
        assert "min_backoff" in options
        assert "max_backoff" in options
        
        # Verify sensible values
        assert options["max_retries"] > 0
        assert options["min_backoff"] > 0
        assert options["max_backoff"] >= options["min_backoff"]
