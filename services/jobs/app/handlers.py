"""
Job handlers for background tasks
"""
import os
import time
import json
from typing import Any, Dict, Optional
import asyncio
import httpx
from datetime import datetime, timezone
from logger.logging_config import logger

# Configuration
API_URL = os.getenv("API_URL", "http://localhost:8000")
SYSTEMS_API_URL = f"{API_URL}/api/v1/systems/"
DATASTREAMS_API_URL = f"{API_URL}/api/v1/datastreams/"
OBSERVATIONS_API_URL = f"{API_URL}/api/v1/observations/"
REDIS_TOPIC_CONFIG_KEY = "mqtt:topic_config"
BATCH_SIZE = 100

# Open Meteo configuration
OPEN_METEO_API_URL = "https://api.open-meteo.com/v1/forecast"
OPEN_METEO_LATITUDE = float(os.getenv("OPEN_METEO_LATITUDE", "37.7749"))
OPEN_METEO_LONGITUDE = float(os.getenv("OPEN_METEO_LONGITUDE", "-122.4194"))

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
        async with httpx.AsyncClient(timeout=30.0) as client:
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


async def handle_sync_mqtt_topics_to_redis(ctx, data: Optional[Dict[str, Any]] = None) -> None:
    """
    Fetch all SENSOR systems and their datastreams via the API.

    Builds mqtt:topic_config in Redis:
        { external_id: '{"model": "A1T", "datastreams": {"Power": "uuid", ...}}' }

    The "datastreams" dict is keyed by properties.mqtt_key on each datastream,
    so handlers can resolve payload field names to datastream IDs without any
    hardcoded UUIDs.
    """
    logger.info("Starting MQTT topic sync job")
    redis = ctx["redis"] if ctx else None

    offset = 0
    total_topics = 0
    all_topic_config: Dict[str, str] = {}

    token = await token_manager.get_token()
    auth_headers = {"Authorization": f"Bearer {token}"}

    async with httpx.AsyncClient(timeout=30.0) as client:
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
async def handle_process_observations(ctx, data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Example job for processing observations in bulk.
    
    data format: {
        "datastream_id": "uuid",
        "start_time": "2024-03-06T00:00:00Z",
        "end_time": "2024-03-06T23:59:59Z"
    }
    """
    if data is None:
        data = {}
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


async def handle_fetch_open_meteo_data(ctx, data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Fetch current weather data from Open Meteo API and create observations.
    
    This job:
    1. Queries for the "Open Meteo" system dynamically using the q filter
    2. Fetches its datastreams
    3. Maps datastreams to temperature, humidity, and dew point properties
    4. Fetches current weather from Open Meteo
    5. Creates observations for each datastream
    
    data format: {} (empty - uses env variables for location)
    """
    if data is None:
        data = {}
    logger.info("Starting Open Meteo data fetch job")
    
    token = await token_manager.get_token()
    auth_headers = {"Authorization": f"Bearer {token}"}
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            # 1. Find the Open Meteo system using q filter
            logger.debug("Querying for Open Meteo system")
            sys_response = await client.get(
                SYSTEMS_API_URL,
                params={"q": "Open Meteo", "limit": 10},
                headers=auth_headers,
            )
            sys_response.raise_for_status()
            systems = sys_response.json()
            
            if not systems:
                logger.error("Open Meteo system not found")
                return {"status": "error", "message": "Open Meteo system not found"}
            
            system = systems[0]
            system_id = system["id"]
            logger.info("Found Open Meteo system", extra={"system_id": system_id})
            
            # 2. Get datastreams for this system
            logger.debug("Fetching datastreams for system", extra={"system_id": system_id})
            ds_response = await client.get(
                DATASTREAMS_API_URL,
                params={"system_id": system_id, "limit": 100},
                headers=auth_headers,
            )
            ds_response.raise_for_status()
            datastreams = ds_response.json()
            
            if not datastreams:
                logger.error("No datastreams found for Open Meteo system")
                return {"status": "error", "message": "No datastreams found"}
            
            # 3. Map datastreams by name
            ds_mapping = {}
            for ds in datastreams:
                name_lower = ds["name"].lower()
                if "temperature" in name_lower:
                    ds_mapping["temperature"] = ds
                elif "humidity" in name_lower:
                    ds_mapping["humidity"] = ds
                elif "dew" in name_lower and "point" in name_lower:
                    ds_mapping["dew_point"] = ds
            
            logger.info(
                "Mapped datastreams",
                extra={
                    "temperature": ds_mapping.get("temperature", {}).get("id"),
                    "humidity": ds_mapping.get("humidity", {}).get("id"),
                    "dew_point": ds_mapping.get("dew_point", {}).get("id"),
                }
            )
            
            # 4. Fetch current weather from Open Meteo
            logger.debug(
                "Fetching Open Meteo data",
                extra={"latitude": OPEN_METEO_LATITUDE, "longitude": OPEN_METEO_LONGITUDE}
            )
            weather_response = await client.get(
                OPEN_METEO_API_URL,
                params={
                    "latitude": OPEN_METEO_LATITUDE,
                    "longitude": OPEN_METEO_LONGITUDE,
                    "current": "temperature_2m,relative_humidity_2m,dew_point_2m",
                    "timezone": "auto"
                }
            )
            weather_response.raise_for_status()
            weather_data = weather_response.json()
            
            current = weather_data.get("current", {})
            logger.info(
                "Fetched Open Meteo data",
                extra={
                    "temperature": current.get("temperature_2m"),
                    "humidity": current.get("relative_humidity_2m"),
                    "dew_point": current.get("dew_point_2m"),
                }
            )
            
            # 5. Create observations for each datastream
            current_time = datetime.now(timezone.utc).isoformat()
            observations_payload = []
            
            # Temperature observation
            if "temperature" in ds_mapping and current.get("temperature_2m") is not None:
                temp_value = current["temperature_2m"]
                observations_payload.append({
                    "datastream_id": ds_mapping["temperature"]["id"],
                    "result_time": current_time,
                    "result_numeric": temp_value
                })
                logger.debug("Prepared temperature observation", extra={"value": temp_value})
            
            # Humidity observation
            if "humidity" in ds_mapping and current.get("relative_humidity_2m") is not None:
                humidity_value = current["relative_humidity_2m"]
                observations_payload.append({
                    "datastream_id": ds_mapping["humidity"]["id"],
                    "result_time": current_time,
                    "result_numeric": humidity_value
                })
                logger.debug("Prepared humidity observation", extra={"value": humidity_value})
            
            # Dew point observation
            if "dew_point" in ds_mapping and current.get("dew_point_2m") is not None:
                dew_point_value = current["dew_point_2m"]
                observations_payload.append({
                    "datastream_id": ds_mapping["dew_point"]["id"],
                    "result_time": current_time,
                    "result_numeric": dew_point_value
                })
                logger.debug("Prepared dew point observation", extra={"value": dew_point_value})
            
            # Create all observations in bulk
            if observations_payload:
                logger.debug("Creating observations in bulk", extra={"count": len(observations_payload)})
                obs_resp = await client.post(
                    f"{OBSERVATIONS_API_URL}bulk",
                    json=observations_payload,
                    headers=auth_headers,
                )
                obs_resp.raise_for_status()
                observations_created = len(observations_payload)
                logger.info("Open Meteo data fetch job complete", extra={"observations_created": observations_created})
            else:
                logger.warning("No observations to create (no data available from Open Meteo)")
                observations_created = 0
            
            return {
                "status": "success",
                "observations_created": observations_created,
                "system_id": system_id
            }
    
    except httpx.HTTPError as e:
        logger.error("HTTP error during Open Meteo fetch", extra={"error": str(e)})
        raise
    except Exception as e:
        logger.error("Unexpected error during Open Meteo fetch", extra={"error": str(e)})
        raise


