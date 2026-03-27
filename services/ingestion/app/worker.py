"""
Standalone observations ingestion worker

Consumes MQTT messages from RabbitMQ queue, processes them through handlers,
and sends observations in bulk to the API.

Usage:
    python -m app.worker
"""
import asyncio
import sys
import os
import json
import httpx
import redis.asyncio as aioredis
from typing import List, Dict, Any
from datetime import datetime
from shared.logger.logging_config import setup_logging_json, setup_logging_colored
from schemas.observation_schemas import ObservationWrite
from app.queue import ObservationQueue
from app.handlers import get_handler, MODEL_HANDLERS

# Configuration
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FORMAT = os.getenv("LOG_FORMAT", "json").lower()
API_BASE_URL = os.getenv("API_BASE_URL")
OBSERVATIONS_BULK_ENDPOINT = f"{API_BASE_URL}/observations/bulk"
REQUEST_TIMEOUT = int(os.getenv("REQUEST_TIMEOUT", "30"))
REDIS_URL = os.getenv("REDIS_URL")
REDIS_TOPIC_MODELS_KEY = "mqtt:topic_models"
AUTO_ACK = os.getenv("AUTO_ACK", "false").lower() == "true"
MAX_RETRIES = int(os.getenv("API_MAX_RETRIES", "5"))
BASE_DELAY = int(os.getenv("BASE_DELAY", "5"))
API_CLIENT_ID = os.getenv("API_CLIENT_ID", "ingestion-worker")
API_CLIENT_SECRET = os.getenv("API_CLIENT_SECRET", "")
# Derive base host URL: strip /api/v1 suffix so token URL points to the right place
# e.g. http://home-telemetry-api:8000/api/v1 → http://home-telemetry-api:8000/auth/token
_api_host = API_BASE_URL.split("/api/")[0] if API_BASE_URL and "/api/" in API_BASE_URL else (API_BASE_URL or "")
API_TOKEN_URL = f"{_api_host}/auth/token"

# Initialize logging
if LOG_FORMAT == "colored":
    logger = setup_logging_colored("home-telemetry-ingestion-worker", level=LOG_LEVEL)
else:
    logger = setup_logging_json("home-telemetry-ingestion-worker", level=LOG_LEVEL)

# ---------------------------------------------------------------------------
# Token manager — fetches a JWT on startup and refreshes before expiry
# ---------------------------------------------------------------------------
class TokenManager:
    def __init__(self) -> None:
        self._token: str = ""
        self._expires_at: float = 0.0  # Unix timestamp
        self._refresh_buffer: int = 60  # refresh this many seconds before expiry

    def _is_valid(self) -> bool:
        import time
        return bool(self._token) and time.time() < self._expires_at - self._refresh_buffer

    async def get_token(self) -> str:
        if not self._is_valid():
            await self._fetch()
        return self._token

    async def _fetch(self) -> None:
        import time
        if not API_CLIENT_SECRET:
            raise RuntimeError("API_CLIENT_SECRET is not set — cannot authenticate with the API")
        logger.info(f"Fetching auth token for client '{API_CLIENT_ID}'")
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(
                API_TOKEN_URL,
                data={
                    "grant_type": "client_credentials",
                    "client_id": API_CLIENT_ID,
                    "client_secret": API_CLIENT_SECRET,
                },
            )
            resp.raise_for_status()
            body = resp.json()
            self._token = body["access_token"]
            expires_in = int(body.get("expires_in", 900))
            self._expires_at = time.time() + expires_in
            logger.info(f"Auth token acquired (expires in {expires_in}s)")


# Global instances
observation_queue = ObservationQueue(auto_ack=AUTO_ACK)
redis_client: aioredis.Redis = None
topic_model_map: dict = {}  # Cache of topic→model mappings from Redis
token_manager = TokenManager()


def _get_model_for_topic(routing_key: str) -> str:
    """
    Convert RabbitMQ routing key (with dots) to MQTT topic (with slashes),
    then look up model in Redis cache.
    
    Example: "tele.NOUS_A1T_4E4984.SENSOR" → "tele/NOUS_A1T_4E4984/SENSOR" → "A1T"
    """
    mqtt_topic = routing_key.replace(".", "/")
    model = topic_model_map.get(mqtt_topic)
    if model:
        logger.debug(f"Matched routing_key '{routing_key}' → mqtt_topic '{mqtt_topic}' → model '{model}'")
    else:
        logger.warning(f"No model found for topic: {mqtt_topic}")
    return model


async def process_messages(messages: List[Dict[str, Any]]):
    """
    Process raw messages from queue through handler and send observations to API.
    
    For each message:
    1. Get the routing key (topic)
    2. Convert dots to slashes and look up model in Redis cache
    3. Get the appropriate handler from MODEL_HANDLERS
    4. Call handler to generate observations
    """
    observations = []

    for message in messages:
        try:
            # DEBUG: Print raw message from queue
            logger.debug(f"\n{'='*60}")
            logger.debug(f"RAW MESSAGE FROM QUEUE:")
            logger.debug(f"{'='*60}")
            logger.debug(f"Full message: {json.dumps(message, indent=2, default=str)}")
            
            routing_key = message.get("topic")
            data_payload = message
            # Remove topic from data since it's metadata, not sensor data
            if "topic" in data_payload:
                data_payload = {k: v for k, v in data_payload.items() if k != "topic"}
            
            logger.debug(f"Routing Key: {routing_key}")
            logger.debug(f"Data: {json.dumps(data_payload, indent=2, default=str)}")

            if not data_payload:
                logger.warning(f"Message has no data: {message}")
                logger.info(f"{'='*60}\n")
                continue

            # Determine model from routing key
            model = _get_model_for_topic(routing_key)
            if not model:
                logger.warning(f"No handler for topic: {routing_key}")
                logger.info(f"{'='*60}\n")
                continue

            # Get handler for this model
            handler = MODEL_HANDLERS.get(model)
            if not handler:
                logger.error(f"Handler not found for model: {model}")
                logger.info(f"{'='*60}\n")
                continue

            logger.debug(f"Model: {model}")
            logger.debug(f"Handler: {handler.__name__}")
            logger.debug(f"{'='*60}\n")

            logger.debug(f"Processing message from {routing_key} with {model} handler")

            # Call handler to get observations
            obs = await handler(data_payload)
            observations.extend(obs)
            logger.debug(f"Handler {model} generated {len(obs)} observations")

        except Exception as e:
            logger.error(f"Error processing message: {e}", extra={"message": message})
            logger.info(f"{'='*60}\n")
            continue

    # Send all observations in bulk (if any were generated)
    if observations:
        success = await send_observations_to_api(observations)
    else:
        # No observations generated, but messages were still processed
        success = True
        logger.info("No observations generated from batch")

    # Acknowledge all messages after processing, regardless of observation count
    if success:
        await observation_queue.ack_batch()
        logger.info("Batch processed successfully - messages acknowledged and removed from queue")
    else:
        # NACK messages to requeue them for retry
        await observation_queue.nack_batch(requeue=True)
        logger.warning("API request failed - messages NACKed and requeued for retry")


async def send_observations_to_api(observations: List[ObservationWrite]):
    """
    Send observations in bulk to the API with exponential backoff retry.
    
    Returns True if successful (201), False otherwise.
    """
    if not observations:
        return True  # No observations to send is considered success
    
    for attempt in range(MAX_RETRIES):
        try:
            logger.info(f"Sending batch of {len(observations)} observations to API (attempt {attempt + 1}/{MAX_RETRIES})")

            # Convert to dicts for JSON serialization (mode='json' ensures UUIDs are converted to strings)
            obs_dicts = [obs.model_dump(mode='json') for obs in observations]

            token = await token_manager.get_token()
            async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
                logger.debug(f"POST {OBSERVATIONS_BULK_ENDPOINT}")
                response = await client.post(
                    OBSERVATIONS_BULK_ENDPOINT,
                    json=obs_dicts,
                    headers={"Authorization": f"Bearer {token}"},
                )
                response.raise_for_status()

                # Check for 201 Created response
                if response.status_code == 201:
                    logger.info(f" Successfully ingested {len(observations)} observations")
                    return True
                else:
                    logger.warning(f"✗ API returned {response.status_code} instead of 201")
                    return False

        except httpx.TimeoutException as e:
            if attempt < MAX_RETRIES - 1:
                delay = BASE_DELAY * (2 ** attempt)
                logger.warning(f"✗ Request timeout - retrying in {delay}s (attempt {attempt + 1}/{MAX_RETRIES})")
                await asyncio.sleep(delay)
            else:
                logger.error(f"✗ Request timeout after {MAX_RETRIES} attempts")
                return False
        except httpx.HTTPStatusError as e:
            if attempt < MAX_RETRIES - 1:
                delay = BASE_DELAY * (2 ** attempt)
                logger.warning(f"✗ API returned error {e.response.status_code} - retrying in {delay}s (attempt {attempt + 1}/{MAX_RETRIES})")
                await asyncio.sleep(delay)
            else:
                logger.error(f"✗ API returned error {e.response.status_code}: {e.response.text}")
                return False
        except Exception as e:
            if attempt < MAX_RETRIES - 1:
                delay = BASE_DELAY * (2 ** attempt)
                logger.warning(f"✗ Failed to send observations - retrying in {delay}s (attempt {attempt + 1}/{MAX_RETRIES}): {e}")
                await asyncio.sleep(delay)
            else:
                logger.error(f"✗ Failed to send observations after {MAX_RETRIES} attempts: {e}")
                return False
    
    return False


async def main():
    """Main worker entry point"""
    global redis_client, topic_model_map

    logger.info("=" * 60)
    logger.info("Starting Observations Ingestion Worker")
    logger.info("=" * 60)
    logger.info(f"API URL: {API_BASE_URL}")
    logger.info(f"Observations Endpoint: {OBSERVATIONS_BULK_ENDPOINT}")
    logger.info(f"Redis URL: {REDIS_URL}")
    logger.info(f"Auto-Ack: {AUTO_ACK} (if False, messages stay in queue)")
    logger.info(f"Batch Size: {int(os.getenv('BATCH_SIZE', '100'))}")
    logger.info(f"Batch Timeout: {int(os.getenv('BATCH_TIMEOUT', '5'))} seconds")
    logger.info("=" * 60)

    try:
        # Connect to Redis
        logger.info("Connecting to Redis...")
        redis_client = await aioredis.from_url(REDIS_URL, decode_responses=True)
        logger.info(" Connected to Redis")

        # Fetch initial auth token (fails fast if credentials are wrong)
        logger.info("Fetching API auth token...")
        await token_manager.get_token()
        logger.info("API auth token ready")

        # Load topic→model mappings from Redis
        logger.info(f"Loading topic→model mappings from Redis (key: {REDIS_TOPIC_MODELS_KEY})...")
        topic_model_map = await redis_client.hgetall(REDIS_TOPIC_MODELS_KEY)
        logger.info(f"Loaded {len(topic_model_map)} topic mappings:")
        for mqtt_topic, model in topic_model_map.items():
            logger.info(f"  {mqtt_topic} → {model}")

        # Connect to RabbitMQ
        logger.info("Connecting to RabbitMQ...")
        await observation_queue.connect()
        logger.info("Connected to RabbitMQ")

        # Register message processor
        observation_queue.register_handler(process_messages)
        logger.info("Registered message processor")

        logger.info("Starting message consumption...")
        logger.info("Waiting for messages...")
        
        # Start consuming messages (blocks indefinitely)
        await observation_queue.start_consuming()

    except KeyboardInterrupt:
        logger.info("Shutdown signal received (KeyboardInterrupt)")
    except Exception as e:
        logger.error(f"Fatal error in worker: {e}")
        sys.exit(1)
    finally:
        # Cleanup
        try:
            await observation_queue.disconnect()
            logger.info("Disconnected from RabbitMQ")
        except Exception as e:
            logger.error(f"Error disconnecting from RabbitMQ: {e}")

        if redis_client:
            try:
                await redis_client.close()
                logger.info("Disconnected from Redis")
            except Exception as e:
                logger.error(f"Error disconnecting from Redis: {e}")

        logger.info("Worker cleanup complete")


if __name__ == "__main__":
    asyncio.run(main())
