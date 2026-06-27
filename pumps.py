"""
pumps.py
--------
Pump control and chemical dosing logic for the UNR Water Treatment system.

  Pump 1 – Alum  (flow rate commanded by RPi1 via Zenoh; falls back to pH threshold)
  Pump 2 – Lime  (on-demand, triggered by post-sedimentation pH)
"""

import threading
from device_config import device_Pump1, device_Pump2

# Shared lock — both the main loop and the Zenoh callback thread write to Pump 1.
pump1_lock = threading.Lock()

ALUM_TRIGGER_pH = 5.5   # pH threshold for local fallback control

LIME_DOSE_pH_THRESHOLD = 7.2   # dose Lime when pH3 falls below this


def stop_pumps() -> None:
    """Emergency / shutdown stop for both pumps."""
    with pump1_lock:
        device_Pump1.write("x")
    device_Pump2.write("x")
    print("All pumps stopped.")


def _get_lime_dose(pH3_value: float) -> int:
    """Return lime dose volume (mL) based on post-sedimentation pH — lower pH → larger dose."""
    if pH3_value < 6.5:
        return 120
    elif pH3_value < 7.1:
        return 60
    return 30


def balance_pH(pH3_value: float) -> None:
    """
    Dispense Lime (Pump 2) if pH3 < LIME_DOSE_pH_THRESHOLD.
    Accepts the already-read pH3 value so the sensor is not queried twice per cycle.
    """
    if pH3_value < LIME_DOSE_pH_THRESHOLD:
        dose = _get_lime_dose(pH3_value)
        print(f"pH3 = {pH3_value:.2f} → dosing {dose} mL Lime")
        device_Pump2.write(f"D,-{dose}")
    else:
        print(f"pH3 = {pH3_value:.2f} → no Lime dose needed")


def set_alum_pump_rate(ml_per_min: float) -> None:
    """
    Set Pump 1 (Alum) flow rate as commanded by RPi1.
    Thread-safe — may be called from the Zenoh subscriber thread.
    """
    with pump1_lock:
        if ml_per_min >= 0.5:
            device_Pump1.write(f"DC,{ml_per_min},*")
        else:
            device_Pump1.write("x")


def alum_pump_state(pH_value: float) -> str:
    """
    Local fallback: set Pump 1 ON/OFF based on pH threshold and return the state string.
    Only used when RPi1 has not sent a commanded rate this cycle.
    Thread-safe via pump1_lock.
    """
    with pump1_lock:
        if pH_value > ALUM_TRIGGER_pH:
            device_Pump1.write("D,15")
            return "ON"
        else:
            device_Pump1.write("D,0")
            return "OFF"
