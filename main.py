import json
import time

from sensors import (
    read_pH1, read_pH2, read_pH3,
    read_ORP, read_EC,
    read_RTD1, read_RTD2, read_RTD3, read_RTD4,
    read_Pump1, read_Pump2,
)
from pumps import balance_pH, alum_pump_state, set_alum_pump_rate, stop_pumps
from logger import new_log_file, log_readings
from zenoh_client import publish_full_readings as publish_data, subscribe_alum_pump

LOOP_DELAY = 2


def _on_alum_pump(sample):
    """Zenoh callback: receives flow-rate commands from RPi1 (runs on Zenoh thread)."""
    try:
        data = json.loads(str(sample.payload))
        ml_per_min = float(data.get("ml_per_min", 0))
        set_alum_pump_rate(ml_per_min)
        print(f"Alum pump: RPi1 commanded {ml_per_min:.2f} mL/min")
    except Exception as e:
        print(f"Alum pump command error: {e}")


def run() -> None:
    log_file = new_log_file()

    _alum_sub = subscribe_alum_pump(_on_alum_pump)
    print("Subscribed to alum pump commands from RPI1")

    try:
        while True:
            pH1 = read_pH1()
            pH2 = read_pH2()
            pH3 = read_pH3()

            # Pass the already-read pH3 value — avoids a redundant I2C read
            balance_pH(float(pH3))

            RTD1 = read_RTD1()
            RTD2 = read_RTD2()
            RTD3 = read_RTD3()
            RTD4 = read_RTD4()
            ORP  = read_ORP()
            EC   = read_EC()
            P1   = read_Pump1()
            P2   = read_Pump2()

            # Local fallback pump state (also writes to pump if RPi1 hasn't commanded)
            pump1_state = alum_pump_state(float(pH1))

            readings = {
                "ORP":   ORP,
                "pH1":   pH1,  "RTD1": RTD1,
                "pH2":   pH2,  "RTD2": RTD2,
                "pH3":   pH3,  "RTD3": RTD3,
                "EC":    EC,   "RTD4": RTD4,
                "Pump1": P1,
                "Pump2": P2,
                "temperature": RTD1,   # alias for remote dashboard
                "pump1_state": pump1_state,
            }

            log_readings(log_file, readings)
            publish_data(readings)

            time.sleep(LOOP_DELAY)

    except KeyboardInterrupt:
        print("\nCtrl-C pressed – shutting down.")
        stop_pumps()


if __name__ == "__main__":
    run()

