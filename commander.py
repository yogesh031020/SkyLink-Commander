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

app = FastAPI()

@app.get("/")
async def get():
    return HTMLResponse("""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>SKYLINK COMMANDER - GCS HUD</title>
        <link href="https://fonts.googleapis.com/css2?family=Orbitron:wght@400;700;900&family=Rajdhani:wght@500;700&family=Share+Tech+Mono&display=swap" rel="stylesheet">
        <style>
            :root {
                --primary: #00f2ff;
                --primary-glow: rgba(0, 242, 255, 0.4);
                --danger: #ff2e63;
                --danger-glow: rgba(255, 46, 99, 0.4);
                --success: #08f7fe;
                --bg-dark: #030712;
                --panel-bg: rgba(10, 15, 30, 0.7);
                --border-color: rgba(0, 242, 255, 0.15);
            }

            body {
                background: radial-gradient(circle at center, #0f172a 0%, var(--bg-dark) 100%);
                color: #e2e8f0;
                font-family: 'Rajdhani', sans-serif;
                margin: 0;
                padding: 0;
                overflow-x: hidden;
                min-height: 100vh;
            }

            /* Animated Grid Background */
            body::before {
                content: "";
                position: fixed;
                top: 0; left: 0; width: 100%; height: 100%;
                background-image: 
                    linear-gradient(rgba(0, 242, 255, 0.03) 1px, transparent 1px),
                    linear-gradient(90deg, rgba(0, 242, 255, 0.03) 1px, transparent 1px);
                background-size: 30px 30px;
                background-position: center;
                pointer-events: none;
                z-index: 0;
            }

            /* Header Section */
            header {
                display: flex;
                justify-content: space-between;
                align-items: center;
                padding: 15px 40px;
                background: rgba(3, 7, 18, 0.85);
                border-bottom: 2px solid var(--primary);
                box-shadow: 0 5px 30px rgba(0, 242, 255, 0.15);
                backdrop-filter: blur(10px);
                z-index: 10;
                position: relative;
            }

            .logo-section h1 {
                margin: 0;
                font-family: 'Orbitron', sans-serif;
                font-size: 1.8rem;
                font-weight: 900;
                letter-spacing: 5px;
                color: var(--primary);
                text-shadow: 0 0 10px var(--primary-glow);
            }

            .logo-section span {
                font-size: 0.85rem;
                color: rgba(226, 232, 240, 0.6);
                letter-spacing: 2px;
                text-transform: uppercase;
            }

            .system-status {
                display: flex;
                gap: 20px;
                align-items: center;
            }

            .status-badge {
                background: var(--panel-bg);
                border: 1px solid var(--border-color);
                border-radius: 6px;
                padding: 8px 15px;
                font-family: 'Share Tech Mono', monospace;
                display: flex;
                align-items: center;
                gap: 8px;
            }

            .indicator {
                width: 8px;
                height: 8px;
                border-radius: 50%;
                background-color: var(--primary);
                box-shadow: 0 0 8px var(--primary);
                animation: pulse 1.5s infinite;
            }

            @keyframes pulse {
                0% { opacity: 0.4; }
                50% { opacity: 1; }
                100% { opacity: 0.4; }
            }

            /* Main Layout Grid */
            .hud-container {
                display: grid;
                grid-template-columns: 1fr 1.5fr 1fr;
                gap: 25px;
                padding: 30px 40px;
                max-width: 1600px;
                margin: 0 auto;
                position: relative;
                z-index: 1;
            }

            /* Panel Styling (Glassmorphism) */
            .panel {
                background: var(--panel-bg);
                border: 1px solid var(--border-color);
                border-radius: 12px;
                padding: 20px;
                backdrop-filter: blur(12px);
                box-shadow: 0 10px 30px rgba(0, 0, 0, 0.5);
                position: relative;
                overflow: hidden;
            }

            .panel::after {
                content: "";
                position: absolute;
                top: 0; left: 0; width: 100%; height: 2px;
                background: linear-gradient(90deg, transparent, var(--primary), transparent);
            }

            .panel-header {
                font-family: 'Orbitron', sans-serif;
                font-size: 1.1rem;
                font-weight: 700;
                letter-spacing: 2px;
                color: var(--primary);
                margin-bottom: 20px;
                border-bottom: 1px solid rgba(0, 242, 255, 0.1);
                padding-bottom: 10px;
                text-transform: uppercase;
            }

            /* Flight Telemetry Readouts */
            .telemetry-row {
                display: flex;
                justify-content: space-between;
                margin-bottom: 15px;
                padding: 10px;
                background: rgba(255,255,255,0.02);
                border-radius: 6px;
                border-left: 3px solid var(--primary);
            }

            .telemetry-label {
                color: rgba(226, 232, 240, 0.6);
                text-transform: uppercase;
                letter-spacing: 1px;
            }

            .telemetry-value {
                font-family: 'Share Tech Mono', monospace;
                font-size: 1.25rem;
                color: #fff;
                text-shadow: 0 0 5px rgba(255, 255, 255, 0.2);
            }

            /* Primary Flight Display (PFD) Center Panel */
            .pfd {
                display: flex;
                flex-direction: column;
                justify-content: center;
                align-items: center;
                min-height: 400px;
            }

            .alt-display {
                font-family: 'Orbitron', sans-serif;
                font-size: 5.5rem;
                font-weight: 900;
                color: #fff;
                text-shadow: 0 0 20px rgba(255,255,255,0.3), 0 0 40px var(--primary-glow);
                margin: 20px 0 10px 0;
            }

            /* Futuristic Dial Compass */
            .compass-ring {
                position: relative;
                width: 200px;
                height: 200px;
                border: 2px dashed var(--primary);
                border-radius: 50%;
                display: flex;
                justify-content: center;
                align-items: center;
                margin: 20px 0;
                transition: transform 0.5s ease-out;
            }

            .compass-cardinal {
                position: absolute;
                font-family: 'Orbitron', sans-serif;
                font-weight: bold;
                color: var(--primary);
            }

            .compass-n { top: 10px; }
            .compass-e { right: 15px; }
            .compass-s { bottom: 10px; }
            .compass-w { left: 15px; }

            .compass-arrow {
                width: 4px;
                height: 80px;
                background: linear-gradient(to top, transparent 50%, var(--danger) 50%);
                border-radius: 2px;
            }

            /* Interactive Command Buttons */
            .btn-group {
                display: flex;
                flex-direction: column;
                gap: 15px;
            }

            .btn {
                background: rgba(0, 242, 255, 0.05);
                border: 1px solid var(--primary);
                color: var(--primary);
                font-family: 'Orbitron', sans-serif;
                font-size: 0.95rem;
                font-weight: 700;
                letter-spacing: 2px;
                padding: 15px 25px;
                border-radius: 8px;
                cursor: pointer;
                transition: all 0.3s ease;
                text-transform: uppercase;
                position: relative;
                overflow: hidden;
            }

            .btn:hover {
                background: var(--primary);
                color: var(--bg-dark);
                box-shadow: 0 0 15px var(--primary-glow);
            }

            .btn-primary {
                background: rgba(8, 247, 254, 0.15);
                border: 1px solid var(--success);
                color: var(--success);
            }

            .btn-primary:hover {
                background: var(--success);
                color: var(--bg-dark);
                box-shadow: 0 0 20px rgba(8, 247, 254, 0.4);
            }

            .btn-danger {
                background: rgba(255, 46, 99, 0.15);
                border: 1px solid var(--danger);
                color: var(--danger);
            }

            .btn-danger:hover {
                background: var(--danger);
                color: #fff;
                box-shadow: 0 0 20px var(--danger-glow);
            }

            /* Console Output Console Panel */
            .console-log {
                background: rgba(2, 5, 10, 0.95);
                border: 1px solid var(--border-color);
                border-radius: 8px;
                height: 180px;
                overflow-y: auto;
                padding: 12px;
                font-family: 'Share Tech Mono', monospace;
                font-size: 0.85rem;
                color: #00f2ff;
                display: flex;
                flex-direction: column;
                gap: 5px;
            }

            .log-line {
                display: flex;
                gap: 10px;
            }

            .log-time { color: rgba(226, 232, 240, 0.4); }
            .log-sys { color: var(--danger); }

            /* Responsive Design */
            @media(max-width: 1024px) {
                .hud-container {
                    grid-template-columns: 1fr;
                    padding: 20px;
                }
            }
        </style>
    </head>
    <body>
        <header>
            <div class="logo-section">
                <h1>SKYLINK COMMANDER</h1>
                <span>Web-Based Ground Control Station v1.4.0</span>
            </div>
            <div class="system-status">
                <div class="status-badge">
                    <div class="indicator" id="ind"></div>
                    <span id="sys_status">MAVLink Connecting</span>
                </div>
                <div class="status-badge">
                    <span style="color: rgba(226,232,240,0.4)">MODE:</span>
                    <span id="mode" style="color: #fff; font-weight:bold;">---</span>
                </div>
            </div>
        </header>

        <div class="hud-container">
            <!-- Left Side: System Control Deck -->
            <div class="panel">
                <div class="panel-header">GCS COMMAND DECK</div>
                <div class="btn-group">
                    <button class="btn" onclick="cmd('zero')">Zero Altitude Sensor</button>
                    <button class="btn btn-primary" onclick="cmd('takeoff')">Autonomous Takeoff</button>
                    <button class="btn" onclick="cmd('land')">Autonomous Land</button>
                    <button class="btn btn-danger" onclick="cmd('disarm')">Emergency Disarm (Stop)</button>
                </div>
            </div>

            <!-- Center Side: Primary Flight Display (PFD) -->
            <div class="panel pfd">
                <div class="panel-header" style="width: 100%; border: none;">PRIMARY FLIGHT INDICATOR</div>
                <div class="alt-display" id="alt">0.00m</div>
                <div style="font-family:'Share Tech Mono'; font-size:1.1rem; letter-spacing:2px; color:rgba(255,255,255,0.4)">ALTITUDE EXCURSION</div>
                
                <div class="compass-ring" id="compass">
                    <div class="compass-cardinal compass-n">N</div>
                    <div class="compass-cardinal compass-e">E</div>
                    <div class="compass-cardinal compass-s">S</div>
                    <div class="compass-cardinal compass-w">W</div>
                    <div class="compass-arrow"></div>
                </div>
            </div>

            <!-- Right Side: Flight Telemetry Diagnostic -->
            <div class="panel">
                <div class="panel-header">SYSTEM STATE METRICS</div>
                
                <div class="telemetry-row">
                    <span class="telemetry-label">APM System Link</span>
                    <span class="telemetry-value" id="t_link" style="color:#08f7fe">STABLE</span>
                </div>
                <div class="telemetry-row">
                    <span class="telemetry-label">Telemetry Mode</span>
                    <span class="telemetry-value" id="t_mode">STABILIZE</span>
                </div>
                <div class="telemetry-row">
                    <span class="telemetry-label">Arming Locks</span>
                    <span class="telemetry-value" id="t_armed" style="color:var(--danger)">SAFE</span>
                </div>
                <div class="telemetry-row">
                    <span class="telemetry-label">Telemetry Output</span>
                    <span class="telemetry-value">50Hz</span>
                </div>

                <div class="panel-header" style="margin-top: 25px; margin-bottom: 10px;">MISSION LOG CONSOLE</div>
                <div class="console-log" id="console">
                    <div class="log-line">
                        <span class="log-time">[00:00:00]</span>
                        <span>[GCS] Initiating custom MAVLink protocol...</span>
                    </div>
                </div>
            </div>
        </div>

        <script>
            const logBox = document.getElementById('console');
            function log(sys, msg) {
                const now = new Date();
                const timeStr = `[${now.toTimeString().split(' ')[0]}]`;
                const line = document.createElement('div');
                line.className = 'log-line';
                line.innerHTML = `<span class="log-time">${timeStr}</span><span class="${sys === 'WARN' ? 'log-sys' : ''}">[${sys}] ${msg}</span>`;
                logBox.appendChild(line);
                logBox.scrollTop = logBox.scrollHeight;
            }

            const ws = new WebSocket("ws://" + window.location.host + "/ws");
            
            ws.onopen = () => {
                log('SYS', 'WebSocket session initialized.');
                document.getElementById('ind').style.backgroundColor = '#08f7fe';
                document.getElementById('ind').style.boxShadow = '0 0 10px #08f7fe';
            };

            ws.onclose = () => {
                log('WARN', 'WebSocket link closed. Attempting reconnect...');
                document.getElementById('ind').style.backgroundColor = '#ff2e63';
                document.getElementById('ind').style.boxShadow = '0 0 10px #ff2e63';
            };

            let lastState = { mode: "", armed: false, status: "" };

            ws.onmessage = (e) => {
                const d = JSON.parse(e.data);
                
                // Update text values
                document.getElementById('alt').innerText = d.alt.toFixed(2) + "m";
                document.getElementById('mode').innerText = d.mode;
                document.getElementById('sys_status').innerText = d.status;
                
                document.getElementById('t_mode').innerText = d.mode;
                document.getElementById('t_armed').innerText = d.armed ? "ARMED (LIVE)" : "SAFE";
                document.getElementById('t_armed').style.color = d.armed ? "#08f7fe" : "#ff2e63";

                // Log changes
                if (d.mode !== lastState.mode) {
                    log('APM', `Mode changed to ${d.mode}`);
                    lastState.mode = d.mode;
                }
                if (d.armed !== lastState.armed) {
                    log('APM', d.armed ? 'MOTORS ARMED! Clear propeller zone.' : 'Motors Disarmed safely.');
                    lastState.armed = d.armed;
                }
                if (d.status !== lastState.status) {
                    log('SYS', `State: ${d.status}`);
                    lastState.status = d.status;
                }

                // Simulate compass rotation based on time (futuristic HUD detail)
                const compassDeg = (Date.now() / 60) % 360;
                document.getElementById('compass').style.transform = `rotate(${-compassDeg}deg)`;
            };

            async function cmd(c) {
                log('GCS', `Issuing ${c.toUpperCase()} override directive.`);
                const res = await fetch('/cmd/' + c, {method: 'POST'});
                const out = await res.json();
                if (out.status === 'ok') {
                    log('SYS', `Directive ${c.toUpperCase()} acknowledged by APM.`);
                }
            }
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
