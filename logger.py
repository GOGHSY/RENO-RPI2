"""
logger.py
---------
CSV data-logging helpers for the UNR Water Treatment system.
"""

import os
from datetime import datetime

LOG_DIR     = "/home/pi/Raspberry-Pi-sample-code/logs"
LOG_HEADERS = [
    "Date/Time", "ORP",
    "pH1", "RTD1",
    "pH2", "RTD2",
    "pH3", "RTD3",
    "EC",  "RTD4",
    "Pump1", "Pump2",
]


def new_log_file() -> str:
    """Return a timestamped CSV file path and write the header row."""
    os.makedirs(LOG_DIR, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = f"{LOG_DIR}/{timestamp}-UNRWaterTreatment.csv"
    _write_line(path, LOG_HEADERS)
    return path


def log_readings(filename: str, readings: dict) -> None:
    """
    Append one row to the CSV.  `readings` must contain keys matching LOG_HEADERS
    (except 'Date/Time', which is added automatically).
    """
    timestamp = str(datetime.now())
    row = [
        timestamp,
        readings["ORP"],
        readings["pH1"],  readings["RTD1"],
        readings["pH2"],  readings["RTD2"],
        readings["pH3"],  readings["RTD3"],
        readings["EC"],   readings["RTD4"],
       readings["Pump1"], readings["Pump2"],
    ]
    _write_line(filename, row)


def _write_line(filename: str, line: list) -> None:
    with open(filename, "a") as f:
        f.write(",".join(str(x) for x in line) + "\n") 
