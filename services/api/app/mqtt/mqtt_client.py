import aiomqtt
import asyncio
import os
import json
from datetime import datetime, timezone
from app.database import AsyncSessionFactory
from app.crud.observation import create_observation
from schemas.observation_schemas import ObservationWrite


# ==========================
# CONFIGURATION
# ==========================
TOPICS = [
    "#",
    "tele/IoTorero_6057F8/SENSOR",
]

mqtt_username = os.getenv("MQTT_USERNAME")
mqtt_password = os.getenv("MQTT_PASSWORD")
mqtt_host = os.getenv("MQTT_HOST")
if not (mqtt_username and mqtt_password and mqtt_host):
    raise RuntimeError("Environment variables MQTT_USERNAME, MQTT_PASSWORD, and MQTT_HOST must be set")


# ==========================
# MESSAGE HANDLER
# ==========================
async def handle_message(message: aiomqtt.Message):
    """Process a single MQTT message — runs on the event loop, can await directly."""
    print(f"[MQTT] Topic: {message.topic}")
    print(f"[MQTT] Payload: {message.payload.decode()}")
    try:
        data = json.loads(message.payload.decode())
        # example payload:  {"Time":"2026-02-28T17:13:40","SHT4X":{"Temperature":23.3,"Humidity":29.8,"DewPoint":4.6},"TempUnit":"C"}
        result_time = datetime.fromisoformat(data["Time"]).replace(tzinfo=timezone.utc)
        temperature = data.get("SHT4X", {}).get("Temperature")
        humidity = data.get("SHT4X", {}).get("Humidity")

        async with AsyncSessionFactory() as db:
            if temperature is not None:
                obs = ObservationWrite(
                    datastream_id="REPLACE_WITH_TEMPERATURE_DATASTREAM_UUID",
                    result_time=result_time,
                    result_numeric=temperature,
                )
                result = await create_observation(db=db, observation_in=obs)
                print(f"[DB] Saved temperature observation: {result.id}")

            if humidity is not None:
                obs = ObservationWrite(
                    datastream_id="REPLACE_WITH_HUMIDITY_DATASTREAM_UUID",
                    result_time=result_time,
                    result_numeric=humidity,
                )
                result = await create_observation(db=db, observation_in=obs)
                print(f"[DB] Saved humidity observation: {result.id}")

    except json.JSONDecodeError:
        print("[MQTT] Failed to decode JSON payload")
    except Exception as e:
        print(f"[MQTT] Error processing message: {e}")


# ==========================
# MQTT LISTENER (async task)
# ==========================
_mqtt_task: asyncio.Task | None = None


async def _mqtt_listen():
    """Connect, subscribe, and listen for messages — runs as a background asyncio task."""
    while True:
        try:
            async with aiomqtt.Client(
                hostname=mqtt_host,
                port=1883,
                username=mqtt_username,
                password=mqtt_password,
            ) as client:
                print("[MQTT] Connected")
                for topic in TOPICS:
                    await client.subscribe(topic)
                    print(f"[MQTT] Subscribed to: {topic}")

                async for message in client.messages:
                    await handle_message(message)

        except aiomqtt.MqttError as e:
            print(f"[MQTT] Connection lost: {e}. Reconnecting in 5s...")
            await asyncio.sleep(5)
        except Exception as e:
            print(f"[MQTT] Unexpected error: {e}. Reconnecting in 5s...")
            await asyncio.sleep(5)


# ==========================
# STARTUP / SHUTDOWN HELPERS
# ==========================
def startup_mqtt():
    """Call during FastAPI lifespan startup. Launches the MQTT listener as a background task."""
    global _mqtt_task
    _mqtt_task = asyncio.create_task(_mqtt_listen())
    print("[MQTT] Listener task started")


def shutdown_mqtt():
    """Call during FastAPI lifespan shutdown. Cancels the MQTT listener task."""
    global _mqtt_task
    if _mqtt_task is not None:
        _mqtt_task.cancel()
        _mqtt_task = None
    print("[MQTT] Listener task stopped")

