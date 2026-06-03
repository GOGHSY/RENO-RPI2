import json
import time

from sensors import(
        read_pH1, read_pH2,read_pH3,
        read_ORP,read_EC,
        read_RTD1,read_RTD2,read_RTD3,read_RTD4,
        read_Pump1,read_Pump2,
        )
from pumps import dispense_alum,balance_pH,alum_pump_state,stop_pumps
from logger import new_log_file, log_readings
from zenoh_client import publish_full_readings as publish_data, subscribe_alum_pump
from device_config import device_Pump1


def _on_alum_pump(sample):
    try:
        data = json.loads(str(sample.payload))
        ml_per_min = float(data.get("ml_per_min", 0))
        if ml_per_min >= 0.5:
            device_Pump1.write(f"DC,{ml_per_min},*")
            print(f"Alum pump: DC,{ml_per_min},* mL/min")
        else:
            device_Pump1.write("x")
            print("Alum pump: stopped (flow too low)")
    except Exception as e:
        print(f"Alum pump command error: {e}")

LOOP_DELAY = 2

def run() -> None:
    log_file = new_log_file()

    # Subscribe to alum pump rate from RPI1 (flow-proportional dosing)
    _alum_sub = subscribe_alum_pump(_on_alum_pump)
    print("Subscribed to alum pump commands from RPI1")

    try:
        while True:
            pH1 = read_pH1()
            pH2 = read_pH2()
            pH3 = read_pH3()

            balance_pH()

            RTD1 = read_RTD1()
            RTD2 = read_RTD2()
            RTD3 = read_RTD3()
            RTD4 = read_RTD4()
            ORP  = read_ORP()
            EC   = read_EC()
            P1   = read_Pump1()
            P2   = read_Pump2()
 
            # ── Alum pump state for MQTT (pH1-based, non-destructive) ─────────
            pump1_state = alum_pump_state(float(pH1))
 
            # ── Build shared payload ──────────────────────────────────────────
            readings = {
                "ORP":   ORP,
                "pH1":   pH1,  "RTD1": RTD1,
                "pH2":   pH2,  "RTD2": RTD2,
                "pH3":   pH3,  "RTD3": RTD3,
                "EC":    EC,   "RTD4": RTD4,
                "Pump1": P1,
                "Pump2": P2,
                # MQTT extras
                "temperature": RTD1,   # primary temperature for remote dashboard
                "pump1_state": pump1_state,
            }
 
            # ── Log to CSV ────────────────────────────────────────────────────
            log_readings(log_file, readings)
 
            # ── Publish to MQTT ───────────────────────────────────────────────
            publish_data(readings)
 
            time.sleep(LOOP_DELAY)
 
    except KeyboardInterrupt:
        print("\nCtrl-C pressed – shutting down.")
        stop_pumps()
 
 
if __name__ == "__main__":
    run()

