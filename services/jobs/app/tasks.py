"""
Job tasks for Dramatiq worker
"""
import os
import time
import json
from typing import Any, Dict, Optional
import httpx
import redis.asyncio as aioredis
from datetime import datetime, timezone
import dramatiq
from logger.logging_config import logger
from app.broker import broker
from app.ml_models.prophet_model import train_and_cache_model

# Set broker as default
dramatiq.set_broker(broker)

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
_api_base = API_URL.split("/api/")[0] if "/api/" in API_URL else API_URL
API_TOKEN_URL = f"{_api_base}/auth/token"

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")


class TokenManager:
    """Caches and auto-refreshes an OAuth2 client credentials token."""

    def __init__(self) -> None:
        self._token: str = ""
        self._expires_at: float = 0.0
        self._refresh_buffer: int = 60

    def _is_valid(self) -> bool:
        return bool(self._token) and time.time() < self._expires_at - self._refresh_buffer

    def get_token(self) -> str:
        if not self._is_valid():
            self._fetch()
        return self._token

    def _fetch(self) -> None:
        with httpx.Client(timeout=30.0) as client:
            response = client.post(
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


@dramatiq.actor()
def sync_mqtt_topics_to_redis() -> None:
    """
    Fetch all SENSOR systems and their datastreams via the API.
    Builds mqtt:topic_config in Redis for MQTT handlers to use.
    """
    logger.info("Starting MQTT topic sync job")

    offset = 0
    total_topics = 0
    all_topic_config: Dict[str, str] = {}

    token = token_manager.get_token()
    auth_headers = {"Authorization": f"Bearer {token}"}

    with httpx.Client(timeout=30.0) as client:
        while True:
            try:
                logger.debug("Fetching systems from API", extra={"offset": offset, "limit": BATCH_SIZE})
                sys_response = client.get(
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

                valid_systems = [s for s in systems if s.get("external_id") and s.get("model")]

                if valid_systems:
                    system_ids = [s["id"] for s in valid_systems]
                    ds_response = client.get(
                        DATASTREAMS_API_URL,
                        params=[("system_ids", sid) for sid in system_ids],
                        headers=auth_headers,
                    )
                    ds_response.raise_for_status()
                    datastreams = ds_response.json()

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

    # Use sync redis connection for this simple operation
    import redis
    r = redis.from_url(REDIS_URL, decode_responses=True)
    
    if all_topic_config:
        current = r.hkeys(REDIS_TOPIC_CONFIG_KEY)
        stale = set(current) - set(all_topic_config.keys())
        if stale:
            logger.info("Removing stale topic configs", extra={"count": len(stale)})
            r.hdel(REDIS_TOPIC_CONFIG_KEY, *stale)

        r.hset(REDIS_TOPIC_CONFIG_KEY, mapping=all_topic_config)
        logger.info("MQTT topic config synced to Redis", extra={"total_topics": total_topics})
    else:
        logger.warning("No valid topics found — Redis not updated")
    
    r.close()


@dramatiq.actor(
    max_retries=10,
    min_backoff=5*60*1000,  # 5 minutes in milliseconds
    max_backoff=5*60*1000,  # No exponential backoff, always 5 min
)
def fetch_open_meteo_data(result_time: Optional[str] = None, is_retry: bool = False) -> None:
    """
    Fetch weather data from Open Meteo API and create observations.
    
    Uses Dramatiq's built-in retry mechanism: automatically retries up to 10 times
    with exactly 5 minutes between attempts, preserving the original result_time.
    
    On first run: result_time is captured from current UTC time, fetches current data
    On retries: result_time is preserved, fetches historical data at that timestamp
    """
    if result_time is None:
        result_time = datetime.now(timezone.utc).isoformat()
        is_retry = False
        logger.info(
            "Starting Open Meteo data fetch job",
            extra={"result_time": result_time}
        )
    else:
        is_retry = True
        logger.info(
            "Retrying Open Meteo data fetch (querying historical data)",
            extra={"result_time": result_time, "is_retry": is_retry}
        )
    
    token = token_manager.get_token()
    auth_headers = {"Authorization": f"Bearer {token}"}
    
    with httpx.Client(timeout=30.0) as client:
        # 1. Find the Open Meteo system
        logger.debug("Querying for Open Meteo system")
        sys_response = client.get(
            SYSTEMS_API_URL,
            params={"q": "Open Meteo", "limit": 10},
            headers=auth_headers,
        )
        sys_response.raise_for_status()
        systems = sys_response.json()
        
        if not systems:
            logger.error("Open Meteo system not found")
            return
        
        system = systems[0]
        system_id = system["id"]
        logger.info("Found Open Meteo system", extra={"system_id": system_id})
        
        # 2. Get datastreams for this system
        logger.debug("Fetching datastreams for system", extra={"system_id": system_id})
        ds_response = client.get(
            DATASTREAMS_API_URL,
            params={"system_id": system_id, "limit": 100},
            headers=auth_headers,
        )
        ds_response.raise_for_status()
        datastreams = ds_response.json()
        
        if not datastreams:
            logger.error("No datastreams found for Open Meteo system")
            return
        
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
        
        # 4. Fetch weather data from Open Meteo (current or historical)
        logger.debug(
            "Fetching Open Meteo data",
            extra={"latitude": OPEN_METEO_LATITUDE, "longitude": OPEN_METEO_LONGITUDE, "is_retry": is_retry}
        )
        
        params = {
            "latitude": OPEN_METEO_LATITUDE,
            "longitude": OPEN_METEO_LONGITUDE,
            "timezone": "auto"
        }
        
        if is_retry:
            # On retry, fetch historical data at the original result_time
            result_dt = datetime.fromisoformat(result_time.replace('Z', '+00:00'))
            date_str = result_dt.strftime("%Y-%m-%d")
            hour = result_dt.hour
            params["start_date"] = date_str
            params["end_date"] = date_str
            params["hourly"] = "temperature_2m,relative_humidity_2m,dew_point_2m"
            logger.debug("Querying historical data", extra={"date": date_str, "hour": hour})
        else:
            # On first run, fetch current data
            params["current"] = "temperature_2m,relative_humidity_2m,dew_point_2m"
        
        weather_response = client.get(
            OPEN_METEO_API_URL,
            params=params
        )
        weather_response.raise_for_status()
        weather_data = weather_response.json()
        
        # Extract data based on whether it's current or historical
        if is_retry:
            # Get hourly data at the specific hour
            result_dt = datetime.fromisoformat(result_time.replace('Z', '+00:00'))
            hour = result_dt.hour
            hourly = weather_data.get("hourly", {})
            times = hourly.get("time", [])
            temps = hourly.get("temperature_2m", [])
            humidities = hourly.get("relative_humidity_2m", [])
            dew_points = hourly.get("dew_point_2m", [])
            
            logger.debug(
                f"Hourly data: {len(times)} times, {len(temps)} temps. Target hour={hour}, "
                f"first_time={times[0] if times else 'none'}, last_time={times[-1] if times else 'none'}"
            )
            
            # Find the index for our hour - try progressively simpler matches
            hour_index = None
            
            if times:
                # Try 1: Find exact hour:00 format (what Open Meteo returns for hourly data)
                target_hour_str = result_dt.strftime("%Y-%m-%dT%H:00")
                try:
                    hour_index = times.index(target_hour_str)
                    logger.debug(f"Found exact hour match: {target_hour_str} at index {hour_index}")
                except ValueError:
                    logger.debug(f"No exact match for {target_hour_str}, trying index {hour} as fallback")
                    # Try 2: Use hour as direct index (if times are in chronological order starting 00:00)
                    if hour < len(times):
                        logger.debug(f"Using hour index {hour} as fallback, time value: {times[hour]}")
                        hour_index = hour
                    else:
                        logger.warning(f"Hour {hour} is out of range (only {len(times)} entries)")
            else:
                logger.warning(f"No times data in hourly response. Hourly keys: {list(hourly.keys())}")
            
            # Extract data if we found valid index
            if hour_index is not None and hour_index < len(temps):
                current = {
                    "temperature_2m": temps[hour_index] if hour_index < len(temps) else None,
                    "relative_humidity_2m": humidities[hour_index] if hour_index < len(humidities) else None,
                    "dew_point_2m": dew_points[hour_index] if hour_index < len(dew_points) else None,
                }
                logger.debug(f"Extracted hourly data at index {hour_index}: temp={current['temperature_2m']}")
            else:
                logger.warning(f"Could not extract hourly data: hour_index={hour_index}, temps_len={len(temps)}")
                current = {}
        else:
            current = weather_data.get("current", {})
        logger.info(
            "Fetched Open Meteo data",
            extra={
                "temperature": current.get("temperature_2m"),
                "humidity": current.get("relative_humidity_2m"),
                "dew_point": current.get("dew_point_2m"),
            }
        )
        
        # 5. Create observations for each datastream with preserved result_time
        observations_payload = []
        
        if "temperature" in ds_mapping and current.get("temperature_2m") is not None:
            observations_payload.append({
                "datastream_id": ds_mapping["temperature"]["id"],
                "result_time": result_time,
                "result_numeric": current["temperature_2m"]
            })
        
        if "humidity" in ds_mapping and current.get("relative_humidity_2m") is not None:
            observations_payload.append({
                "datastream_id": ds_mapping["humidity"]["id"],
                "result_time": result_time,
                "result_numeric": current["relative_humidity_2m"]
            })
        
        if "dew_point" in ds_mapping and current.get("dew_point_2m") is not None:
            observations_payload.append({
                "datastream_id": ds_mapping["dew_point"]["id"],
                "result_time": result_time,
                "result_numeric": current["dew_point_2m"]
            })
        
        if observations_payload:
            logger.debug("Creating observations in bulk", extra={"count": len(observations_payload)})
            obs_resp = client.post(
                f"{OBSERVATIONS_API_URL}bulk",
                json=observations_payload,
                headers=auth_headers,
            )
            obs_resp.raise_for_status()
            observations_created = len(observations_payload)
            logger.info(
                "Open Meteo data fetch job complete",
                extra={
                    "observations_created": observations_created,
                    "result_time": result_time,
                    "is_retry": is_retry,
                }
            )
        else:
            logger.warning("No observations to create")
            observations_created = 0
        
        logger.debug(
            "Open Meteo job finished",
            extra={
                "observations_created": observations_created,
                "system_id": system_id,
            }
        )


@dramatiq.actor()
def train_temperature_model(datastream_id: Optional[str] = None) -> None:
    """
    Train Prophet temperature model and cache in Redis.
    
    Fetches 30 days of historical data from the temperature datastream,
    trains a Prophet model, and caches it in Redis for use by the forecast API.
    
    Uses a distributed Redis lock to ensure only one worker executes this at a time.
    """
    datastream_id = datastream_id or os.getenv("OUTSIDE_TEMP_DATASTREAM_ID")
    RETRAIN_IN_PROGRESS_KEY = "model:retrain:in_progress"
    LOCK_KEY = "model:retrain:lock"
    LOCK_TIMEOUT = 600  # 10 minutes
    
    if not datastream_id:
        logger.error("No datastream_id configured")
        return
    
    import redis
    r = redis.from_url(REDIS_URL, decode_responses=True)
    
    # Try to acquire distributed lock
    lock_acquired = r.set(LOCK_KEY, "1", nx=True, ex=LOCK_TIMEOUT)
    
    if not lock_acquired:
        logger.warning(
            "Model training already in progress (locked by another worker), skipping",
            extra={"datastream_id": datastream_id}
        )
        r.close()
        return
    
    try:
        token = token_manager.get_token()
        
        logger.info("Starting temperature model training", extra={"datastream_id": datastream_id})
        
        # Note: train_and_cache_model is async but called from a sync actor context
        # We need to use a sync redis connection and run it synchronously
        import asyncio
        from app.ml_models.prophet_model import train_and_cache_model
        
        # Run async function in sync context
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            model_id = loop.run_until_complete(train_and_cache_model(
                datastream_id=datastream_id,
                token=token,
            ))
        finally:
            loop.close()
        
        logger.info(
            "Model training completed successfully",
            extra={"datastream_id": datastream_id, "model_id": model_id}
        )
        
    except Exception as e:
        logger.exception(
            "Model training failed",
            extra={"datastream_id": datastream_id, "error": str(e)}
        )
    finally:
        # Clear the in-progress flag and release the lock
        try:
            r.delete(RETRAIN_IN_PROGRESS_KEY)
            r.delete(LOCK_KEY)
            logger.info(
                "Cleared retrain in-progress flag and released lock",
                extra={"datastream_id": datastream_id}
            )
        except Exception as e:
            logger.warning(
                "Failed to clear retrain in-progress flag or release lock",
                extra={"datastream_id": datastream_id, "error": str(e)}
            )
        finally:
            r.close()
