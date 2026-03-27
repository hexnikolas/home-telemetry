"""
Job handlers for background tasks
"""
import os
import time
import json
from typing import Any, Dict
import asyncio
import httpx
from app.queue import job_queue
from logger.logging_config import logger

# Configuration
API_URL = os.getenv("API_URL", "http://localhost:8000")
SYSTEMS_API_URL = f"{API_URL}/api/v1/systems/"
DATASTREAMS_API_URL = f"{API_URL}/api/v1/datastreams/"
REDIS_TOPIC_CONFIG_KEY = "mqtt:topic_config"
BATCH_SIZE = 100

# Auth configuration
API_CLIENT_ID = os.getenv("API_CLIENT_ID", "")
API_CLIENT_SECRET = os.getenv("API_CLIENT_SECRET", "")
# Derive token URL: strip /api/... suffix, append /auth/token
_api_base = API_URL.split("/api/")[0] if "/api/" in API_URL else API_URL
API_TOKEN_URL = f"{_api_base}/auth/token"


class TokenManager:
    """Caches and auto-refreshes an OAuth2 client credentials token."""

    def __init__(self) -> None:
        self._token: str = ""
        self._expires_at: float = 0.0
        self._refresh_buffer: int = 60  # refresh 60s before expiry

    def _is_valid(self) -> bool:
        return bool(self._token) and time.time() < self._expires_at - self._refresh_buffer

    async def get_token(self) -> str:
        if not self._is_valid():
            await self._fetch()
        return self._token

    async def _fetch(self) -> None:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                API_TOKEN_URL,
                data={
                    "grant_type": "client_credentials",
                    "client_id": API_CLIENT_ID,
                    "client_secret": API_CLIENT_SECRET,
                },
            )
            response.raise_for_status()
            payload = response.json()
            self._token = payload["access_token"]
            expires_in = payload.get("expires_in", 900)
            self._expires_at = time.time() + expires_in
            logger.info("Fetched new access token", extra={"expires_in": expires_in})


token_manager = TokenManager()


async def handle_sync_mqtt_topics_to_redis(data: Dict[str, Any]) -> None:
    """
    Fetch all SENSOR systems and their datastreams via the API.

    Builds mqtt:topic_config in Redis:
        { external_id: '{"model": "A1T", "datastreams": {"Power": "uuid", ...}}' }

    The "datastreams" dict is keyed by properties.mqtt_key on each datastream,
    so handlers can resolve payload field names to datastream IDs without any
    hardcoded UUIDs.
    """
    logger.info("Starting MQTT topic sync job")
    redis = job_queue.redis

    offset = 0
    total_topics = 0
    all_topic_config: Dict[str, str] = {}

    token = await token_manager.get_token()
    auth_headers = {"Authorization": f"Bearer {token}"}

    async with httpx.AsyncClient() as client:
        while True:
            try:
                logger.debug("Fetching systems from API", extra={"offset": offset, "limit": BATCH_SIZE})
                sys_response = await client.get(
                    SYSTEMS_API_URL,
                    params={"system_type": "SENSOR", "limit": BATCH_SIZE, "offset": offset},
                    headers=auth_headers,
                )

                if sys_response.status_code == 404:
                    logger.info("No more systems to fetch")
                    break

                sys_response.raise_for_status()
                systems = sys_response.json()

                if not systems:
                    break

                # Filter to systems that have both an external_id and a model
                valid_systems = [s for s in systems if s.get("external_id") and s.get("model")]

                if valid_systems:
                    system_ids = [s["id"] for s in valid_systems]

                    # Fetch all datastreams for this batch of systems in one call
                    ds_response = await client.get(
                        DATASTREAMS_API_URL,
                        params=[("system_ids", sid) for sid in system_ids],
                        headers=auth_headers,
                    )
                    ds_response.raise_for_status()
                    datastreams = ds_response.json()

                    # Group datastreams by system_id, keyed by mqtt_key
                    ds_by_system: Dict[str, Dict[str, str]] = {}
                    for ds in datastreams:
                        sid = ds.get("system_id")
                        mqtt_key = ds.get("properties", {}).get("mqtt_key")
                        if sid and mqtt_key:
                            ds_by_system.setdefault(sid, {})[mqtt_key] = ds["id"]

                    for s in valid_systems:
                        topic = s["external_id"]
                        config = {
                            "model": s["model"],
                            "datastreams": ds_by_system.get(s["id"], {}),
                        }
                        all_topic_config[topic] = json.dumps(config)
                        total_topics += 1

                    logger.info(
                        "Batch processed",
                        extra={"systems_fetched": len(systems), "topics_built": len(valid_systems)},
                    )

                if len(systems) < BATCH_SIZE:
                    logger.info("Reached end of systems")
                    break

                offset += BATCH_SIZE

            except httpx.HTTPError as e:
                logger.error("HTTP error during topic sync", extra={"error": str(e)})
                raise
            except Exception as e:
                logger.error("Unexpected error during MQTT topic sync", extra={"error": str(e)})
                raise

    if all_topic_config:
        # Remove stale topics
        current = await redis.hkeys(REDIS_TOPIC_CONFIG_KEY)
        stale = set(current) - set(all_topic_config.keys())
        if stale:
            logger.info("Removing stale topic configs", extra={"count": len(stale)})
            await redis.hdel(REDIS_TOPIC_CONFIG_KEY, *stale)

        await redis.hset(REDIS_TOPIC_CONFIG_KEY, mapping=all_topic_config)
        logger.info("MQTT topic config synced to Redis", extra={"total_topics": total_topics})
    else:
        logger.warning("No valid topics found — Redis not updated")

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


