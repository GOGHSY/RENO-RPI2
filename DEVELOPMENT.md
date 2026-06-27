# Development Guide — RENO-RPI2

---

## Prerequisites

### Hardware
- Raspberry Pi (any model with I2C, tested on RPi 2/3/4)
- Atlas Scientific EZO circuit boards connected to I2C bus 1
- Peristaltic pumps driven by Atlas EZO PMP or EZO-PMP modules
- Network connectivity to RPi1 (Tailscale VPN recommended)

### Software

```bash
# Enable I2C
sudo raspi-config
# Interface Options → I2C → Enable

# Install I2C tools (for diagnosis)
sudo apt-get install -y i2c-tools

# Install Zenoh Python binding
pip3 install eclipse-zenoh
```

---

## Build Process

There is no build step — this is pure Python 3. No compilation, no packaging.

---

## Running Locally

```bash
cd /home/pi/MQTTsystem
python3 main.py
```

Expected startup output:
```
Zenoh connected to router at tcp/100.96.169.94:7447
Subscribed to alum pump commands from RPI1
pH1  (Pre Rapid Mix) = 7.12
pH2  (Post Floc) = 7.08
pH3  (Post Sed) = 6.98
pH3 = 6.98 → dosing 30 mL Lime
...
Zenoh published: {ORP: ..., timestamp: ...}
```

---

## Testing

There is **no test suite** in this codebase. All verification is done manually against live hardware.

### Manual Verification Steps

**1. Scan the I2C bus**
```bash
i2cdetect -y 1
```
Expected addresses present: 96, 97, 98, 99, 100, 102, 104, 105, 106, 109, 110

**2. Test a single sensor without running the full loop**
```python
from AtlasI2C import AtlasI2C
dev = AtlasI2C()
dev.set_i2c_address(99)  # pH1
print(dev.query("R"))    # should print "Success ...: 7.xx"
```

**3. Test Zenoh connectivity**
```python
import zenoh, json
conf = zenoh.Config()
conf.insert_json5("connect/endpoints", '["tcp/100.96.169.94:7447"]')
s = zenoh.open(conf)
s.put("reno/water/test", json.dumps({"test": True}))
s.close()
```

**4. Test pump manually**
```python
from AtlasI2C import AtlasI2C
pump = AtlasI2C()
pump.set_i2c_address(110)  # Lime pump
pump.write("D,10")          # dispense 10 mL
import time; time.sleep(3)
pump.write("x")             # stop
```

---

## Debugging

### Service logs
```bash
sudo journalctl -u wtp-rpi2 -f
tail -f /home/pi/MQTTsystem/wtp-rpi2.log
```

### Common Failures

| Symptom | Likely Cause | Fix |
|---|---|---|
| `IOError: [Errno 121] Remote I/O error` | Wrong I2C address or device not connected | Run `i2cdetect -y 1` |
| `OSError: [Errno 2] No such file or directory: '/dev/i2c-1'` | I2C not enabled | `sudo raspi-config` → enable I2C |
| `Warning: Zenoh connection failed` | RPi1 unreachable / not running zenohd | Check Tailscale, check RPi1 service |
| `Error <device>: 2` | Atlas EZO still processing — read too soon | Increase `READ_DELAY` in sensors.py |
| `IndexError` in `_read()` | Sensor returned malformed response | Check for I2C noise; inspect raw with `AtlasI2C.read()` |
| CSV file not created | `LOG_DIR` does not exist | `mkdir -p /home/pi/Raspberry-Pi-sample-code/logs` |

### Checking sensor responses
Set `DEBUG = True` (manually, there's no flag) by temporarily uncommenting the `print(response)` line in `AtlasI2C.read()` (line 138).

---

## Development Workflow

1. **Edit on local machine** → `scp` or `rsync` to RPi2
2. **Run manually** to verify output: `python3 main.py`
3. **Restart service** after confirming: `sudo systemctl restart wtp-rpi2`

Suggested rsync one-liner:
```bash
rsync -avz --exclude='*.pyc' --exclude='__pycache__' \
  ./ pi@<rpi2-ip>:/home/pi/MQTTsystem/
```

---

## Coding Conventions (Inferred)

- **Module-level singletons** for hardware devices — no dependency injection.
- **Bare `print()`** for all logging — no logging framework.
- **Raw strings returned** from sensors — callers cast to `float()` when needed.
- **Fail-soft on network** — Zenoh failures are caught at connection time and silently skipped thereafter.
- **No type hints on most functions** — only `-> None` and `-> str` annotations exist.
- **Private helpers prefixed `_`** — e.g., `_read()`, `_init_device()`, `_get_lime_dose()`, `_write_line()`.

---

## Useful Commands

```bash
# Start / stop / restart service
sudo systemctl start wtp-rpi2
sudo systemctl stop wtp-rpi2
sudo systemctl restart wtp-rpi2

# Check service status
sudo systemctl status wtp-rpi2

# View all I2C devices
i2cdetect -y 1

# Kill and re-run manually (for debugging)
sudo systemctl stop wtp-rpi2
python3 /home/pi/MQTTsystem/main.py

# List CSV log files
ls -lh /home/pi/Raspberry-Pi-sample-code/logs/

# Tail latest CSV
ls -t /home/pi/Raspberry-Pi-sample-code/logs/*.csv | head -1 | xargs tail -f
```
