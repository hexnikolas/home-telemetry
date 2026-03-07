"""
Job handlers for background tasks
"""
from typing import Any, Dict
import asyncio
import httpx
from app.queue import job_queue

REDIS_MQTT_TOPICS_KEY = "mqtt:topics"
BATCH_SIZE = 100
SYSTEMS_API_URL = "http://localhost:8000/api/v1/systems/"  # adjust to your base URL

async def handle_sync_mqtt_topics_to_redis(data: Dict[str, Any]) -> None:
    """
    Fetch all SENSOR systems via HTTP API, extract their external_id,
    and add them to a Redis Set for the MQTT client to consume.
    """
    redis = job_queue.redis

    offset = 0
    added = 0

    async with httpx.AsyncClient() as client:
        while True:
            response = await client.get(
                SYSTEMS_API_URL,
                params={
                    "system_type": "SENSOR",
                    "limit": BATCH_SIZE,
                    "offset": offset
                }
            )

            if response.status_code == 404:
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
                    await redis.hdel("mqtt:topic_models", *stale)
                await redis.hset("mqtt:topic_models", mapping=topics_with_models)
                added += len(topics_with_models)
                print(f"[JOBS] Fetched {len(systems)} systems, adding {len(topics_with_models)} topics to Redis")

            
            if len(systems) < BATCH_SIZE:
                break

            offset += BATCH_SIZE

    print(f"[JOBS] MQTT topic sync complete - topics added to Redis")

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
    print(f"[JOBS] Processing observations for datastream {data.get('datastream_id')}")
    
    # TODO: Implement actual processing logic
    # This could aggregate data, run calculations, etc.
    await asyncio.sleep(1)
    
    return {
        "processed_observations": 150,
        "datastream_id": data.get('datastream_id'),
        "status": "success"
    }


