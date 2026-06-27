# Components — RENO-RPI2

---

## `AtlasI2C` (`AtlasI2C.py`)

### Purpose
Low-level I2C driver for Atlas Scientific EZO circuit boards. Adapted from Atlas's official Raspberry Pi sample code. Handles all byte-level communication with the Linux I2C subsystem.

### Responsibilities
- Opens `/dev/i2c-{bus}` (default bus 1) for binary read/write
- Sets the active I2C slave address using `ioctl(I2C_SLAVE, addr)`
- Sends ASCII command strings with a null terminator
- Reads 31-byte responses and strips the Atlas EZO status prefix byte
- Applies a Raspberry Pi–specific MSB-clearing glitch workaround on all response bytes

### Key Constants

| Constant | Value | Meaning |
|---|---|---|
| `LONG_TIMEOUT` | 1.5 s | Wait time for `R` (read) and `CAL` commands |
| `SHORT_TIMEOUT` | 0.3 s | Wait time for all other commands |
| `DEFAULT_BUS` | 1 | I2C bus number |
| `DEFAULT_ADDRESS` | 98 | Fallback I2C address |
| `LONG_TIMEOUT_COMMANDS` | `("R", "CAL")` | Commands requiring long wait |
| `SLEEP_COMMANDS` | `("SLEEP",)` | Commands that put chip to sleep (no response) |

### Public Interface

```python
class AtlasI2C:
    def __init__(address=None, moduletype="", name="", bus=None)
    def set_i2c_address(addr: int) -> None
    def write(cmd: str) -> None          # sends cmd + null byte
    def read(num_of_bytes=31) -> str     # returns "Success <info>: <value>" or "Error <info>: <code>"
    def query(command: str) -> str       # write + timed wait + read
    def close() -> None
    def list_i2c_devices() -> list[int]  # scans all 128 addresses
    # properties: long_timeout, short_timeout, name, address, moduletype
```

### Response Format
`read()` returns a formatted string:
- Success: `"Success <moduletype> <address> <name>: <measurement>"`
- Error:   `"Error <moduletype> <address> <name>: <error_code>"`

Callers (in `sensors.py`) split on `": "` to extract just the measurement value.

### Notes
- The MSB-clearing glitch workaround is applied to bytes `[1:]` — the first byte is the status code (must be `1` for success).
- The `SLEEP` command returns no response; `query()` returns the string `"sleep mode"` instead.
- File handles are kept open for the lifetime of the object — `close()` must be called explicitly or the handles leak.

---

## `device_config` (`device_config.py`)

### Purpose
Single point of truth for all I2C device addresses. Creates and exports one `AtlasI2C` object per physical device at module import time.

### Responsibilities
- Maps human-readable sensor names to I2C addresses
- Queries each device for its module type (`I` command) and name (`name,?`) during initialization
- Exports singleton device objects consumed by `sensors.py` and `pumps.py`

### Device Map

| Export | Address | Sensor Type | Location |
|---|---|---|---|
| `device_pH1` | 99 | pH | Pre Rapid Mix |
| `device_pH2` | 96 | pH | Post Flocculation |
| `device_pH3` | 97 | pH | Post Sedimentation |
| `device_ORP` | 98 | ORP | Pre Rapid Mix |
| `device_EC` | 100 | Conductivity | Post Lime Dose |
| `device_RTD1` | 102 | Temperature | Pre Rapid Mix |
| `device_RTD2` | 104 | Temperature | Pre Rapid Mix |
| `device_RTD3` | 105 | Temperature | Post Floc |
| `device_RTD4` | 106 | Temperature | Effluent |
| `device_Pump1` | 109 | Peristaltic pump | Alum Dosing |
| `device_Pump2` | 110 | Peristaltic pump | Lime Dosing |

### Key Function

```python
def _init_device(address: int) -> AtlasI2C
```
Creates an `AtlasI2C` instance using a two-step initialization: a temp instance queries the device, then a fully-populated instance is returned. Safe — logs warnings on query failure rather than raising.

---

## `sensors` (`sensors.py`)

### Purpose
Named, labelled read functions for every sensor. Thin wrappers that add human-readable labels to console output.

### Responsibilities
- Provides one function per sensor, each a call to the private `_read()` helper
- Prints a labelled reading to stdout on every call
- Returns the measurement as a raw string (not converted to float)

### Key Function

```python
def _read(device: AtlasI2C, label: str) -> str:
    device.write("R")
    time.sleep(READ_DELAY)   # 1.5 seconds
    reading = device.read().split(": ")[1].replace('\x00', '').strip()
    print(f"{label} = {reading}")
    return reading
```

### Public Interface

```python
def read_pH1() -> str   # "pH1  (Pre Rapid Mix)"
def read_pH2() -> str   # "pH2  (Post Floc)"
def read_pH3() -> str   # "pH3  (Post Sed)"
def read_ORP() -> str
def read_EC()  -> str
def read_RTD1() -> str
def read_RTD2() -> str
def read_RTD3() -> str
def read_RTD4() -> str
def read_Pump1() -> str
def read_Pump2() -> str
```

### Notes
- `READ_DELAY = 1.5 s` matches `AtlasI2C.LONG_TIMEOUT` — the minimum time for the EZO chip to complete a reading.
- All functions return **strings**, not floats. `main.py` calls `float()` only where needed (e.g., `alum_pump_state(float(pH1))`).
- `read_Pump1()` and `read_Pump2()` query the pump for its current flow-rate reading, not to start/stop it.

---

## `pumps` (`pumps.py`)

### Purpose
All chemical dosing logic. Encapsulates the control decisions for both the Alum (Pump 1) and Lime (Pump 2) dosing systems.

### Responsibilities
- Continuous Alum dosing at startup (fixed duty cycle)
- pH-responsive Lime dosing (reads pH3, applies dose curve)
- Alum pump state reporting with side-effect control (MQTT mode)
- Emergency / shutdown stop for both pumps

### Key Functions

```python
def stop_pumps() -> None
```
Sends `"x"` (stop) to both pumps under `pump1_lock`. Called in the `KeyboardInterrupt` handler.

```python
def _get_lime_dose(pH3_value: float) -> int
```
Dose-response table:

| pH3 | Dose (mL) |
|---|---|
| < 6.5 | 120 |
| 6.5 – 7.1 | 60 |
| ≥ 7.1 | 30 |

```python
def balance_pH(pH3_value: float) -> None
```
Accepts the already-read pH3 float (no extra I2C query), then dispenses lime if `pH3 < 7.2`. Uses `D,-{dose}` (negative volume = run continuously until stopped).

```python
def set_alum_pump_rate(ml_per_min: float) -> None
```
Thread-safe (acquires `pump1_lock`). Used by the Zenoh callback to apply RPi1-commanded flow rates.

```python
def alum_pump_state(pH_value: float) -> str
```
Local fallback: returns `"ON"` or `"OFF"` and writes `D,15` or `D,0` to Pump 1 under `pump1_lock`. Threshold is `ALUM_TRIGGER_pH = 5.5`.

### Atlas EZO Pump Command Reference

| Command | Meaning |
|---|---|
| `DC,{pct},*` | Continuous duty cycle at `pct`% |
| `D,{vol}` | Dispense absolute volume (mL); negative = dispense without stopping |
| `D,{vol}` (negative) | Dispense continuously — pump runs until `x` |
| `x` | Stop pump immediately |

---

## `zenoh_client` (`zenoh_client.py`)

### Purpose
Manages the Zenoh pub/sub session with RPi1. Provides publish and subscribe helpers.

### Responsibilities
- Opens a Zenoh session connecting to RPi1's router at startup (module-level)
- Publishes complete sensor readings as JSON on every loop iteration
- Subscribes to alum pump flow-rate commands from RPi1

### Key Expressions

| Direction | Key | Payload |
|---|---|---|
| Publish (RPi2 → RPi1) | `reno/water/treatment/010` | JSON dict of all sensor readings + timestamp |
| Subscribe (RPi1 → RPi2) | `reno/water/alum/pump` | `{"ml_per_min": float}` |

### Public Interface

```python
def publish_full_readings(payload: dict) -> None
# Adds "timestamp" key, serializes to JSON, calls session.put(KEY_EXPR, ...)

def subscribe_alum_pump(callback) -> object
# Returns a Zenoh subscriber object; callback receives a Sample
```

### Fail-Soft Behavior
If `zenoh.open()` raises at import time, `_session` is set to `None`. All publish/subscribe calls check `if _session is None: return` — the system degrades gracefully to local-only operation.

### Notes
- `100.96.169.94` is a Tailscale VPN address (100.x.x.x range); RPi1 must be reachable on that address.
- The session is never explicitly closed — it lives for the entire process lifetime.
- `publish_readings()` (the old 4-arg version) is dead code; `publish_full_readings()` superseded it.

---

## `logger` (`logger.py`)

### Purpose
CSV data logging. Creates one file per run and appends one row per loop iteration.

### Responsibilities
- Creates a timestamped CSV file with a header row at startup
- Appends sensor readings as a CSV row each loop

### Public Interface

```python
LOG_DIR = "/home/pi/Raspberry-Pi-sample-code/logs"

def new_log_file() -> str
# Returns path: "{LOG_DIR}/{datetime}-UNRWaterTreatment.csv"
# Side effect: writes header row immediately

def log_readings(filename: str, readings: dict) -> None
# Extracts values by key from readings dict, appends one CSV row
```

### CSV Column Order

```
Date/Time, ORP, pH1, RTD1, pH2, RTD2, pH3, RTD3, EC, RTD4, Pump1, Pump2
```

### Notes
- The `readings` dict must contain exactly the keys listed in `LOG_HEADERS` (except `Date/Time`). Missing keys raise `KeyError` — no validation.
- Extra keys in `readings` (like `temperature`, `pump1_state`) are silently ignored by `log_readings`.
- File is opened in `"a"` (append) mode for every write — no buffering beyond the OS.

---

## `main` (`main.py`)

### Purpose
Entry point and orchestrator. Contains the main control loop and the async alum pump callback.

### Responsibilities
- Wires together all subsystems
- Subscribes to alum pump commands from RPi1 before starting the loop
- Runs the 2-second polling loop
- Handles graceful shutdown on Ctrl-C

### Key Variables

```python
LOOP_DELAY = 2   # seconds between loop iterations
```

### `_on_alum_pump(sample)` Callback
Fired by the Zenoh subscriber thread when RPi1 publishes a new alum pump rate:
- Parses `{"ml_per_min": float}` from payload
- If `ml_per_min >= 0.5`: sends `DC,{rate},*` to Pump 1
- Otherwise: sends `"x"` (stop)

### `run()` Function
Main blocking loop. Order of operations per iteration:
1. Read pH1, pH2, pH3
2. `balance_pH()` — may dose Lime (also re-reads pH3)
3. Read RTD1-4, ORP, EC, Pump1, Pump2
4. Compute `pump1_state` via `alum_pump_state()` — **side effect: writes to Pump 1**
5. Assemble `readings` dict
6. Log to CSV
7. Publish via Zenoh
8. Sleep 2 seconds

### systemd Service
Defined in `wtp-rpi2.service`:
- Starts after `network-online.target`
- Runs as user `pi`
- Working directory: `/home/pi/MQTTsystem`
- stdout/stderr appended to `/home/pi/MQTTsystem/wtp-rpi2.log`
- `Restart=always` with 10-second backoff
