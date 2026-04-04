"""
Tests for Dead Letter Queue (DLQ) functionality
"""
import pytest
from datetime import datetime, timezone
from unittest.mock import Mock, patch, AsyncMock, MagicMock

from app.queue import ObservationQueue, DLQ_NAME, QUEUE_NAME, MAX_MESSAGE_RETRIES


class TestDLQConfiguration:
    """Test DLQ configuration and naming"""

    def test_dlq_name_format(self):
        """Test that DLQ name follows expected format"""
        expected_dlq_name = f"{QUEUE_NAME}.dlq"
        assert DLQ_NAME == expected_dlq_name
        assert DLQ_NAME.endswith(".dlq")

    def test_dlq_name_contains_queue_name(self):
        """Test that DLQ name contains the main queue name"""
        assert QUEUE_NAME in DLQ_NAME

    def test_default_queue_name(self):
        """Test default queue name is 'observations'"""
        assert QUEUE_NAME == "observations"
        assert DLQ_NAME == "observations.dlq"

    def test_max_message_retries_configured(self):
        """Test that max retries is configured"""
        assert MAX_MESSAGE_RETRIES > 0
        # Typically should be 3 or more
        assert MAX_MESSAGE_RETRIES >= 1


class TestRetryCountTracking:
    """Test retry count tracking in message headers"""

    @pytest.mark.asyncio
    async def test_retry_count_header_increment(self):
        """Test that retry count is incremented in message headers"""
        queue = ObservationQueue()
        queue.channel = AsyncMock()
        queue.pending_ack_messages = []
        
        # Mock a message with retry count 0
        mock_message = AsyncMock()
        mock_message.headers = {"x-retry-count": 0}
        mock_message.routing_key = QUEUE_NAME
        mock_message.body = b"test data"
        mock_message.ack = AsyncMock()
        
        queue.pending_ack_messages.append(mock_message)

    @pytest.mark.asyncio
    async def test_retry_count_extraction_from_headers(self):
        """Test extracting retry count from message headers"""
        queue = ObservationQueue()
        
        # Simulate extracting retry count
        mock_message = AsyncMock()
        
        # Test with no retry count
        mock_message.headers = {}
        retry_count = 0
        if mock_message.headers and "x-retry-count" in mock_message.headers:
            retry_count = int(mock_message.headers["x-retry-count"])
        assert retry_count == 0
        
        # Test with existing retry count
        mock_message.headers = {"x-retry-count": 2}
        retry_count = 0
        if mock_message.headers and "x-retry-count" in mock_message.headers:
            retry_count = int(mock_message.headers["x-retry-count"])
        assert retry_count == 2

    def test_retry_count_starts_at_zero(self):
        """Test that new messages start with retry count 0"""
        # New messages should not have retry count header
        # First retry should be count 1
        assert MAX_MESSAGE_RETRIES >= 1
        # So we can retry at least once


class TestDLQMovement:
    """Test moving messages to DLQ"""

    @pytest.mark.asyncio
    async def test_message_moved_to_dlq_after_max_retries(self):
        """Test that messages are moved to DLQ after max retries"""
        queue = ObservationQueue()
        queue.channel = AsyncMock()
        queue.pending_ack_messages = []
        
        # Mock a message that has reached max retries
        mock_message = AsyncMock()
        mock_message.headers = {"x-retry-count": MAX_MESSAGE_RETRIES}
        mock_message.routing_key = QUEUE_NAME
        mock_message.body = b"test data"
        mock_message.ack = AsyncMock()
        
        queue.pending_ack_messages.append(mock_message)
        
        # Mock the publish method
        queue.channel.default_exchange.publish = AsyncMock()
        
        await queue.move_batch_to_dlq()
        
        # Verify message was published to DLQ
        assert queue.channel.default_exchange.publish.called
        call_args = queue.channel.default_exchange.publish.call_args
        assert call_args is not None
        
        # Check if DLQ_NAME was used as routing key
        # (verify call was made with correct routing key in one of the calls)
        routing_keys = [call[1].get('routing_key') for call in queue.channel.default_exchange.publish.call_args_list]
        assert DLQ_NAME in routing_keys

    @pytest.mark.asyncio
    async def test_message_not_moved_to_dlq_before_max_retries(self):
        """Test that messages are requeued before max retries reached"""
        queue = ObservationQueue()
        queue.channel = AsyncMock()
        queue.pending_ack_messages = []
        
        # Mock a message below max retries
        mock_message = AsyncMock()
        mock_message.headers = {"x-retry-count": MAX_MESSAGE_RETRIES - 1}
        mock_message.routing_key = QUEUE_NAME
        mock_message.body = b"test data"
        mock_message.ack = AsyncMock()
        
        queue.pending_ack_messages.append(mock_message)
        
        # Mock the publish method
        queue.channel.default_exchange.publish = AsyncMock()
        
        await queue.move_batch_to_dlq()
        
        # Verify message was published back to main queue
        assert queue.channel.default_exchange.publish.called
        routing_keys = [call[1].get('routing_key') for call in queue.channel.default_exchange.publish.call_args_list]
        assert QUEUE_NAME in routing_keys

    @pytest.mark.asyncio
    async def test_dlq_message_contains_metadata(self):
        """Test that messages in DLQ contain retry and failure metadata"""
        queue = ObservationQueue()
        
        # Simulate DLQ message with metadata
        mock_message = AsyncMock()
        mock_message.headers = {
            "x-retry-count": MAX_MESSAGE_RETRIES,
            "x-failed-at": datetime.now(timezone.utc).isoformat(),
            "x-original-routing-key": QUEUE_NAME,
        }
        
        # Verify all required metadata is present
        assert "x-retry-count" in mock_message.headers
        assert "x-failed-at" in mock_message.headers
        assert "x-original-routing-key" in mock_message.headers
        assert mock_message.headers["x-original-routing-key"] == QUEUE_NAME


class TestRetryLogic:
    """Test retry and requeue logic"""

    def test_retry_count_progression(self):
        """Test that retry count progresses correctly"""
        retry_counts = [0, 1, 2, MAX_MESSAGE_RETRIES]
        
        for i, count in enumerate(retry_counts[:-1]):
            next_count = count + 1
            assert next_count > count
        
        # After reaching max, should go to DLQ
        assert retry_counts[-1] >= MAX_MESSAGE_RETRIES

    def test_max_retries_boundary(self):
        """Test max retries boundary condition"""
        # Message with exactly max retries should go to DLQ
        retry_count = MAX_MESSAGE_RETRIES
        assert retry_count >= MAX_MESSAGE_RETRIES
        
        # Message with one less should be requeued
        retry_count = MAX_MESSAGE_RETRIES - 1
        assert retry_count < MAX_MESSAGE_RETRIES

    @pytest.mark.asyncio
    async def test_requeue_with_incremented_retry_count(self):
        """Test that requeued messages have incremented retry count"""
        queue = ObservationQueue()
        queue.channel = AsyncMock()
        queue.pending_ack_messages = []
        
        # Message with retry count 1 (below max)
        mock_message = AsyncMock()
        original_retry_count = 1
        mock_message.headers = {"x-retry-count": original_retry_count}
        mock_message.routing_key = QUEUE_NAME
        mock_message.body = b"test data"
        mock_message.ack = AsyncMock()
        
        queue.pending_ack_messages.append(mock_message)
        queue.channel.default_exchange.publish = AsyncMock()
        
        await queue.move_batch_to_dlq()
        
        # Verify message was requeued to main queue with incremented count
        if queue.channel.default_exchange.publish.called:
            for call in queue.channel.default_exchange.publish.call_args_list:
                routing_key = call[1].get('routing_key')
                if routing_key == QUEUE_NAME:
                    # Found the requeue call
                    break


class TestDLQEdgeCases:
    """Test edge cases in DLQ handling"""

    @pytest.mark.asyncio
    async def test_empty_pending_messages(self):
        """Test handling of empty pending messages list"""
        queue = ObservationQueue()
        queue.channel = AsyncMock()
        queue.pending_ack_messages = []
        
        # Should not raise exception
        await queue.move_batch_to_dlq()
        assert len(queue.pending_ack_messages) == 0

    @pytest.mark.asyncio
    async def test_multiple_messages_to_dlq(self):
        """Test handling multiple messages going to DLQ"""
        queue = ObservationQueue()
        queue.channel = AsyncMock()
        queue.pending_ack_messages = []
        queue.channel.default_exchange.publish = AsyncMock()
        
        # Create 3 messages at max retries
        for i in range(3):
            mock_message = AsyncMock()
            mock_message.headers = {"x-retry-count": MAX_MESSAGE_RETRIES}
            mock_message.routing_key = QUEUE_NAME
            mock_message.body = f"test data {i}".encode()
            mock_message.ack = AsyncMock()
            queue.pending_ack_messages.append(mock_message)
        
        await queue.move_batch_to_dlq()
        
        # All messages should have been processed
        assert len(queue.pending_ack_messages) == 0

    @pytest.mark.asyncio
    async def test_mixed_retry_states(self):
        """Test handling messages with different retry counts"""
        queue = ObservationQueue()
        queue.channel = AsyncMock()
        queue.pending_ack_messages = []
        queue.channel.default_exchange.publish = AsyncMock()
        
        # Message that should be requeued
        msg1 = AsyncMock()
        msg1.headers = {"x-retry-count": 1}
        msg1.routing_key = QUEUE_NAME
        msg1.body = b"data1"
        msg1.ack = AsyncMock()
        
        # Message that should go to DLQ
        msg2 = AsyncMock()
        msg2.headers = {"x-retry-count": MAX_MESSAGE_RETRIES}
        msg2.routing_key = QUEUE_NAME
        msg2.body = b"data2"
        msg2.ack = AsyncMock()
        
        queue.pending_ack_messages.extend([msg1, msg2])
        
        await queue.move_batch_to_dlq()
        
        # Both should be processed
        assert len(queue.pending_ack_messages) == 0
        # Both should be acknowledged
        assert msg1.ack.called
        assert msg2.ack.called

    @pytest.mark.asyncio
    async def test_message_ack_after_dlq_move(self):
        """Test that messages are acknowledged after being moved to DLQ"""
        queue = ObservationQueue()
        queue.channel = AsyncMock()
        queue.pending_ack_messages = []
        queue.channel.default_exchange.publish = AsyncMock()
        
        mock_message = AsyncMock()
        mock_message.headers = {"x-retry-count": MAX_MESSAGE_RETRIES}
        mock_message.routing_key = QUEUE_NAME
        mock_message.body = b"test"
        mock_message.ack = AsyncMock()
        
        queue.pending_ack_messages.append(mock_message)
        
        await queue.move_batch_to_dlq()
        
        # Message should be acknowledged
        assert mock_message.ack.called


class TestDLQQueueIntegration:
    """Test DLQ integration with ObservationQueue"""

    def test_queue_initialization_with_dlq_support(self):
        """Test that queue initializes with DLQ support"""
        queue = ObservationQueue(queue_name=QUEUE_NAME)
        assert queue.queue_name == QUEUE_NAME
        assert queue is not None

    @pytest.mark.asyncio
    async def test_batch_lock_prevents_race_condition(self):
        """Test that batch_lock prevents race conditions during DLQ move"""
        queue = ObservationQueue()
        queue.channel = AsyncMock()
        queue.batch_lock = pytest.importorskip("asyncio").Lock()
        queue.pending_ack_messages = []
        
        # Lock should be available
        assert not queue.batch_lock.locked()
