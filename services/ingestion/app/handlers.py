"""
Message handlers for different sensor types.

Each handler transforms raw message data from RabbitMQ into observation objects.
Handlers are registered by model type in MODEL_HANDLERS.

Message flow:
1. RabbitMQ receives message with routing key: "tele.NOUS_A1T_4E4984.SENSOR"
2. Worker converts routing key (dots→slashes): "tele/NOUS_A1T_4E4984/SENSOR"
3. Worker looks up topic config in Redis hash "mqtt:topic_config" (written by jobs sync)
4. Config contains: {"model": "A1T", "datastreams": {"Power": "uuid", ...}}
5. Worker gets handler from MODEL_HANDLERS: handle_sensor_A1T()
6. Handler receives the datastreams dict and maps payload fields → datastream IDs

Redis setup (via jobs sync job):
    HSET mqtt:topic_config "tele/NOUS_A1T_4E4984/SENSOR"
         '{"model": "A1T", "datastreams": {"Power": "uuid", "Voltage": "uuid", "Total": "uuid"}}'
"""
from typing import List, Dict
from datetime import datetime, timezone
import pytz
from schemas.observation_schemas import ObservationWrite

# Timezone for incoming sensor data
CET = pytz.timezone('Europe/Paris')  # CET/CEST timezone


def _parse_time(data: dict) -> datetime:
    """Parse 'Time' field from sensor payload and convert CET → UTC."""
    time_str = data.get("Time")
    if time_str:
        try:
            dt = datetime.fromisoformat(time_str)
            return CET.localize(dt).astimezone(timezone.utc)
        except (ValueError, TypeError):
            pass
    return datetime.now(timezone.utc)


# ==========================
# TOPIC HANDLERS
# ==========================
async def handle_sensor_SHT40(data: dict, datastreams: Dict[str, str]) -> List[ObservationWrite]:
    """
    Handle SHT4X temperature/humidity sensor messages.

    datastreams keys (set via properties.mqtt_key on each datastream):
        "Temperature", "Humidity", "DewPoint"
    """
    result_time = _parse_time(data)
    sht = data.get("SHT4X", {})

    readings = {
        "Temperature": sht.get("Temperature"),
        "Humidity":    sht.get("Humidity"),
        "DewPoint":    sht.get("DewPoint"),
    }

    observations = []
    for mqtt_key, value in readings.items():
        ds_id = datastreams.get(mqtt_key)
        if value is not None and ds_id:
            observations.append(ObservationWrite(
                datastream_id=ds_id,
                result_time=result_time,
                result_numeric=value,
            ))

    return observations


async def handle_sensor_A1T(data: dict, datastreams: Dict[str, str]) -> List[ObservationWrite]:
    """
    Handle NOUS A1T consumption messages.

    datastreams keys (set via properties.mqtt_key on each datastream):
        "Power", "Voltage", "Total"
    """
    result_time = _parse_time(data)
    energy = data.get("ENERGY", {})

    readings = {
        "Power":   energy.get("Power"),
        "Voltage": energy.get("Voltage"),
        "Total":   energy.get("Total"),
    }

    observations = []
    for mqtt_key, value in readings.items():
        ds_id = datastreams.get(mqtt_key)
        if value is not None and ds_id:
            observations.append(ObservationWrite(
                datastream_id=ds_id,
                result_time=result_time,
                result_numeric=value,
            ))

    return observations


# ==========================
# MODEL → HANDLER REGISTRY
# ==========================
MODEL_HANDLERS = {
    "SHT40": handle_sensor_SHT40,
    "A1T":   handle_sensor_A1T,
}


def get_handler(model: str):
    """Get the handler function for a given model."""
    return MODEL_HANDLERS.get(model)
