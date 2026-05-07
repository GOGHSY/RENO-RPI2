"""
zenoh_client.py
---------------
Zenoh connection and publish helpers for the UNR Water Treatment system.
"""

import json
from datetime import datetime
import zenoh

# ── Zenoh config ──────────────────────────────────────────────────────────────
KEY_EXPR    = "reno/water/treatment/010"
RPI1_ROUTER = "tcp/100.96.169.94:7447"   # zenohd running on RPi1

# ── Session setup ─────────────────────────────────────────────────────────────
_session = None
try:
    conf = zenoh.Config()
    conf.insert_json5("connect/endpoints", f'["{RPI1_ROUTER}"]')
    _session = zenoh.open(conf)
    print(f"Zenoh connected to router at {RPI1_ROUTER}")
except Exception as e:
    print(f"Warning: Zenoh connection failed: {e}")
    _session = None


def publish_readings(pH: float, orp: float, temperature: float, pump1: str) -> None:
    """Serialize sensor readings to JSON and publish via Zenoh."""
    if _session is None:
        return

    data = {
        "timestmp":   str(datetime.now()),
        "ph":          pH,
        "orp":         orp,
        "temperature": temperature,
        "pump1":       pump1,
    }

    _session.put(KEY_EXPR, json.dumps(data))
    print("Zenoh published:", data)


def publish_full_readings(payload: dict) -> None:
    """Publish arbitrary dict via Zenoh."""
    if _session is None:
        return

    payload["timestamp"] = str(datetime.now())
    _session.put(KEY_EXPR, json.dumps(payload))
    print("Zenoh published:", payload)
