import aiomqtt
import asyncio
import os
import json
from datetime import datetime, timezone
from app.database import AsyncSessionFactory
from app.crud.observation import create_observations_bulk
from schemas.observation_schemas import ObservationWrite
import redis.asyncio as aioredis
from logger.logging_config import logger

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
REDIS_TOPIC_MODELS_KEY = "mqtt:topic_models"
TOPIC_REFRESH_INTERVAL = int(os.getenv("MQTT_TOPIC_REFRESH_INTERVAL", 60))  # seconds

# ==========================
# TOPIC HANDLERS
# ==========================
async def handle_sensor_SHT40(data: dict):
    """Handle SHT4X temperature/humidity sensor messages."""
    result_time = datetime.now(timezone.utc)
    temperature = data.get("SHT4X", {}).get("Temperature")
    humidity = data.get("SHT4X", {}).get("Humidity")
    dew_point = data.get("SHT4X", {}).get("DewPoint")

    observations = []

    if temperature is not None:
        observations.append(ObservationWrite(
            datastream_id="d84925e1-c18c-4605-90be-3e0079e868f5",
            result_time=result_time,
            result_numeric=temperature,
        ))
    if humidity is not None:
        observations.append(ObservationWrite(
            datastream_id="7a4f551d-9a76-444d-a732-9d136ce02f16",
            result_time=result_time,
            result_numeric=humidity,
        ))
    if dew_point is not None:
        observations.append(ObservationWrite(
            datastream_id="db8576c5-4a04-4b0c-bec2-7fa943ebf2c8",
            result_time=result_time,
            result_numeric=dew_point,
        ))

    if observations:
        async with AsyncSessionFactory() as db:
            results = await create_observations_bulk(db=db, observations_in=observations)
            logger.info("Saved observations from SHT40", extra={"count": len(results)})


async def handle_sensor_A1T(data: dict):
    """Handle NOUS A1T consumption messages."""
    logger.debug("Received NOUS A1T data", extra={"data": data})
    result_time = datetime.now(timezone.utc)
    active_power = data.get("ENERGY", {}).get("Power")
    voltage = data.get("ENERGY", {}).get("Voltage")
    energy_total = data.get("ENERGY", {}).get("Total")

    observations = []

    if active_power is not None:
        observations.append(ObservationWrite(
            datastream_id="08f166d2-398c-4ea2-959f-c146dc3406e1",
            result_time=result_time,
            result_numeric=active_power,
        ))
    if voltage is not None:
        observations.append(ObservationWrite(
            datastream_id="029d5008-b442-4679-a086-dbefeea5f686",
            result_time=result_time,
            result_numeric=voltage,
        ))
    if energy_total is not None:
        observations.append(ObservationWrite(
            datastream_id="207e9e00-404e-4c0d-8470-a8b114293e8d",
            result_time=result_time,
            result_numeric=energy_total,
        ))

    if observations:
        async with AsyncSessionFactory() as db:
            results = await create_observations_bulk(db=db, observations_in=observations)
            logger.info("Saved observations from A1T", extra={"count": len(results)})


# ==========================
# MODEL → HANDLER REGISTRY
# ==========================
MODEL_HANDLERS = {
    "SHT40": handle_sensor_SHT40,
    "A1T": handle_sensor_A1T,
}

# ==========================
# CONFIGURATION
# ==========================
mqtt_username = os.getenv("MQTT_USERNAME")
mqtt_password = os.getenv("MQTT_PASSWORD")
mqtt_host = os.getenv("MQTT_HOST")
if not (mqtt_username and mqtt_password and mqtt_host):
    raise RuntimeError("Environment variables MQTT_USERNAME, MQTT_PASSWORD, and MQTT_HOST must be set")


# ==========================
# DYNAMIC TOPIC HANDLERS
# ==========================
# Shared state — mutated by the refresh loop, read by the dispatcher
_topic_handlers: dict = {}
_topic_handlers_lock = asyncio.Lock()


async def _build_topic_handlers(redis) -> dict:
    """Pull topic→model mapping from Redis and resolve to handler functions."""
    topic_model_map = await redis.hgetall(REDIS_TOPIC_MODELS_KEY)
    handlers = {}
    for topic, model in topic_model_map.items():
        handler = MODEL_HANDLERS.get(model)
        if handler:
            handlers[topic] = handler
        else:
            logger.warning("No handler registered for model", extra={"model": model})
    return handlers


async def _topic_refresh_loop(client: aiomqtt.Client, redis):
    """
    Periodically pull topic→model from Redis, detect new/removed topics,
    subscribe/unsubscribe accordingly, and update the shared handler map.
    """
    global _topic_handlers

    while True:
        try:
            await asyncio.sleep(TOPIC_REFRESH_INTERVAL)

            fresh_handlers = await _build_topic_handlers(redis)

            async with _topic_handlers_lock:
                current_topics = set(_topic_handlers.keys())
                fresh_topics = set(fresh_handlers.keys())

                new_topics = fresh_topics - current_topics
                removed_topics = current_topics - fresh_topics

                for topic in new_topics:
                    await client.subscribe(topic)
                    logger.info("Subscribed to new MQTT topic", extra={"topic": topic})

                for topic in removed_topics:
                    await client.unsubscribe(topic)
                    logger.info("Unsubscribed from removed MQTT topic", extra={"topic": topic})

                _topic_handlers = fresh_handlers

        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error("Topic refresh error", extra={"error": str(e)})


# ==========================
# MESSAGE DISPATCHER
# ==========================
async def handle_message(message: aiomqtt.Message):
    """Dispatch message to the appropriate handler based on topic."""
    topic = str(message.topic)
    logger.debug("Received MQTT message", extra={"topic": topic})

    async with _topic_handlers_lock:
        handler = _topic_handlers.get(topic)

    if handler is None:
        logger.warning("No handler registered for topic", extra={"topic": topic})
        return

    try:
        data = json.loads(message.payload.decode())
        await handler(data)
    except json.JSONDecodeError:
        logger.error("Failed to decode JSON payload", extra={"topic": topic})
    except Exception as e:
        logger.error("Error processing message", extra={"topic": topic, "error": str(e)})


# ==========================
# MQTT LISTENER (async task)
# ==========================
_mqtt_task: asyncio.Task | None = None


async def _mqtt_listen():
    """Connect, subscribe to initial topics from Redis, and listen for messages."""
    global _topic_handlers

    redis = await aioredis.from_url(REDIS_URL, decode_responses=True)

    while True:
        try:
            async with aiomqtt.Client(
                hostname=mqtt_host,
                port=1883,
                username=mqtt_username,
                password=mqtt_password,
            ) as client:
                logger.info("Connected to MQTT broker")

                # Build initial topic→handler map from Redis
                async with _topic_handlers_lock:
                    _topic_handlers = await _build_topic_handlers(redis)

                # Subscribe to all initial topics
                for topic in _topic_handlers:
                    await client.subscribe(topic)
                    logger.info("Subscribed to topic", extra={"topic": topic})

                # Start the refresh loop as a background task
                refresh_task = asyncio.create_task(_topic_refresh_loop(client, redis))

                try:
                    async for message in client.messages:
                        await handle_message(message)
                finally:
                    refresh_task.cancel()
                    await asyncio.gather(refresh_task, return_exceptions=True)

        except aiomqtt.MqttError as e:
            logger.error("MQTT connection lost, reconnecting in 5s", extra={"error": str(e)})
            await asyncio.sleep(5)
        except Exception as e:
            logger.error("Unexpected MQTT error, reconnecting in 5s", extra={"error": str(e)})
            await asyncio.sleep(5)


# ==========================
# STARTUP / SHUTDOWN HELPERS
# ==========================
def startup_mqtt():
    global _mqtt_task
    _mqtt_task = asyncio.create_task(_mqtt_listen())
    logger.info("MQTT listener task started")


def shutdown_mqtt():
    global _mqtt_task
    if _mqtt_task is not None:
        _mqtt_task.cancel()
        _mqtt_task = None
        logger.info("MQTT listener task cancelled")
    logger.info("[MQTT] Listener task stopped")