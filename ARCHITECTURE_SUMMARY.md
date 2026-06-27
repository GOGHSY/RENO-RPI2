# Executive Summary — RENO-RPI2

## What This Is

**RENO-RPI2** is the embedded Python control application for **Raspberry Pi 2** at the **University of Nevada, Reno Water Treatment Plant**. It is one node in a two-Pi system. RPi2 handles all physical I/O: reading 9 Atlas Scientific EZO sensors and controlling 2 peristaltic chemical dosing pumps over I2C. RPi1 (the gateway node, code not present here) runs the Zenoh router, MQTT bridge, and remote dashboard.

---

## Architecture in One Diagram

```
RPi1 (Gateway)                        RPi2 (This codebase)
┌────────────────┐   Zenoh TCP VPN   ┌──────────────────────────────────┐
│  zenohd router │◄──────────────────│ main.py — 2-second control loop  │
│  MQTT bridge   │                   │  ├── sensors.py  (9 devices)      │
│  Dashboard     │──────────────────►│  ├── pumps.py   (dose logic)      │
└────────────────┘  alum pump cmds   │  ├── logger.py  (CSV)             │
                                     │  └── zenoh_client.py              │
                                     │              │                    │
                                     │         /dev/i2c-1                │
                                     │    Atlas Scientific EZO Bus       │
                                     │  pH×3  ORP  EC  RTD×4  Pump×2    │
                                     └──────────────────────────────────┘
```

---

## Execution Flow (Ponytail Method)

```
1. python3 main.py
2.   └─► device_config.py  → opens /dev/i2c-1, queries 9 Atlas EZO devices
3.   └─► zenoh_client.py   → TCP connect to RPi1 at 100.96.169.94:7447
4.   └─► run()
5.         ├─ new_log_file()   → creates /home/pi/.../{timestamp}.csv
6.         ├─ subscribe_alum_pump()  → Zenoh subscriber thread starts
7.         └─ while True (every 2 s):
8.               read pH1, pH2, pH3
9.               balance_pH()  → re-reads pH3; dispenses Lime if pH < 7.2
10.              read RTD×4, ORP, EC, Pump×2
11.              alum_pump_state()  → writes D,15/D,0 to Alum pump
12.              log_readings()     → append CSV row
13.              publish_full_readings()  → JSON via Zenoh to RPi1
14.              sleep(2)
15.
16. [async] _on_alum_pump()  → fires when RPi1 sends flow rate command
17.         writes DC,{ml_per_min},* or "x" to Alum pump
```

---

## Most Important Files for a New Developer

| Priority | File | Why |
|---|---|---|
| 1 | `main.py` | The heartbeat — all wiring and loop logic |
| 2 | `device_config.py` | Physical hardware map — which sensor is which address |
| 3 | `pumps.py` | The only non-trivial business logic (dosing decisions) |
| 4 | `zenoh_client.py` | The network — how RPi2 talks to RPi1 |
| 5 | `sensors.py` | Straightforward but important to understand the read pattern |
| 6 | `AtlasI2C.py` | Rarely needed; only relevant when debugging I2C issues |
| 7 | `wtp-rpi2.service` | Understand deployment — how the service runs on the Pi |

---

## Recommended Reading Order

1. `wtp-rpi2.service` — understand how it runs in production (30 seconds)
2. `device_config.py` — memorize the address-to-sensor map (2 minutes)
3. `main.py` — read top to bottom; the loop IS the system (5 minutes)
4. `pumps.py` — understand the lime dose curve and alum state logic (5 minutes)
5. `zenoh_client.py` — understand pub/sub topology and key expressions (3 minutes)
6. `sensors.py` + `logger.py` — skim; both are simple wrappers (2 minutes)
7. `AtlasI2C.py` — read only if I2C debugging is needed

---

## Top 10 Architectural Insights

1. **RPi2 is a dumb sensor node** — dosing logic lives here, but the commanding intelligence (flow-proportional alum dosing) lives on RPi1 and is received as Zenoh messages.

2. **All 9 hardware devices are module-level singletons** in `device_config.py` — imported by name everywhere. There is no device registry or discovery; addresses are all hard-coded literals.

3. **The main loop is blocking and sequential** — no async/await, no threading in the main path. A single slow I2C read stalls the entire cycle. With 11 sensor reads at 1.5 s each, the read phase alone takes ~16.5 s per cycle, making the 2-second `LOOP_DELAY` effectively irrelevant.

4. **Zenoh replaces MQTT** — the service file is named `wtp-rpi2.service` and the working directory is `MQTTsystem`, but the code uses Zenoh exclusively. This is a mid-flight protocol migration.

5. **The system degrades gracefully if RPi1 is unreachable** — Zenoh connection failure at startup sets `_session = None`, and all publish/subscribe calls no-op. Local sensing, dosing, and CSV logging continue unaffected.

6. **Pump 1 (Alum) has two competing control paths** — the Zenoh callback sets the flow rate commanded by RPi1 (flow-proportional), while `alum_pump_state()` in the main loop writes ON/OFF based on a local pH threshold every 2 seconds. These race and conflict (see TODO #1 and #3).

7. **pH3 is read twice per cycle** — once by `read_pH3()` (for the payload/log) and once inside `balance_pH()` (for the dose decision). The logged pH3 and the dose trigger pH3 may differ.

8. **The dose curve for Lime is a hard-coded three-band lookup** — 120/60/30 mL for pH < 6.5 / 6.5–7.1 / ≥ 7.1. There is no PID controller, no rate limiting, and no total-dose accumulator.

9. **The RPi1 Zenoh router address is a Tailscale VPN IP** (`100.96.169.94`) — both Pis must be enrolled in the same Tailscale network for any inter-Pi communication to work.

10. **There are no tests** — the only validation is running against live hardware. All sensor data arrives as raw strings; `float()` conversion happens ad-hoc at point of use without error handling.

---

## Surprising / Non-Obvious Implementation Details

- **`alum_pump_state()` has a side effect** — its name sounds like a read, but it actually **writes** a pump command on every call. This is a silent actuator action buried inside what looks like a status query.

- **`balance_pH()` sends negative volumes to the pump**: `device_Pump2.write(f"D,-{dose}")`. In Atlas EZO PMP protocol, a negative volume means "dispense continuously" — the pump runs until stopped with `"x"`. A positive `D,{vol}` dispenses a fixed volume then stops. The negative sign here makes the Lime pump run until the next loop iteration's dose decision.

- **`publish_readings()` (the old 4-arg version) is dead code** and lives alongside `publish_full_readings()` in the same file — the two functions do different things and the old one is never imported.

- **The loop delay is dominated by I2C reads, not `time.sleep(2)`** — reading 11 sensors at 1.5 s settling time each means each loop takes ~19 seconds minimum, regardless of the 2-second `LOOP_DELAY`.

- **The Zenoh key expression ends in `/010`** — this is likely a station or unit identifier. The naming convention for other stations isn't visible in this repo.
