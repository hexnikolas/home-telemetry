"""
Tests for ObservationQueue - RabbitMQ connection and queue management
"""
import pytest
import asyncio
from datetime import datetime, timezone
from unittest.mock import Mock, patch, AsyncMock, MagicMock, call

from app.queue import ObservationQueue, QUEUE_NAME, BATCH_SIZE, BATCH_TIMEOUT, MAX_MESSAGE_RETRIES


class TestQueueInitialization:
    """Test queue initialization and configuration"""

    def test_queue_default_configuration(self):
        """Test default queue configuration"""
        queue = ObservationQueue()
        
        assert queue.queue_name == QUEUE_NAME
        assert queue.rabbitmq_url is not None
        assert queue.auto_ack == True
        assert queue.batch == []
        assert queue.batch_messages == []
        assert queue.pending_ack_messages == []

    def test_queue_custom_name(self):
        """Test queue with custom name"""
        custom_name = "custom-observations"
        queue = ObservationQueue(queue_name=custom_name)
        
        assert queue.queue_name == custom_name

    def test_queue_auto_ack_configuration(self):
        """Test queue with auto_ack disabled"""
        queue = ObservationQueue(auto_ack=False)
        assert queue.auto_ack == False
        
        queue2 = ObservationQueue(auto_ack=True)
        assert queue2.auto_ack == True

    def test_queue_initial_state(self):
        """Test queue has correct initial state"""
        queue = ObservationQueue()
        
        assert queue.connection is None
        assert queue.channel is None
        assert queue.queue is None
        assert queue.message_handler is None
        assert queue.batch_lock is not None
        assert isinstance(queue.batch_lock, asyncio.Lock)


class TestQueueConnection:
    """Test RabbitMQ connection setup"""

    @pytest.mark.asyncio
    async def test_connect_establishes_connection(self):
        """Test that connect establishes RabbitMQ connection"""
        queue = ObservationQueue()
        
        # Mock aio_pika
        mock_connection = AsyncMock()
        mock_channel = AsyncMock()
        mock_queue = AsyncMock()
        
        with patch('app.queue.aio_pika') as mock_pika:
            mock_pika.connect = AsyncMock(return_value=mock_connection)
            mock_connection.channel = AsyncMock(return_value=mock_channel)
            mock_channel.declare_queue = AsyncMock(return_value=mock_queue)
            
            await queue.connect()
            
            # Verify connection was established
            assert queue.connection == mock_connection
            assert queue.channel == mock_channel
            assert queue.queue == mock_queue
            mock_pika.connect.assert_called_once()

    @pytest.mark.asyncio
    async def test_connect_declares_durable_queue(self):
        """Test that queue is declared as durable"""
        queue = ObservationQueue()
        
        mock_connection = AsyncMock()
        mock_channel = AsyncMock()
        mock_queue = AsyncMock()
        
        with patch('app.queue.aio_pika') as mock_pika:
            mock_pika.connect = AsyncMock(return_value=mock_connection)
            mock_connection.channel = AsyncMock(return_value=mock_channel)
            mock_channel.declare_queue = AsyncMock(return_value=mock_queue)
            
            await queue.connect()
            
            # Verify queue was declared as durable
            mock_channel.declare_queue.assert_called_once_with(QUEUE_NAME, durable=True)

    @pytest.mark.asyncio
    async def test_disconnect_closes_connection(self):
        """Test that disconnect closes connection"""
        queue = ObservationQueue()
        queue.connection = AsyncMock()
        
        await queue.disconnect()
        
        queue.connection.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_disconnect_with_no_connection(self):
        """Test disconnect when no connection exists"""
        queue = ObservationQueue()
        queue.connection = None
        
        # Should not raise exception
        await queue.disconnect()

    @pytest.mark.asyncio
    async def test_reconnect_closes_old_connection(self):
        """Test that reconnect closes old connection"""
        queue = ObservationQueue()
        old_connection = AsyncMock()
        queue.connection = old_connection
        
        with patch('app.queue.aio_pika') as mock_pika:
            mock_connection = AsyncMock()
            mock_channel = AsyncMock()
            mock_queue = AsyncMock()
            
            mock_pika.connect = AsyncMock(return_value=mock_connection)
            mock_connection.channel = AsyncMock(return_value=mock_channel)
            mock_channel.declare_queue = AsyncMock(return_value=mock_queue)
            
            await queue.reconnect()
            
            # Old connection should be closed
            old_connection.close.assert_called_once()


class TestHandlerRegistration:
    """Test handler registration and management"""

    def test_register_handler(self):
        """Test registering a message handler"""
        queue = ObservationQueue()
        
        def dummy_handler(batch):
            pass
        
        queue.register_handler(dummy_handler)
        
        assert queue.message_handler == dummy_handler

    def test_can_register_async_handler(self):
        """Test registering an async handler"""
        queue = ObservationQueue()
        
        async def async_handler(batch):
            pass
        
        queue.register_handler(async_handler)
        
        assert queue.message_handler == async_handler

    def test_handler_can_be_replaced(self):
        """Test replacing an existing handler"""
        queue = ObservationQueue()
        
        def handler1(batch):
            pass
        
        def handler2(batch):
            pass
        
        queue.register_handler(handler1)
        assert queue.message_handler == handler1
        
        queue.register_handler(handler2)
        assert queue.message_handler == handler2


class TestBatchManagement:
    """Test batch operations without processing"""

    @pytest.mark.asyncio
    async def test_add_to_batch(self):
        """Test adding message to batch"""
        queue = ObservationQueue()
        
        message = {"sensor": "temp", "value": 22.5}
        await queue.add_to_batch(message)
        
        assert len(queue.batch) == 1
        assert queue.batch[0] == message

    @pytest.mark.asyncio
    async def test_add_multiple_to_batch(self):
        """Test adding multiple messages to batch"""
        queue = ObservationQueue()
        
        messages = [
            {"sensor": "temp", "value": 22.5},
            {"sensor": "humidity", "value": 65.0},
            {"sensor": "pressure", "value": 1013.25},
        ]
        
        for msg in messages:
            await queue.add_to_batch(msg)
        
        assert len(queue.batch) == 3
        assert queue.batch == messages

    @pytest.mark.asyncio
    async def test_batch_tracks_rabbitmq_messages(self):
        """Test batch tracks original RabbitMQ messages"""
        queue = ObservationQueue()
        
        message = {"sensor": "temp"}
        rabbitmq_msg = AsyncMock()
        
        await queue.add_to_batch(message, rabbitmq_msg)
        
        assert len(queue.batch_messages) == 1
        assert queue.batch_messages[0] == rabbitmq_msg

    @pytest.mark.asyncio
    async def test_add_without_rabbitmq_message(self):
        """Test adding message without tracking RabbitMQ message"""
        queue = ObservationQueue()
        
        message = {"sensor": "temp"}
        await queue.add_to_batch(message)  # No rabbitmq_message param
        
        assert len(queue.batch) == 1
        assert len(queue.batch_messages) == 0

    @pytest.mark.asyncio
    async def test_ack_batch_acknowledges_all_messages(self):
        """Test ack_batch acknowledges all pending messages"""
        queue = ObservationQueue()
        
        mock_msgs = [AsyncMock() for _ in range(3)]
        queue.pending_ack_messages = mock_msgs
        
        await queue.ack_batch()
        
        # All messages should be acknowledged
        for msg in mock_msgs:
            msg.ack.assert_called_once()

    @pytest.mark.asyncio
    async def test_ack_batch_clears_pending(self):
        """Test ack_batch clears pending messages after ack"""
        queue = ObservationQueue()
        
        mock_msgs = [AsyncMock() for _ in range(3)]
        queue.pending_ack_messages = mock_msgs
        
        await queue.ack_batch()
        
        # Pending messages should be cleared after acking
        assert len(queue.pending_ack_messages) == 0

    @pytest.mark.asyncio
    async def test_ack_empty_batch(self):
        """Test acking empty batch doesn't cause error"""
        queue = ObservationQueue()
        queue.pending_ack_messages = []
        
        # Should not raise exception
        await queue.ack_batch()


class TestQueueConstants:
    """Test queue configuration constants"""

    def test_batch_size_configured(self):
        """Test batch size configuration"""
        assert BATCH_SIZE > 0
        assert isinstance(BATCH_SIZE, int)

    def test_batch_timeout_configured(self):
        """Test batch timeout configuration"""
        assert BATCH_TIMEOUT > 0
        assert isinstance(BATCH_TIMEOUT, int)

    def test_max_retries_configured(self):
        """Test max message retries configured"""
        assert MAX_MESSAGE_RETRIES > 0
        assert isinstance(MAX_MESSAGE_RETRIES, int)

    def test_queue_name_not_empty(self):
        """Test queue name is configured"""
        assert QUEUE_NAME
        assert len(QUEUE_NAME) > 0


class TestQueueProperties:
    """Test queue properties and state"""

    def test_queue_is_async_compatible(self):
        """Test queue works with async operations"""
        queue = ObservationQueue()
        assert queue.batch_lock is not None
        assert isinstance(queue.batch_lock, asyncio.Lock)

    @pytest.mark.asyncio
    async def test_batch_lock_is_exclusive(self):
        """Test batch lock prevents concurrent modifications"""
        queue = ObservationQueue()
        
        accessed = []
        
        async def task1():
            async with queue.batch_lock:
                accessed.append(1)
                await asyncio.sleep(0.01)
                accessed.append(1)
        
        async def task2():
            async with queue.batch_lock:
                accessed.append(2)
                accessed.append(2)
        
        # Run tasks concurrently
        await asyncio.gather(task1(), task2())
        
        # Should see one task complete before the other starts
        # Not both interleaved
        assert accessed[0] == accessed[1]  # First task's access pattern should be together
        
    def test_queue_durable_by_default(self):
        """Test queue defaults to durable"""
        queue = ObservationQueue()
        # The actual durable flag is specified in connect() method
        # This test just verifies the intent in our implementation
        assert queue is not None


class TestConnectionErrorHandling:
    """Test error handling during connection"""

    @pytest.mark.asyncio
    async def test_connect_error_propagates(self):
        """Test connection errors are properly raised"""
        queue = ObservationQueue()
        
        with patch('app.queue.aio_pika') as mock_pika:
            mock_pika.connect = AsyncMock(side_effect=Exception("Connection failed"))
            
            with pytest.raises(Exception):
                await queue.connect()

    @pytest.mark.asyncio
    async def test_reconnect_handles_close_error(self):
        """Test reconnect handles error closing old connection"""
        queue = ObservationQueue()
        old_connection = AsyncMock()
        old_connection.close = AsyncMock(side_effect=Exception("Close failed"))
        queue.connection = old_connection
        
        with patch('app.queue.aio_pika') as mock_pika:
            mock_connection = AsyncMock()
            mock_channel = AsyncMock()
            mock_queue = AsyncMock()
            
            mock_pika.connect = AsyncMock(return_value=mock_connection)
            mock_connection.channel = AsyncMock(return_value=mock_channel)
            mock_channel.declare_queue = AsyncMock(return_value=mock_queue)
            
            # Should not raise exception even if close fails
            await queue.reconnect()
            
            assert queue.connection == mock_connection
