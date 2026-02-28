import paho.mqtt.client as mqtt
import asyncio
import threading
import os
from app.crud.observation import create_observation

# ==========================
# DATABASE PERSISTENCE
# ==========================
_loop = None


# ==========================
# MQTT CALLBACKS
# ==========================
def on_connect(client, userdata, flags, rc):
    print(f"[MQTT] Connected with result code {rc}")
    for topic in TOPICS:
        client.subscribe(topic)
        print(f"[MQTT] Subscribed to topic: {topic}")


def on_message(client, userdata, msg):
    print(f"[MQTT] Received message from topic: {msg.topic}")
    print(f"[MQTT] Payload: {msg.payload.decode()}")

def on_disconnect(client, userdata, rc):
    print("[MQTT] Disconnected")


def on_subscribe(client, userdata, mid, granted_qos):
    print("[MQTT] Subscribed")


# ==========================
# TOPICS TO SUBSCRIBE
# ==========================
TOPICS = [
    # Add your MQTT topics here
    # "home/sensor/temperature",
    # "home/sensor/humidity",
    "#"
]


# ==========================
# MQTT CLIENT SETUP
# ==========================
mqtt_client = mqtt.Client()

# get credentials from env vars
mqtt_username = os.getenv("MQTT_USERNAME")
mqtt_password = os.getenv("MQTT_PASSWORD")
mqtt_host = os.getenv("MQTT_HOST")
if not (mqtt_username and mqtt_password and mqtt_host):
    raise RuntimeError("Environment variables MQTT_USERNAME, MQTT_PASSWORD, and MQTT_HOST must be set")
mqtt_client.username_pw_set(mqtt_username, mqtt_password)

mqtt_client.on_connect = on_connect
mqtt_client.on_message = on_message
mqtt_client.on_disconnect = on_disconnect
mqtt_client.on_subscribe = on_subscribe


# ==========================
# STARTUP / SHUTDOWN HELPERS
# ==========================
def startup_mqtt():
    """Call during FastAPI lifespan startup."""
    global _loop
    _loop = asyncio.get_running_loop()

    def connect():
        try:
            mqtt_client.connect(mqtt_host, 1883, 60)
            mqtt_client.loop_start()
            print("[MQTT] Connection started")
        except Exception as e:
            print(f"[MQTT] Failed to connect: {e}")

    threading.Thread(target=connect, daemon=True).start()


def shutdown_mqtt():
    """Call during FastAPI lifespan shutdown."""
    mqtt_client.loop_stop()
    mqtt_client.disconnect()
    print("[MQTT] Disconnected")

