import aiomqtt
import asyncio
import os
import json
from datetime import datetime
from zoneinfo import ZoneInfo
from app.database import AsyncSessionFactory
from app.crud.observation import create_observations_bulk, create_observation
from schemas.observation_schemas import ObservationWrite


# ==========================
# TOPIC HANDLERS
# ==========================
async def handle_sensor_sht4x(data: dict):
    """Handle SHT4X temperature/humidity sensor messages."""
    # example payload: {"Time":"2026-02-28T17:13:40","SHT4X":{"Temperature":23.3,"Humidity":29.8,"DewPoint":4.6},"TempUnit":"C"}
    result_time = datetime.fromisoformat(data["Time"]).replace(tzinfo=ZoneInfo("Europe/Athens"))
    temperature = data.get("SHT4X", {}).get("Temperature")
    humidity = data.get("SHT4X", {}).get("Humidity")
    dew_point = data.get("SHT4X", {}).get("DewPoint")

    observations = []

    if temperature is not None:
        observations.append(ObservationWrite(
            datastream_id="388a0b8f-f3ea-4f2b-9f0d-0a27dc44dce3",
            result_time=result_time,
            result_numeric=temperature,
        ))

    if humidity is not None:
        observations.append(ObservationWrite(
            datastream_id="35af36ae-4d57-416c-8354-c05457bcc6cc",
            result_time=result_time,
            result_numeric=humidity,
        ))

    if dew_point is not None:
        observations.append(ObservationWrite(
            datastream_id="5645b49f-32de-45d0-b4f2-5578b822ac86",
            result_time=result_time,
            result_numeric=dew_point,
        ))

    if observations:
        async with AsyncSessionFactory() as db:
            results = await create_observations_bulk(db=db, observations_in=observations)
            print(f"[DB] Saved {len(results)} observations in bulk")

async def handle_sensor_nous_a1t(data: dict):
    """Handle NOUS A1T consumption messages."""
    print(data)


# ==========================
# TOPIC → HANDLER MAPPING
# ==========================
TOPIC_HANDLERS = {
    "tele/IoTorero_6057F8/SENSOR": handle_sensor_sht4x,
    "tele/NOUS_A1T_4E4984/SENSOR": handle_sensor_nous_a1t,
    # "tele/other_device/SENSOR": handle_energy_meter,
}

# Subscribe to all topics that have a registered handler
TOPICS = list(TOPIC_HANDLERS.keys())

# ==========================
# CONFIGURATION
# ==========================
mqtt_username = os.getenv("MQTT_USERNAME")
mqtt_password = os.getenv("MQTT_PASSWORD")
mqtt_host = os.getenv("MQTT_HOST")
if not (mqtt_username and mqtt_password and mqtt_host):
    raise RuntimeError("Environment variables MQTT_USERNAME, MQTT_PASSWORD, and MQTT_HOST must be set")


# ==========================
# MESSAGE DISPATCHER
# ==========================
async def handle_message(message: aiomqtt.Message):
    """Dispatch message to the appropriate handler based on topic."""
    topic = str(message.topic)
    print(f"[MQTT] Topic: {topic}")
    print(f"[MQTT] Payload: {message.payload.decode()}")

    handler = TOPIC_HANDLERS.get(topic)
    if handler is None:
        print(f"[MQTT] No handler registered for topic: {topic}")
        return

    try:
        data = json.loads(message.payload.decode())
        await handler(data)
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

