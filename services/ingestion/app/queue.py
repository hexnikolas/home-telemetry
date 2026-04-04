"""
RabbitMQ queue consumer for observations ingestion
Collects messages from queue and batches them for bulk API submission
"""
import json
import asyncio
from typing import List, Callable, Optional, Any
from datetime import datetime, timedelta, timezone
import aio_pika
import os
from shared.logger.logging_config import setup_logging_json, setup_logging_colored

LOG_FORMAT = os.getenv("LOG_FORMAT", "json")
if LOG_FORMAT == "colored":
    logger = setup_logging_colored("home-telemetry-ingestion-queue")
else:
    logger = setup_logging_json("home-telemetry-ingestion-queue")

RABBITMQ_URL = os.getenv("RABBITMQ_URL")

if not RABBITMQ_URL:
    raise ValueError("RABBITMQ_URL environment variable is not set")

QUEUE_NAME = os.getenv("QUEUE_NAME", "observations")
DLQ_NAME = f"{QUEUE_NAME}.dlq"  # Dead Letter Queue
BATCH_SIZE = int(os.getenv("BATCH_SIZE", "100"))
BATCH_TIMEOUT = int(os.getenv("BATCH_TIMEOUT", "5"))  # seconds
MAX_MESSAGE_RETRIES = int(os.getenv("MAX_MESSAGE_RETRIES", "3"))  # Max retries per message


class ObservationQueue:
    def __init__(self, rabbitmq_url: str = RABBITMQ_URL, queue_name: str = QUEUE_NAME, auto_ack: bool = True):
        self.rabbitmq_url = rabbitmq_url
        self.queue_name = queue_name
        self.auto_ack = auto_ack  # If False, messages won't be acknowledged
        self.connection: Optional[aio_pika.Connection] = None
        self.channel: Optional[aio_pika.Channel] = None
        self.queue: Optional[aio_pika.Queue] = None
        self.message_handler: Optional[Callable] = None
        self.batch: List[dict] = []
        self.batch_messages: List[aio_pika.IncomingMessage] = []  # Track original message objects
        self.pending_ack_messages: List[aio_pika.IncomingMessage] = []  # Messages waiting to be acknowledged
        self.batch_lock = asyncio.Lock()
        self.last_flush = datetime.now(timezone.utc)

    async def connect(self):
        """Initialize RabbitMQ connection"""
        try:
            self.connection = await aio_pika.connect(self.rabbitmq_url)
            self.channel = await self.connection.channel()
            self.queue = await self.channel.declare_queue(self.queue_name, durable=True)
            logger.info(f"[INGESTION] Connected to RabbitMQ queue: {self.queue_name}")
        except Exception as e:
            logger.error(f"[INGESTION] Failed to connect to RabbitMQ: {e}")
            raise

    async def disconnect(self):
        """Close RabbitMQ connection"""
        if self.connection:
            await self.connection.close()
            logger.info("[INGESTION] Disconnected from RabbitMQ")

    async def reconnect(self):
        """Reconnect to RabbitMQ"""
        try:
            if self.connection:
                await self.connection.close()
        except Exception:
            pass
        await self.connect()

    def register_handler(self, handler: Callable):
        """Register handler to process batches"""
        self.message_handler = handler
        logger.info("[INGESTION] Registered batch handler")

    async def add_to_batch(self, message: dict, rabbitmq_message: aio_pika.IncomingMessage = None):
        """Add message to batch, optionally tracking the original RabbitMQ message"""
        should_flush = False
        async with self.batch_lock:
            self.batch.append(message)
            if rabbitmq_message:
                self.batch_messages.append(rabbitmq_message)
            logger.debug(f"[INGESTION] Added message to batch. Batch size: {len(self.batch)}")
            
            # Check if we should flush, but don't hold lock during flush
            if len(self.batch) >= BATCH_SIZE:
                should_flush = True

        # Call flush outside the lock to prevent deadlock
        if should_flush:
            await self._flush_batch()

    async def ack_batch(self):
        """Acknowledge all pending messages after successful API submission"""
        async with self.batch_lock:
            for msg in self.pending_ack_messages:
                try:
                    await msg.ack()
                    logger.debug(f"[INGESTION] Acknowledged message")
                except Exception as e:
                    logger.error(f"[INGESTION] Failed to acknowledge message: {e}")
            count = len(self.pending_ack_messages)
            self.pending_ack_messages.clear()
            logger.info(f"[INGESTION] Acknowledged {count} messages")

    async def move_batch_to_dlq(self):
        """Move all pending messages to DLQ or requeue with incremented retry count"""
        async with self.batch_lock:
            for msg in self.pending_ack_messages:
                try:
                    # Get current retry count from message headers
                    retry_count = 0
                    if msg.headers and "x-retry-count" in msg.headers:
                        retry_count = int(msg.headers["x-retry-count"])
                    
                    if retry_count >= MAX_MESSAGE_RETRIES:
                        # Max retries exceeded - move to DLQ
                        await self.channel.default_exchange.publish(
                            aio_pika.Message(
                                body=msg.body,
                                headers={
                                    "x-retry-count": retry_count,
                                    "x-failed-at": datetime.now(timezone.utc).isoformat(),
                                    "x-original-routing-key": msg.routing_key,
                                },
                                delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
                            ),
                            routing_key=DLQ_NAME,
                        )
                        # ACK the original message (it's been moved to DLQ)
                        await msg.ack()
                        logger.warning(f"[INGESTION] Message moved to DLQ after {retry_count} retries")
                    else:
                        # Republish with incremented retry count
                        await self.channel.default_exchange.publish(
                            aio_pika.Message(
                                body=msg.body,
                                headers={"x-retry-count": retry_count + 1},
                                delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
                            ),
                            routing_key=QUEUE_NAME,
                        )
                        # ACK the original message (it's been requeued with new retry count)
                        await msg.ack()
                        logger.debug(f"[INGESTION] Message requeued with retry count {retry_count + 1}")
                        
                except Exception as e:
                    logger.error(f"[INGESTION] Failed to handle failed message: {e}")
                    # As fallback, NACK to requeue
                    try:
                        await msg.nack(requeue=True)
                    except:
                        pass
            
            count = len(self.pending_ack_messages)
            self.pending_ack_messages.clear()
            logger.info(f"[INGESTION] Processed {count} failed messages (retry or DLQ)")

    async def _should_flush(self) -> bool:
        """Check if batch should be flushed based on time or size"""
        if not self.batch:
            return False
        
        time_since_last_flush = (datetime.now(timezone.utc) - self.last_flush).total_seconds()
        return time_since_last_flush >= BATCH_TIMEOUT or len(self.batch) >= BATCH_SIZE

    async def _flush_batch(self):
        """Flush current batch to handler"""
        batch_to_send = None
        messages_to_ack = None

        # Prepare batch while holding lock
        async with self.batch_lock:
            if not self.batch or not self.message_handler:
                return

            batch_to_send = self.batch.copy()
            messages_to_ack = self.batch_messages.copy()
            self.batch.clear()
            self.batch_messages.clear()
            self.last_flush = datetime.now(timezone.utc)
            
            # Move messages to pending BEFORE calling handler (so ack_batch() has them available)
            self.pending_ack_messages.extend(messages_to_ack)

        # Call handler OUTSIDE the lock to prevent deadlock when handler calls ack_batch()
        try:
            logger.info(f"[INGESTION] Flushing batch with {len(batch_to_send)} messages")
            await self.message_handler(batch_to_send)
        except Exception as e:
            logger.error(f"[INGESTION] Error processing batch: {e}")
            logger.warning("[INGESTION] Messages in failed batch will be NACKed and retried")

    async def consume_messages(self):
        """Consume messages from queue and add to batch"""
        if not self.queue:
            raise RuntimeError("Queue not initialized. Call connect() first.")

        logger.info("[INGESTION] Starting message consumption...")
        
        async def message_callback(message: aio_pika.IncomingMessage):
            # If auto_ack is False, don't acknowledge the message
            if self.auto_ack:
                async with message.process():
                    try:
                        body = json.loads(message.body.decode())
                        # Extract routing key from RabbitMQ message metadata
                        routing_key = message.routing_key
                        body["topic"] = routing_key
                        logger.debug(f"[INGESTION] Received message: {body}")
                        await self.add_to_batch(body)
                    except json.JSONDecodeError as e:
                        logger.error(f"[INGESTION] Failed to decode message: {e}")
                    except Exception as e:
                        logger.error(f"[INGESTION] Error processing message: {e}")
            else:
                # No auto-ack mode - process message without acknowledging, but track it
                try:
                    body = json.loads(message.body.decode())
                    # Extract routing key from RabbitMQ message metadata
                    routing_key = message.routing_key
                    body["topic"] = routing_key
                    logger.debug(f"[INGESTION] Received message (NO-ACK): {body}")
                    # Track original message for later acknowledgment
                    await self.add_to_batch(body, rabbitmq_message=message)
                except json.JSONDecodeError as e:
                    logger.error(f"[INGESTION] Failed to decode message: {e}")
                except Exception as e:
                    logger.error(f"[INGESTION] Error processing message: {e}")

        # Consume messages
        async with self.queue.iterator() as queue_iter:
            async for message in queue_iter:
                await message_callback(message)

    async def flush_periodically(self):
        """Periodically flush batch if threshold time is reached"""
        logger.info("[INGESTION] Starting periodic batch flush timer")
        
        while True:
            try:
                await asyncio.sleep(1)  # Check every second
                should_flush = False
                
                async with self.batch_lock:
                    if await self._should_flush():
                        should_flush = True

                # Call flush outside the lock to prevent deadlock
                if should_flush:
                    await self._flush_batch()
                    
            except asyncio.CancelledError:
                logger.info("[INGESTION] Periodic flush task cancelled")
                # Final flush before exit
                async with self.batch_lock:
                    if self.batch:
                        await self._flush_batch()
                break
            except Exception as e:
                logger.error(f"[INGESTION] Error in periodic flush: {e}")

    async def start_consuming(self):
        """Start consuming messages with periodic flush"""
        if not self.message_handler:
            raise RuntimeError("No message handler registered. Call register_handler() first.")

        # Start periodic flush task
        flush_task = asyncio.create_task(self.flush_periodically())
        
        try:
            # Start consuming (blocks indefinitely)
            await self.consume_messages()
        except KeyboardInterrupt:
            logger.info("[INGESTION] Consume interrupted")
        finally:
            flush_task.cancel()
            try:
                await flush_task
            except asyncio.CancelledError:
                pass
