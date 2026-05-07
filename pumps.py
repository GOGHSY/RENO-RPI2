"""
pumps.py
--------
Pump control and chemical dosing logic for the UNR Water Treatment system.

  Pump 1 – Alum  (continuous duty, started at system startup)
  Pump 2 – Lime  (on-demand, triggered by post-sedimentation pH)
"""

import time
from device_config import device_pH3, device_Pump1, device_Pump2

READ_DELAY = 1.5  # seconds

ALUM_DUTY_CYCLE = 45   # % – continuous dispense rate at startup

def dispense_alum() -> None:
    """Start Pump 1 (Alum) at a fixed duty cycle."""
    print("Pump1 ON – continuous Alum dosing started")
    device_Pump1.write(f"DC,{ALUM_DUTY_CYCLE},*")


def stop_pumps() -> None:
    """Emergency / shutdown stop for both pumps."""
    device_Pump1.write("x")
    device_Pump2.write("x")
    print("All pumps stopped.")


def _get_lime_dose(pH3_value: float) -> int:
    """
    Return the lime dose volume (mL) based on post-sedimentation pH.
    Lower pH → larger correction dose.
    """
    if pH3_value < 6.5:
        return 120
    elif pH3_value < 7.1:
        return 60
    return 30


def balance_pH() -> None:
    """
    Read pH3 (post-sedimentation) and dispense Lime (Pump 2) if pH < 7.2.
    Called once per main loop iteration.
    """
    device_pH3.write("R")
    time.sleep(READ_DELAY)
    pH3_value = float(device_pH3.read().split(": ")[1].replace('\x00', '').strip())

    if pH3_value < 7.2:
        dose = _get_lime_dose(pH3_value)
        print(f"pH3 = {pH3_value:.2f} → dosing {dose} mL Lime")
        device_Pump2.write(f"D,-{dose}")
    else:
        print(f"pH3 = {pH3_value:.2f} → no Lime dose needed")


ALUM_TRIGGER_pH = 5.5   # pH threshold used in the MQTT loop

def alum_pump_state(pH_value: float) -> str:
    """
    Decide whether Pump 1 should be ON or OFF based on pH (MQTT mode).
    Returns 'ON' or 'OFF' and writes the appropriate command.
    """
    if pH_value > ALUM_TRIGGER_pH:
        device_Pump1.write("D,15")
        return "ON"
    else:
        device_Pump1.write("D,0")
        return "OFF"
