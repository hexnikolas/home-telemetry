"""
Message handlers for different sensor types.

Each handler transforms raw message data from RabbitMQ into observation objects.
Handlers are registered by model type in MODEL_HANDLERS.

Message flow:
1. RabbitMQ receives message with routing key: "tele.NOUS_A1T_4E4984.SENSOR"
2. Worker converts routing key (dots→slashes): "tele/NOUS_A1T_4E4984/SENSOR"
3. Worker looks up model in Redis hash "mqtt:topic_models": "A1T"
4. Worker gets handler from MODEL_HANDLERS: handle_sensor_A1T()
5. Handler transforms data into ObservationWrite objects

Expected RabbitMQ message format (routing key with dots):
    routing_key: "tele.NOUS_A1T_4E4984.SENSOR" or "tele.IoTorero_6057F8.SENSOR"
    body: {
        "Time": "2026-03-26T11:51:17",
        "ENERGY": {
            "Power": 100.3,
            "Voltage": 34,
            ...
        }
    }

Redis setup (topic→model mapping with slashes):
    HSET mqtt:topic_models "tele/NOUS_A1T_4E4984/SENSOR" "A1T"
    HSET mqtt:topic_models "tele/IoTorero_6057F8/SENSOR" "SHT40"
"""
from typing import List, Dict, Any
from datetime import datetime, timezone
import pytz
from schemas.observation_schemas import ObservationWrite

# Timezone for incoming sensor data
CET = pytz.timezone('Europe/Paris')  # CET/CEST timezone

# ==========================
# TOPIC HANDLERS
# ==========================
async def handle_sensor_SHT40(data: dict) -> List[ObservationWrite]:
    """
    Handle SHT4X temperature/humidity sensor messages.
    
    Returns list of observations extracted from the message.
    """
    # Extract time from message, default to now if not present
    time_str = data.get("Time")
    if time_str:
        try:
            # Parse ISO format time string and localize to CET
            dt = datetime.fromisoformat(time_str)
            result_time = CET.localize(dt).astimezone(timezone.utc)
        except (ValueError, TypeError):
            result_time = datetime.now(timezone.utc)
    else:
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

    return observations


async def handle_sensor_A1T(data: dict) -> List[ObservationWrite]:
    """
    Handle NOUS A1T consumption messages.
    
    Returns list of observations extracted from the message.
    """
    # Extract time from message, default to now if not present
    time_str = data.get("Time")
    if time_str:
        try:
            # Parse ISO format time string and localize to CET
            dt = datetime.fromisoformat(time_str)
            result_time = CET.localize(dt).astimezone(timezone.utc)
        except (ValueError, TypeError):
            result_time = datetime.now(timezone.utc)
    else:
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

    return observations


# ==========================
# MODEL → HANDLER REGISTRY
# ==========================
MODEL_HANDLERS = {
    "SHT40": handle_sensor_SHT40,
    "A1T": handle_sensor_A1T,
}


def get_handler(model: str):
    """Get the handler function for a given model."""
    return MODEL_HANDLERS.get(model)
