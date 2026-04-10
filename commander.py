import threading
import time
import json
import asyncio
import uvicorn
from fastapi import FastAPI, WebSocket
from fastapi.responses import HTMLResponse
from pymavlink import mavutil

# --- Drone Connection ---
mavutil.set_dialect("ardupilotmega")
try:
    master = mavutil.mavlink_connection('/dev/ttyS0', baud=57600)
    print("Waiting for Heartbeat...")
    master.wait_heartbeat()
    print("HEARTBEAT RECEIVED!")
except Exception as e:
    print(f"Connection Error: {e}")

drone_state = {"mode": "STABILIZE", "armed": False, "alt": 0.0, "status": "READY", "alt_offset": 0.0}
mission_lock = False

def drone_loop():
    global drone_state
    while True:
        try:
            msg = master.recv_match(type=['HEARTBEAT', 'VFR_HUD', 'STATUSTEXT'], blocking=True, timeout=1)
            if not msg: continue
            if msg.get_type() == 'HEARTBEAT':
                drone_state["armed"] = bool(msg.base_mode & mavutil.mavlink.MAV_MODE_FLAG_SAFETY_ARMED)
                mode_lookup = {0: "STABILIZE", 2: "ALT_HOLD", 9: "LAND", 11: "DRIFT"}
                drone_state["mode"] = mode_lookup.get(msg.custom_mode, f"MODE_{msg.custom_mode}")
            elif msg.get_type() == 'VFR_HUD':
                drone_state["alt"] = msg.alt - drone_state["alt_offset"]
            elif msg.get_type() == 'STATUSTEXT':
                print(f"DRONE SAYS: {msg.text}")
        except: pass

threading.Thread(target=drone_loop, daemon=True).start()

def set_rc_raw(ch1=1500, ch2=1500, ch3=1000, ch4=1500, ch5=1100):
    master.mav.rc_channels_override_send(master.target_system, master.target_component, ch1, ch2, ch3, ch4, ch5, 1500, 1500, 1500)

def set_mode_raw(mode_id):
    master.mav.command_long_send(master.target_system, master.target_component, 176, 0, 1, mode_id, 0, 0, 0, 0, 0)

def takeoff_sequence():
    global drone_state, mission_lock
    if mission_lock: return
    mission_lock = True
    
    try:
        print("--- MISSION STARTING ---")
        drone_state["status"] = "PRE-FLIGHT"
        set_rc_raw(ch5=1100) # Stabilize
        set_mode_raw(0)
        time.sleep(2)
        
        print("STEP 1: WAITING FOR MANUAL ARM (USE TRANSMITTER)...")
        drone_state["status"] = "PLEASE ARM NOW"
        
        # RELEASE CHANNELS 1-4 (set to 0) so the transmitter can work!
        master.mav.rc_channels_override_send(master.target_system, master.target_component, 0, 0, 0, 0, 1100, 0, 0, 0)
        
        # Wait up to 30 seconds for external arming
        start_wait = time.time()
        while not drone_state["armed"]:
            time.sleep(0.1)
            if time.time() - start_wait > 30:
                print("WAITING TIMEOUT. MISSION CANCELLED.")
                drone_state["status"] = "TIMEOUT"
                mission_lock = False
                return

        print("ARM DETECTED! PROCEEDING...")
        drone_state["status"] = "ARMED SUCCESS"
        time.sleep(1) 

        print("STEP 2: ALT_HOLD...")
        set_rc_raw(ch5=1300) # Slot 2
        set_mode_raw(2)
        time.sleep(1)
        
        print("STEP 3: THROTTLE RAMP-UP...")
        drone_state["status"] = "SPOOLING UP"
        for throttle_val in range(1100, 1540, 20):
            set_rc_raw(ch3=throttle_val, ch5=1300)
            time.sleep(0.1)
            if drone_state["armed"] == False:
                drone_state["status"] = "REBOOTED"
                mission_lock = False
                return

        drone_state["status"] = "CLIMBING"
        start_point = time.time()
        while drone_state["alt"] < 0.50 and (time.time() - start_point) < 6:
            time.sleep(0.1)
        
        set_rc_raw(ch3=1500, ch5=1300)
        drone_state["status"] = "HOVERING"
        print("MISSION COMPLETE!")
    finally:
        mission_lock = False

app = FastAPI()

@app.get("/")
async def get():
    return HTMLResponse("""
    <!DOCTYPE html>
    <html>
    <body style="background:#050505; color:#00f2ff; font-family:sans-serif; text-align:center; padding-top:60px;">
        <h1 style="letter-spacing:10px; opacity:0.3;">SKY-LINK COMMANDER</h1>
        <div style="font-size:6rem; margin:20px 0; font-weight:bold;" id="alt">0.00m</div>
        <div id="sys_status" style="font-size:1.5rem; letter-spacing:3px; color:#ff2e63;">READY</div>
        <div id="mode" style="color:#888; font-family:monospace; margin-bottom:40px;">---</div>
        <div style="display:flex; flex-direction:column; align-items:center; gap:15px;">
            <button style="width:300px; padding:15px; border-radius:10px;" onclick="cmd('zero')">ZERO BAROMETER</button>
            <button style="width:300px; padding:20px; background:#08f7fe; border-radius:10px;" onclick="cmd('takeoff')">AUTONOMOUS TAKEOFF</button>
            <button style="width:300px; padding:15px; border-radius:10px;" onclick="cmd('land')">AUTONOMOUS LAND</button>
            <button style="width:300px; padding:15px; background:#ff2e63; color:white; border-radius:10px;" onclick="cmd('disarm')">EMERGENCY STOP</button>
        </div>
        <script>
            const ws = new WebSocket("ws://" + window.location.host + "/ws");
            ws.onmessage = (e) => {
                const d = JSON.parse(e.data);
                document.getElementById('alt').innerText = d.alt.toFixed(2) + "m";
                document.getElementById('mode').innerText = d.mode;
                document.getElementById('sys_status').innerText = d.status;
            };
            async function cmd(c) { await fetch('/cmd/' + c, {method: 'POST'}); }
        </script>
    </body>
    </html>
    """)

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    while True:
        await websocket.send_text(json.dumps(drone_state))
        await asyncio.sleep(0.1)

@app.post("/cmd/{command}")
async def run_command(command: str):
    global drone_state, mission_lock
    if command == 'zero': drone_state["alt_offset"] = drone_state["alt"] + drone_state["alt_offset"]
    elif command == 'takeoff': threading.Thread(target=takeoff_sequence).start()
    elif command == 'land': 
        mission_lock = False
        set_rc_raw(ch3=1400, ch5=1500)
        set_mode_raw(9)
    elif command == 'disarm':
        mission_lock = False
        master.mav.command_long_send(master.target_system, master.target_component, 75, 0, 0, 21196, 0, 0, 0, 0, 0)
        drone_state["status"] = "READY"
        set_rc_raw(ch3=1000)
    return {"status": "ok"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
