"""
device_config.py
----------------
Atlas I2C device initialization for the UNR Water Treatment system.
Import this module to get pre-initialized device objects.
"""

from AtlasI2C import AtlasI2C


def _init_device(address: int) -> AtlasI2C:
    dev = AtlasI2C()
    dev.set_i2c_address(address)

    # Parse module type safely
    try:
        response = dev.query("I")
        parts = response.split(",")
        moduletype = parts[1] if len(parts) > 1 else "UNKNOWN"
    except Exception as e:
        print(f"Warning: could not get module type for address {address}: {e}")
        moduletype = "UNKNOWN"

    # Parse device name safely
    try:
        name_response = dev.query("name,?")
        name_parts = name_response.split(",")
        name = name_parts[1] if len(name_parts) > 1 else f"device_{address}"
    except Exception as e:
        print(f"Warning: could not get name for address {address}: {e}")
        name = f"device_{address}"

    return AtlasI2C(address=address, moduletype=moduletype, name=name)

# ¿¿ pH Probes ¿¿¿¿¿¿¿¿¿¿¿¿¿¿¿¿¿¿¿¿¿¿¿¿¿¿¿¿¿¿¿¿¿¿¿¿¿¿¿¿¿¿¿¿¿¿¿¿¿¿¿¿¿¿¿¿¿¿¿¿¿¿¿¿
device_pH1  = _init_device(99)   # Pre Rapid Mix
device_pH2  = _init_device(96)   # Post Flocculation
device_pH3  = _init_device(97)   # Post Sedimentation

# ¿¿ ORP ¿¿¿¿¿¿¿¿¿¿¿¿¿â€¿¿¿¿¿¿¿¿¿¿¿¿¿¿¿¿¿¿¿¿¿¿¿¿¿¿¿¿¿¿¿¿¿¿¿¿¿¿¿¿¿¿¿¿¿¿¿¿¿¿¿¿¿¿¿¿
device_ORP  = _init_device(98)   # Pre Rapid Mix

# ¿¿ Conductivity ¿¿¿¿¿¿¿¿¿¿¿¿¿¿¿¿¿¿¿¿¿¿¿¿¿¿¿¿¿¿¿¿¿¿¿¿¿¿¿¿¿¿¿¿¿¿¿¿¿¿¿¿¿¿¿¿¿¿¿¿¿
device_EC   = _init_device(100)  # Post Lime Dose

# ¿¿ Temperature (RTD) ¿¿¿¿¿¿¿¿¿¿¿¿¿¿¿¿¿¿¿¿¿¿¿¿¿¿¿¿¿¿¿¿¿¿¿¿¿¿¿¿¿¿¿¿¿¿¿¿¿¿¿¿¿¿¿¿
device_RTD1 = _init_device(102)  # Pre Rapid Mix
device_RTD2 = _init_device(104)  # Pre Rapid Mix
device_RTD3 = _init_device(105)  # Post Floc
device_RTD4 = _init_device(106)  # Effluent

# ¿¿ Pumps ¿¿¿¿¿¿¿¿¿¿¿¿¿¿¿¿¿¿¿¿¿¿¿¿¿¿¿¿¿¿¿¿¿¿¿¿¿¿¿¿¿¿¿¿¿¿¿¿€¿¿¿¿¿¿¿¿¿¿¿¿¿¿¿¿¿¿¿¿
device_Pump1 = _init_device(109)  # Alum Dosing
device_Pump2 = _init_device(110)  # Lime Dosing¿
