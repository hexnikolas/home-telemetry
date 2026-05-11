"""
RabbitMQ consumer for model retrain requests
Listens to model.retrain queue and processes retrain messages
"""
import json
import os
import asyncio
import aio_pika
import redis.asyncio as aioredis
from typing import Optional, Dict, Any
from datetime import datetime, timezone
from logger.logging_config import setup_logging_json, setup_logging_colored
from app.handlers import handle_train_temperature_model

LOG_FORMAT = os.getenv("LOG_FORMAT", "json")
if LOG_FORMAT == "colored":
    logger = setup_logging_colored("home-telemetry-jobs-retrain")
else:
    logger = setup_logging_json("home-telemetry-jobs-retrain")

RABBITMQ_URL = os.getenv("RABBITMQ_URL")
QUEUE_NAME = "model.retrain"


class RetrainQueueConsumer:
    """Consumes retrain messages from RabbitMQ and processes them"""
    
    def __init__(self, rabbitmq_url: str = RABBITMQ_URL, queue_name: str = QUEUE_NAME):
        self.rabbitmq_url = rabbitmq_url
        self.queue_name = queue_name
        self.connection: Optional[aio_pika.Connection] = None
        self.channel: Optional[aio_pika.Channel] = None
        self.queue: Optional[aio_pika.Queue] = None
    
    async def connect(self):
        """Initialize RabbitMQ connection"""
        try:
            self.connection = await aio_pika.connect(self.rabbitmq_url)
            self.channel = await self.connection.channel()
            self.queue = await self.channel.declare_queue(self.queue_name, durable=True)
            logger.info(f"[RETRAIN] Connected to RabbitMQ queue: {self.queue_name}")
        except Exception as e:
            logger.error(f"[RETRAIN] Failed to connect to RabbitMQ: {e}")
            raise
    
    async def disconnect(self):
        """Close RabbitMQ connection"""
        if self.connection:
            await self.connection.close()
            logger.info("[RETRAIN] Disconnected from RabbitMQ")
    
    async def start_consuming(self):
        """Start consuming messages from the queue"""
        if not self.queue:
            raise RuntimeError("Not connected to RabbitMQ")
        
        logger.info("[RETRAIN] Starting to consume messages")
        
        async with self.queue.iterator() as queue_iter:
            async for message in queue_iter:
                async with message.process():
                    try:
                        # Parse message first
                        body = json.loads(message.body.decode())
                        datastream_id = body.get("datastream_id") or os.getenv("OUTSIDE_TEMP_DATASTREAM_ID")
                        requested_at = body.get("requested_at")
                        
                        # Check if retrain is already in progress (prevent concurrent retrains)
                        redis = await aioredis.from_url(
                            os.getenv("REDIS_URL", "redis://redis:6379/0"),
                            decode_responses=True
                        )
                        
                        in_progress = await redis.get("model:retrain:in_progress")
                        
                        if in_progress:
                            logger.info("[RETRAIN] Retrain already in progress, skipping duplicate message")
                            await redis.close()
                            # Message is ACK'd automatically by the async with block
                            continue
                        
                        # Set the in-progress flag NOW (before processing starts)
                        await redis.set("model:retrain:in_progress", "true", ex=600)  # 10 min timeout
                        await redis.close()
                        
                        logger.info(
                            "[RETRAIN] Received retrain message",
                            extra={
                                "datastream_id": datastream_id,
                                "requested_at": requested_at,
                            }
                        )
                        
                        # Call the handler
                        result = await handle_train_temperature_model(
                            ctx=None,
                            data={"datastream_id": datastream_id}
                        )
                        
                        logger.info(
                            "[RETRAIN] Retrain completed",
                            extra={
                                "result": result,
                            }
                        )
                    
                    except json.JSONDecodeError as e:
                        logger.error(f"[RETRAIN] Failed to parse message: {e}")
                    except Exception as e:
                        logger.exception(f"[RETRAIN] Failed to process retrain message: {e}")


async def run_retrain_consumer():
    """Run the retrain queue consumer"""
    if not RABBITMQ_URL:
        logger.warning("[RETRAIN] RABBITMQ_URL not set, skipping consumer")
        return
    
    consumer = RetrainQueueConsumer(RABBITMQ_URL, QUEUE_NAME)
    
    try:
        await consumer.connect()
        await consumer.start_consuming()
    except Exception as e:
        logger.error(f"[RETRAIN] Consumer crashed: {e}")
    finally:
        await consumer.disconnect()
