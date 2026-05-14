import pytest
import json
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone

from app.rabbitmq_consumer import RetrainQueueConsumer, run_retrain_consumer


# Helper classes for async context managers
class AsyncContextManager:
    """Simple async context manager for mocking."""
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, *args):
        pass


class AsyncIteratorContext:
    """Async context manager + iterator for queue.iterator()."""
    def __init__(self, message):
        self.message = message
        self.returned = False
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, *args):
        pass
    
    def __aiter__(self):
        return self
    
    async def __anext__(self):
        if not self.returned:
            self.returned = True
            return self.message
        raise StopAsyncIteration


class TestRetrainQueueConsumerInit:
    """Test RetrainQueueConsumer initialization."""

    def test_init_default_values(self):
        """Test consumer initializes with default values."""
        with patch("app.rabbitmq_consumer.RABBITMQ_URL", "amqp://rabbitmq:5672"):
            with patch("app.rabbitmq_consumer.QUEUE_NAME", "model.retrain"):
                consumer = RetrainQueueConsumer()
        
        assert consumer.queue_name == "model.retrain"
        assert consumer.connection is None
        assert consumer.channel is None
        assert consumer.queue is None

    def test_init_custom_values(self):
        """Test consumer initializes with custom values."""
        consumer = RetrainQueueConsumer(
            rabbitmq_url="amqp://custom:5672",
            queue_name="custom.queue"
        )
        
        assert consumer.rabbitmq_url == "amqp://custom:5672"
        assert consumer.queue_name == "custom.queue"


class TestRetrainQueueConsumerConnect:
    """Test RabbitMQ connection."""

    @pytest.mark.asyncio
    async def test_connect_success(self):
        """Test successful RabbitMQ connection."""
        mock_connection = AsyncMock()
        mock_channel = AsyncMock()
        mock_queue = AsyncMock()
        
        mock_connection.channel = AsyncMock(return_value=mock_channel)
        mock_channel.declare_queue = AsyncMock(return_value=mock_queue)
        
        with patch("app.rabbitmq_consumer.aio_pika.connect", return_value=mock_connection):
            consumer = RetrainQueueConsumer(
                rabbitmq_url="amqp://rabbitmq:5672",
                queue_name="model.retrain"
            )
            
            await consumer.connect()
        
        assert consumer.connection == mock_connection
        assert consumer.channel == mock_channel
        assert consumer.queue == mock_queue
        mock_connection.channel.assert_called_once()
        mock_channel.declare_queue.assert_called_once_with("model.retrain", durable=True)

    @pytest.mark.asyncio
    async def test_connect_failure(self):
        """Test RabbitMQ connection failure."""
        with patch("app.rabbitmq_consumer.aio_pika.connect") as mock_connect:
            mock_connect.side_effect = Exception("Connection refused")
            
            consumer = RetrainQueueConsumer(
                rabbitmq_url="amqp://invalid:5672",
                queue_name="model.retrain"
            )
            
            with pytest.raises(Exception) as exc_info:
                await consumer.connect()
            
            assert "Connection refused" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_connect_queue_declare_failure(self):
        """Test queue declaration failure."""
        mock_connection = AsyncMock()
        mock_channel = AsyncMock()
        
        mock_connection.channel = AsyncMock(return_value=mock_channel)
        mock_channel.declare_queue = AsyncMock(side_effect=Exception("Queue error"))
        
        with patch("app.rabbitmq_consumer.aio_pika.connect", return_value=mock_connection):
            consumer = RetrainQueueConsumer()
            
            with pytest.raises(Exception) as exc_info:
                await consumer.connect()
            
            assert "Queue error" in str(exc_info.value)


class TestRetrainQueueConsumerDisconnect:
    """Test RabbitMQ disconnection."""

    @pytest.mark.asyncio
    async def test_disconnect_success(self):
        """Test successful RabbitMQ disconnection."""
        consumer = RetrainQueueConsumer()
        consumer.connection = AsyncMock()
        
        await consumer.disconnect()
        
        consumer.connection.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_disconnect_no_connection(self):
        """Test disconnection when no connection exists."""
        consumer = RetrainQueueConsumer()
        consumer.connection = None
        
        # Should not raise error
        await consumer.disconnect()


class TestRetrainQueueConsumerStartConsuming:
    """Test message consumption."""

    @pytest.mark.asyncio
    async def test_start_consuming_not_connected(self):
        """Test consuming without being connected raises error."""
        consumer = RetrainQueueConsumer()
        consumer.queue = None
        
        with pytest.raises(RuntimeError) as exc_info:
            await consumer.start_consuming()
        
        assert "Not connected" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_consume_valid_retrain_message(self):
        """Test consuming valid retrain message."""
        # Setup message
        message_body = json.dumps({
            "requested_at": datetime.now(timezone.utc).isoformat()
        })
        
        mock_message = AsyncMock()
        mock_message.body = message_body.encode()
        mock_message.process = MagicMock(return_value=AsyncContextManager())
        
        # Setup queue iterator
        mock_queue = AsyncMock()
        mock_queue.iterator = MagicMock(return_value=AsyncIteratorContext(mock_message))
        
        mock_redis = AsyncMock()
        mock_redis.get = AsyncMock(return_value=None)  # Not in progress
        mock_redis.set = AsyncMock()
        mock_redis.close = AsyncMock()
        
        consumer = RetrainQueueConsumer()
        consumer.queue = mock_queue
        
        with patch("app.rabbitmq_consumer.aioredis.from_url", return_value=mock_redis):
            with patch("app.rabbitmq_consumer.handle_train_temperature_model") as mock_handler:
                mock_handler.return_value = {"status": "success"}
                
                with patch("app.rabbitmq_consumer.os.getenv") as mock_getenv:
                    def getenv_side_effect(key, default=None):
                        if key == "REDIS_URL":
                            return "redis://redis:6379/0"
                        elif key == "OUTSIDE_TEMP_DATASTREAM_ID":
                            return "test-ds-id"
                        return default
                    
                    mock_getenv.side_effect = getenv_side_effect
                    
                    await consumer.start_consuming()

    @pytest.mark.asyncio
    async def test_consume_invalid_json(self):
        """Test consuming message with invalid JSON."""
        mock_message = AsyncMock()
        mock_message.body = b"invalid json {]"
        mock_message.process = MagicMock(return_value=AsyncContextManager())
        
        # Setup queue iterator
        mock_queue = AsyncMock()
        mock_queue.iterator = MagicMock(return_value=AsyncIteratorContext(mock_message))
        
        consumer = RetrainQueueConsumer()
        consumer.queue = mock_queue
        
        # Should handle invalid JSON without raising
        await consumer.start_consuming()

    @pytest.mark.asyncio
    async def test_consume_retrain_already_in_progress(self):
        """Test handling message when retrain already in progress."""
        message_body = json.dumps({
            "requested_at": datetime.now(timezone.utc).isoformat()
        })
        
        mock_message = AsyncMock()
        mock_message.body = message_body.encode()
        mock_message.process = MagicMock(return_value=AsyncContextManager())
        
        # Setup queue iterator
        mock_queue = AsyncMock()
        mock_queue.iterator = MagicMock(return_value=AsyncIteratorContext(mock_message))
        
        # Setup redis - report in progress
        mock_redis = AsyncMock()
        mock_redis.get = AsyncMock(return_value="true")  # In progress
        mock_redis.close = AsyncMock()
        
        consumer = RetrainQueueConsumer()
        consumer.queue = mock_queue
        
        with patch("app.rabbitmq_consumer.aioredis.from_url", return_value=mock_redis):
            with patch("app.rabbitmq_consumer.handle_train_temperature_model") as mock_handler:
                await consumer.start_consuming()
        
        # Handler should NOT be called since retrain is in progress
        mock_handler.assert_not_called()

    @pytest.mark.asyncio
    async def test_consume_handler_exception(self):
        """Test handling exception from handler."""
        message_body = json.dumps({
            "requested_at": datetime.now(timezone.utc).isoformat()
        })
        
        mock_message = AsyncMock()
        mock_message.body = message_body.encode()
        mock_message.process = MagicMock(return_value=AsyncContextManager())
        
        # Setup queue iterator
        mock_queue = AsyncMock()
        mock_queue.iterator = MagicMock(return_value=AsyncIteratorContext(mock_message))
        
        # Setup redis
        mock_redis = AsyncMock()
        mock_redis.get = AsyncMock(return_value=None)  # Not in progress
        mock_redis.set = AsyncMock()
        mock_redis.close = AsyncMock()
        
        consumer = RetrainQueueConsumer()
        consumer.queue = mock_queue
        
        with patch("app.rabbitmq_consumer.aioredis.from_url", new_callable=AsyncMock) as mock_from_url:
            mock_from_url.return_value = mock_redis
            with patch("app.rabbitmq_consumer.handle_train_temperature_model") as mock_handler:
                mock_handler.side_effect = Exception("Handler failed")
                
                with patch("app.rabbitmq_consumer.os.getenv") as mock_getenv:
                    def getenv_side_effect(key, default=None):
                        if key == "REDIS_URL":
                            return "redis://redis:6379/0"
                        elif key == "OUTSIDE_TEMP_DATASTREAM_ID":
                            return "test-ds-id"
                        return default
                    
                    mock_getenv.side_effect = getenv_side_effect
                    
                    # Should handle exception gracefully
                    await consumer.start_consuming()
        
        # Should still process message despite exception
        mock_handler.assert_called()

    @pytest.mark.asyncio
    async def test_consume_sets_in_progress_flag(self):
        """Test that in-progress flag is set before processing."""
        message_body = json.dumps({
            "requested_at": datetime.now(timezone.utc).isoformat()
        })
        
        mock_message = AsyncMock()
        mock_message.body = message_body.encode()
        mock_message.process = MagicMock(return_value=AsyncContextManager())
        
        # Setup queue iterator
        mock_queue = AsyncMock()
        mock_queue.iterator = MagicMock(return_value=AsyncIteratorContext(mock_message))
        
        # Setup redis
        mock_redis = AsyncMock()
        mock_redis.get = AsyncMock(return_value=None)  # Not in progress
        mock_redis.set = AsyncMock()
        mock_redis.close = AsyncMock()
        
        consumer = RetrainQueueConsumer()
        consumer.queue = mock_queue
        
        with patch("app.rabbitmq_consumer.aioredis.from_url", new_callable=AsyncMock) as mock_from_url:
            mock_from_url.return_value = mock_redis
            with patch("app.rabbitmq_consumer.handle_train_temperature_model"):
                with patch("app.rabbitmq_consumer.os.getenv") as mock_getenv:
                    def getenv_side_effect(key, default=None):
                        if key == "REDIS_URL":
                            return "redis://redis:6379/0"
                        elif key == "OUTSIDE_TEMP_DATASTREAM_ID":
                            return "test-ds-id"
                        return default
                    
                    mock_getenv.side_effect = getenv_side_effect
                    
                    await consumer.start_consuming()
        
        # Verify in-progress flag was set
        mock_redis.set.assert_called_with("model:retrain:in_progress", "true", ex=600)


class TestRunRetrainConsumer:
    """Test main consumer entry point."""

    @pytest.mark.asyncio
    async def test_run_no_rabbitmq_url(self):
        """Test consumer skips if RABBITMQ_URL not set."""
        with patch("app.rabbitmq_consumer.RABBITMQ_URL", None):
            # Should complete without error
            await run_retrain_consumer()

    @pytest.mark.asyncio
    async def test_run_connection_error(self):
        """Test consumer handles connection error gracefully."""
        mock_consumer_class = AsyncMock()
        mock_consumer = AsyncMock()
        mock_consumer.connect = AsyncMock(side_effect=Exception("Connection failed"))
        mock_consumer.disconnect = AsyncMock()
        
        with patch("app.rabbitmq_consumer.RABBITMQ_URL", "amqp://rabbitmq:5672"):
            with patch("app.rabbitmq_consumer.RetrainQueueConsumer", return_value=mock_consumer):
                # Should not raise, error is caught
                await run_retrain_consumer()
        
        # Ensure disconnect is called even on error
        mock_consumer.disconnect.assert_called_once()

    @pytest.mark.asyncio
    async def test_run_successful_flow(self):
        """Test successful consumer flow."""
        mock_consumer = AsyncMock()
        mock_consumer.connect = AsyncMock()
        mock_consumer.start_consuming = AsyncMock()
        mock_consumer.disconnect = AsyncMock()
        
        with patch("app.rabbitmq_consumer.RABBITMQ_URL", "amqp://rabbitmq:5672"):
            with patch("app.rabbitmq_consumer.RetrainQueueConsumer", return_value=mock_consumer):
                await run_retrain_consumer()
        
        # Verify connection flow
        mock_consumer.connect.assert_called_once()
        mock_consumer.start_consuming.assert_called_once()
        mock_consumer.disconnect.assert_called_once()

    @pytest.mark.asyncio
    async def test_run_disconnect_always_called(self):
        """Test disconnect is called even if consuming fails."""
        mock_consumer = AsyncMock()
        mock_consumer.connect = AsyncMock()
        mock_consumer.start_consuming = AsyncMock(side_effect=Exception("Consuming failed"))
        mock_consumer.disconnect = AsyncMock()
        
        with patch("app.rabbitmq_consumer.RABBITMQ_URL", "amqp://rabbitmq:5672"):
            with patch("app.rabbitmq_consumer.RetrainQueueConsumer", return_value=mock_consumer):
                await run_retrain_consumer()
        
        # Disconnect should still be called in finally block
        mock_consumer.disconnect.assert_called_once()
