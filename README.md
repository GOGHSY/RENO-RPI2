# RENO-RPI2 — UNR Water Treatment Plant Sensor Node

Embedded Python application running on **Raspberry Pi 2 (RPi2)** at the University of Nevada, Reno (UNR) Water Treatment Plant (WTP). RPi2 is the sensor/actuator node: it reads Atlas Scientific EZO sensors over I2C, controls chemical dosing pumps, logs readings to CSV, and exchanges data with the upstream Raspberry Pi 1 (RPi1) via the Zenoh pub/sub protocol.

---

## Features

- Reads 9 Atlas Scientific EZO sensors per loop cycle:
  - 3× pH probes (pre rapid mix, post flocculation, post sedimentation)
  - 1× ORP (oxidation-reduction potential)
  - 1× EC (electrical conductivity / post lime dose)
  - 4× RTD temperature probes
- Controls 2 peristaltic dosing pumps:
  - **Pump 1** — Alum (coagulant); flow rate commanded by RPi1
  - **Pump 2** — Lime; dosed automatically when post-sedimentation pH < 7.2
- Publishes all readings to RPi1 via Zenoh over Tailscale VPN
- Subscribes to real-time alum pump commands from RPi1
- Logs every cycle to a timestamped CSV file
- Runs as a `systemd` service with automatic restart

---

## Tech Stack

| Layer | Technology |
|---|---|
| Language | Python 3 |
| Hardware bus | Linux I2C (`/dev/i2c-1`) |
| Sensors/pumps | Atlas Scientific EZO modules |
| Messaging | Zenoh (pub/sub) |
| Network | Tailscale VPN (100.96.x.x) |
| Persistence | CSV flat files |
| Process manager | systemd |
| Platform | Raspberry Pi (Linux, ARM) |

---

## Project Structure

```
RENO-RPI2/
├── main.py            # Entry point — main control loop
├── device_config.py   # I2C device initialization (all addresses)
├── sensors.py         # Per-sensor read functions
├── pumps.py           # Chemical dosing logic
├── zenoh_client.py    # Zenoh pub/sub connection
├── logger.py          # CSV logging helpers
├── AtlasI2C.py        # Low-level Atlas I2C driver
└── wtp-rpi2.service   # systemd unit file
```

---

## Environment / Configuration

All configuration is hard-coded in source files (no `.env` file). Deployable values to change before installation:

| File | Value | Default | Description |
|---|---|---|---|
| `zenoh_client.py` | `RPI1_ROUTER` | `tcp/100.96.169.94:7447` | Tailscale IP:port of RPi1 Zenoh router |
| `zenoh_client.py` | `KEY_EXPR` | `reno/water/treatment/010` | Zenoh key expression for sensor data |
| `logger.py` | `LOG_DIR` | `/home/pi/Raspberry-Pi-sample-code/logs` | CSV output directory |
| `wtp-rpi2.service` | `WorkingDirectory` | `/home/pi/MQTTsystem` | Service working directory |
| `main.py` | `LOOP_DELAY` | `2` (seconds) | Sleep between readings |
| `sensors.py` | `READ_DELAY` | `1.5` (seconds) | Atlas EZO settling time |
| `pumps.py` | `ALUM_DUTY_CYCLE` | `45` (%) | Unused startup duty cycle constant |
| `pumps.py` | `ALUM_TRIGGER_pH` | `5.5` | pH threshold for alum pump state |

---

## Installation

### Prerequisites

```bash
sudo apt-get install python3-pip i2c-tools
pip3 install zenoh
# Enable I2C: raspi-config → Interface Options → I2C → Enable
```

### Deploy as systemd Service

```bash
sudo cp wtp-rpi2.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable wtp-rpi2
sudo systemctl start wtp-rpi2
```

### Running Locally

```bash
cd /home/pi/MQTTsystem
python3 main.py
```

> **Note:** The service `WorkingDirectory` is `/home/pi/MQTTsystem` but the log path in `logger.py` uses `/home/pi/Raspberry-Pi-sample-code/logs`. Ensure both directories exist.

---

## Running / Logs

```bash
# Check service status
sudo systemctl status wtp-rpi2

# Follow live logs
tail -f /home/pi/MQTTsystem/wtp-rpi2.log

# List CSV logs
ls /home/pi/Raspberry-Pi-sample-code/logs/
```

---

## Quick Start (New Developer)

1. Read `device_config.py` — understand which sensor sits at which I2C address.
2. Read `main.py` — the 2-second loop is the heartbeat of the entire system.
3. Read `pumps.py` — the dosing logic is the only non-trivial business logic.
4. Read `zenoh_client.py` — understand the two-node communication topology.
5. Refer to `AtlasI2C.py` only if I2C communication itself is misbehaving.
