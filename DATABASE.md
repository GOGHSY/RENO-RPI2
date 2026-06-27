# Data Storage — RENO-RPI2

There is no database. The system uses flat CSV files for local persistence.

---

## CSV Log Files

### Location

```
/home/pi/Raspberry-Pi-sample-code/logs/
```

### File Naming

```
{ISO-datetime}-UNRWaterTreatment.csv
```

Example: `2026-06-27 08:15:33.421032-UNRWaterTreatment.csv`

One file is created per process start (per `run()` call). The filename is not filesystem-safe on all platforms because it contains colons (`:`) from the datetime — this works on Linux but not on Windows/macOS.

### Schema

| Column | Source | Unit | Notes |
|---|---|---|---|
| `Date/Time` | `datetime.now()` | ISO string | Added automatically by `log_readings()` |
| `ORP` | `read_ORP()` | mV | Raw string from EZO |
| `pH1` | `read_pH1()` | pH units | Raw string |
| `RTD1` | `read_RTD1()` | °C | Raw string |
| `pH2` | `read_pH2()` | pH units | Raw string |
| `RTD2` | `read_RTD2()` | °C | Raw string |
| `pH3` | `read_pH3()` | pH units | Raw string |
| `RTD3` | `read_RTD3()` | °C | Raw string |
| `EC` | `read_EC()` | μS/cm | Raw string |
| `RTD4` | `read_RTD4()` | °C | Raw string |
| `Pump1` | `read_Pump1()` | mL/min | Pump flow-rate reading |
| `Pump2` | `read_Pump2()` | mL/min | Pump flow-rate reading |

### Sample Row

```
2026-06-27 08:15:35.112034,250.3,7.12,22.4,7.08,22.1,6.98,22.3,450.2,21.9,15.0,0.0
```

### Notes
- All values are stored as raw strings — no type coercion occurs at log time.
- Values prefixed with `"Error"` from a failed read will appear in the CSV if `_read()` fails to parse.
- No rotation, compression, or size limit is applied.
- The log directory (`/home/pi/Raspberry-Pi-sample-code/logs`) must exist before the service starts; `new_log_file()` does not create it.

---

## Zenoh (Ephemeral)

Zenoh is used for real-time data transport only — it provides no persistence. Each `session.put()` delivers the current reading JSON to RPi1; if RPi1 is unreachable, the message is dropped silently.

### Published Payload Schema

```json
{
  "ORP":         "250.3",
  "pH1":         "7.12",   "RTD1": "22.4",
  "pH2":         "7.08",   "RTD2": "22.1",
  "pH3":         "6.98",   "RTD3": "22.3",
  "EC":          "450.2",  "RTD4": "21.9",
  "Pump1":       "15.0",
  "Pump2":       "0.0",
  "temperature": "22.4",
  "pump1_state": "ON",
  "timestamp":   "2026-06-27 08:15:35.112034"
}
```

> `temperature` is an alias for `RTD1` (added for remote dashboard compatibility).  
> `pump1_state` is `"ON"` or `"OFF"` derived from the alum pump control logic.
