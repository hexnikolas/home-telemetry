"""
Job handlers for background tasks
"""
import os
from typing import Any, Dict
import asyncio
import httpx
from app.queue import job_queue
from logger.logging_config import logger

# Configuration
API_URL = os.getenv("API_URL", "http://localhost:8000")
SYSTEMS_API_URL = f"{API_URL}/api/v1/systems/"
REDIS_MQTT_TOPICS_KEY = "mqtt:topics"
BATCH_SIZE = 100


async def handle_sync_mqtt_topics_to_redis(data: Dict[str, Any]) -> None:
    """
    Fetch all SENSOR systems via HTTP API, extract their external_id,
    and add them to a Redis Set for the MQTT client to consume.
    """
    logger.info("Starting MQTT topic sync job")
    redis = job_queue.redis

    offset = 0
    added = 0

    async with httpx.AsyncClient() as client:
        while True:
            try:
                logger.debug("Fetching systems from API", extra={"offset": offset, "limit": BATCH_SIZE})
                response = await client.get(
                    SYSTEMS_API_URL,
                    params={
                        "system_type": "SENSOR",
                        "limit": BATCH_SIZE,
                        "offset": offset
                    }
                )

                if response.status_code == 404:
                    logger.info("No more systems to fetch")
                    break

                response.raise_for_status()
                systems = response.json()

                topics_with_models = {
                    s["external_id"]: s["model"]
                    for s in systems
                    if s.get("external_id") and s.get("model")
                }

                if topics_with_models:
                    current = await redis.hgetall("mqtt:topic_models")
                    stale = set(current.keys()) - set(topics_with_models.keys())
                    if stale:
                        logger.info("Removing stale MQTT topics", extra={"count": len(stale)})
                        await redis.hdel("mqtt:topic_models", *stale)
                    await redis.hset("mqtt:topic_models", mapping=topics_with_models)
                    added += len(topics_with_models)
                    logger.info(
                        "Batch processed and synced to Redis",
                        extra={
                            "systems_fetched": len(systems),
                            "topics_added": len(topics_with_models),
                            "total_added": added
                        }
                    )

                
                if len(systems) < BATCH_SIZE:
                    logger.info("Reached end of systems")
                    break

                offset += BATCH_SIZE
            except httpx.HTTPError as e:
                logger.error("HTTP error during system fetch", extra={"error": str(e)})
                raise
            except Exception as e:
                logger.error("Unexpected error during MQTT topic sync", extra={"error": str(e)})
                raise

    logger.info("MQTT topic sync complete", extra={"total_topics_added": added})

# Example: Data processing job
async def handle_process_observations(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Example job for processing observations in bulk.
    
    data format: {
        "datastream_id": "uuid",
        "start_time": "2024-03-06T00:00:00Z",
        "end_time": "2024-03-06T23:59:59Z"
    }
    """
    datastream_id = data.get('datastream_id')
    logger.info("Processing observations", extra={"datastream_id": datastream_id})
    
    # TODO: Implement actual processing logic
    # This could aggregate data, run calculations, etc.
    await asyncio.sleep(1)
    
    logger.info("Observation processing complete", extra={"datastream_id": datastream_id, "processed": 150})
    
    return {
        "processed_observations": 150,
        "datastream_id": datastream_id,
        "status": "success"
    }


