from pymavlink import mavutil
import time

try:
    master = mavutil.mavlink_connection('/dev/ttyS0', baud=57600)
    master.wait_heartbeat()
    print("Connected to APM!")

    def set_param(name, val):
        print(f"Setting {name} to {val}...")
        master.mav.param_set_send(master.target_system, master.target_component, name.encode('utf-8'), val, mavutil.mavlink.MAV_PARAM_TYPE_REAL32)
        time.sleep(1)

    # Disable Spin on Arm to prevent power spikes
    set_param('MOT_SPIN_ARMED', 0)
    # Disable Arming Safety Checks for bench testing
    set_param('ARMING_CHECK', 0)
    # Enable Throttle Overrides
    set_param('FS_THR_ENABLE', 0)

    print("\nDONE! Parameters optimized for isolated power. Please reboot APM.")
except Exception as e:
    print(f"Setup Error: {e}")
