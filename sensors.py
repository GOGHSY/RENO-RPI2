"""
sensors.py
----------
Read functions for every Atlas I2C sensor in the UNR Water Treatment system.
Each function sends a 'R' (read) command, waits for the measurement,
strips the response prefix, and returns the value as a clean string.
"""

import time
from device_config import (
    device_pH1, device_pH2, device_pH3,
    device_ORP, device_EC,
    device_RTD1, device_RTD2, device_RTD3, device_RTD4,
    device_Pump1, device_Pump2,
)
from pumps import pump1_lock

READ_DELAY = 1.5  # seconds – minimum settling time for Atlas EZO readings


def _read(device, label: str) -> str:
    """Generic read helper: write 'R', wait, parse, print, and return the value."""
    device.write("R")
    time.sleep(READ_DELAY)
    raw = device.read()
    if not raw.startswith("Success"):
        print(f"{label} ERROR: {raw}")
        return "ERROR"
    reading = raw.split(": ")[1].replace('\x00', '').strip()
    print(f"{label} = {reading}")
    return reading


# ── pH ───────────────────────────────────────────────────────────────��───────
def read_pH1()  -> str: return _read(device_pH1,  "pH1  (Pre Rapid Mix)")
def read_pH2()  -> str: return _read(device_pH2,  "pH2  (Post Floc)")
def read_pH3()  -> str: return _read(device_pH3,  "pH3  (Post Sed)")

# ── ORP ──────────────────────────────────────────────────────────────────────
def read_ORP()  -> str: return _read(device_ORP,  "ORP  (Pre Rapid Mix)")

# ── Conductivity ─────────────────────────────────────────────────────────────
def read_EC()   -> str: return _read(device_EC,   "EC   (Post Lime)")

# ── Temperature ──────────────────────────────────────────────────────────────
def read_RTD1() -> str: return _read(device_RTD1, "RTD1 (Pre Rapid Mix)")
def read_RTD2() -> str: return _read(device_RTD2, "RTD2 (Pre Rapid Mix)")
def read_RTD3() -> str: return _read(device_RTD3, "RTD3 (Post Floc)")
def read_RTD4() -> str: return _read(device_RTD4, "RTD4 (Effluent)")

# ── Pumps ─────────────────────────────────────────────────────────────────────
def read_Pump1() -> str:
    with pump1_lock:  # device_Pump1 is also written from the Zenoh command thread
        return _read(device_Pump1, "Alum Pump")
def read_Pump2() -> str: return _read(device_Pump2, "Lime Pump")
