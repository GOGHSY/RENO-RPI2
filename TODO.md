# TODO — RENO-RPI2

Issues and improvements identified by static analysis of the codebase.

---

## Bugs

### 1. ~~Pump 1 controlled from two threads without synchronization~~ ✅ FIXED
`pumps.py` now exports `pump1_lock: threading.Lock`. All writes to `device_Pump1` in `set_alum_pump_rate()` and `alum_pump_state()` acquire the lock. The Zenoh callback uses `set_alum_pump_rate()` instead of writing directly.

### 2. ~~pH3 is read twice per loop cycle~~ ✅ FIXED
`balance_pH()` now accepts `pH3_value: float` as a parameter. The main loop passes `float(pH3)` (the already-read value) instead of triggering a second I2C read.

### 3. ~~`alum_pump_state()` side effect invisible~~ ✅ PARTIALLY FIXED
A separate `set_alum_pump_rate()` function now handles RPi1-commanded rates. `alum_pump_state()` is retained as the local fallback (still has the write side effect by design — it is the local control path).

### 4. ~~CSV filename contains colons~~ ✅ FIXED
`logger.py` now uses `strftime("%Y%m%d_%H%M%S")` for the filename timestamp.

---

## Dead Code

### 5. ~~`dispense_alum()` is never called~~ ✅ FIXED
Removed from `pumps.py`.

### 6. ~~`publish_readings()` is never called~~ ✅ FIXED
Removed from `zenoh_client.py`.

---

## Missing Error Handling

### 7. ~~`_read()` silently returns error codes as data~~ ✅ FIXED
`sensors._read()` now checks for `"Success"` prefix before parsing. Returns `"ERROR"` string on failed reads and logs the raw error to stdout.

### 8. No retry on I2C read failure
**File:** `sensors.py`  
A transient I2C `IOError` still propagates up to `main.py`'s loop, crashing the service (triggering 10-second systemd restart).  
**Fix:** Wrap `_read()` in a try/except with one retry before propagating.

### 9. ~~Log directory not created on startup~~ ✅ FIXED
`logger.new_log_file()` now calls `os.makedirs(LOG_DIR, exist_ok=True)` before creating the file.

---

## Technical Debt

### 10. Path mismatch: service vs. log directory
**File:** `wtp-rpi2.service:9`, `logger.py:9`  
The service `WorkingDirectory` is `/home/pi/MQTTsystem` but logs go to `/home/pi/Raspberry-Pi-sample-code/logs`. These names don't match — the first suggests a rewrite from an older MQTT-based system; the second suggests even older sample code. The service log (`wtp-rpi2.log`) and data logs go to different directories with no obvious rationale.  
**Fix:** Standardize on one directory; update both `wtp-rpi2.service` and `logger.py`.

### 11. All configuration is hard-coded
**File:** `zenoh_client.py:12-13`, `logger.py:9`, `main.py:29`  
IP address, port, Zenoh key expressions, log path, and loop timing are all literals in source files. Changing the network topology requires a code change.  
**Fix:** Move configuration to a `config.ini`, `.env`, or command-line arguments.

### 12. No structured logging
**File:** All files  
All diagnostic output uses `print()`. There is no log level, no timestamps in stdout output, and no way to suppress verbose per-reading prints without editing source.  
**Fix:** Replace `print()` with Python's `logging` module; set log level via environment variable.

### 13. `AtlasI2C` file handles never explicitly closed
**File:** `AtlasI2C.py:171-172`  
`close()` is defined but never called. Under normal operation the handles leak until process exit (which is fine on a dedicated embedded system, but poor practice).

### 14. Zenoh session never closed
**File:** `zenoh_client.py:17-23`  
`_session.close()` is never called, even on `KeyboardInterrupt`. The Zenoh protocol may not deliver in-flight messages.

---

## Suggested Improvements

### 15. Add watchdog / heartbeat
If a sensor hangs on a read, the `time.sleep(READ_DELAY)` in `_read()` waits but the EZO command might have already been lost. A timeout-aware I2C wrapper would catch this.

### 16. Separate sensor sampling from dosing control
Currently `balance_pH()` is called between pH reads and temperature reads, making the loop's timing hard to reason about. A cleaner architecture would complete all reads first, then apply all control decisions.

### 17. Dose rate limiting for Lime pump
`balance_pH()` can dispense 120 mL of lime every 2 seconds if pH3 stays below 6.5. There is no rate limit, cooldown, or total-volume guard. Over-dosing lime is chemically dangerous.

### 18. No unit documentation on sensor outputs
The `readings` dict keys have no associated units. `RTD1` is in °C, `EC` is in μS/cm, `ORP` is in mV — but none of this is captured in code or comments.
