"""
mqtt_client.py
--------------
MQTT connection and publish helpers for the UNR Water Treatment system.
Uses the HiveMQ public broker by default; swap broker/port via constants.
"""

import json
from datetime import datetime
import paho.mqtt.client as mqtt

# ── Broker settings ───────────────────────────────────────────────────────────
BROKER   = "100.96.169.94"
PORT     = 1883
KEEPALIVE = 60

# ── Topics ────────────────────────────────────────────────────────────────────
TOPIC_ALL = "reno/water/treatment/010"

# ── Client setup ──────────────────────────────────────────────────────────────
_client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
#_client.connect(BROKER, PORT, KEEPALIVE)
try:
    _client.connect(BROKER, PORT, KEEPALIVE)
    _client.loop_start()
    print("MQTT connected successfully")
except Exception as e:
    print(f"Warning: MQTT connection failed: {e}")


def publish_readings(pH: float, orp: float, temperature: float, pump1: str) -> None:
    """Serialize sensor readings to JSON and publish to TOPIC_ALL."""
    data = {
        "timestamp":   str(datetime.now()),
        "ph":          pH,
        "orp":         orp,
        "temperature": temperature,
        "pump1":       pump1,
    }
    _client.publish(TOPIC_ALL, json.dumps(data))
    print("MQTT published:", data)


def publish_full_readings(payload: dict) -> None:
    """
    Publish an arbitrary dict of readings (used by the full treatment loop).
    Keys should match the CSV log headers for consistency.
    """
    payload["timestamp"] = str(datetime.now())
    _client.publish(TOPIC_ALL, json.dumps(payload))
    print("MQTT published:", payload)
