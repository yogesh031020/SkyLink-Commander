# SkyLink Commander

Web-based ground control station running on a Raspberry Pi 4, bridging a browser HUD to an APM 2.8 flight controller over MAVLink. Built because Mission Planner is overkill for simple autonomous missions and doesn't run well on Pi — I wanted a lightweight custom GCS I could access from any device on the same network.

## What it does

`commander.py` opens a MAVLink serial connection to the APM 2.8, starts a Flask web server, and streams live telemetry to a browser dashboard over WebSocket. The HUD shows heading, altitude, airspeed, battery voltage, and flight mode — updating every 500ms. Takeoff and landing are triggered from the browser with a single button, which calls the pre-arm check sequence first.

```
Browser (any device) ←→ WebSocket ←→ Flask (RPi 4)
                                          ↓
                                   MAVLink serial
                                          ↓
                                      APM 2.8
                                          ↓
                                       Motors
```

## Setup

`setup_drone.py` runs the pre-arm sequence: checks GPS lock, battery voltage, RC calibration status, and barometer health before allowing takeoff commands. Prevents arming if any check fails.

## Hardware

| Component | Role |
|---|---|
| Raspberry Pi 4 (2GB) | Companion computer + GCS server |
| APM 2.8 | Flight controller |
| USB-to-Serial (CP2102) | RPi ↔ APM UART connection |
| Any browser device | HUD client |

## Run it

```bash
# On the Raspberry Pi:
pip install dronekit flask flask-socketio pymavlink
python commander.py --port /dev/ttyUSB0 --baud 57600
```

Then open `http://:5000` on any device on the same network.

## HUD features

- Live heading indicator (compass rose)
- Altitude and climb rate
- Battery voltage with low-battery warning
- Flight mode display (STABILIZE, GUIDED, AUTO, LAND)
- Arm/disarm status
- One-click takeoff (runs pre-arm checks first) and RTL

## What I learned

WebSocket connections dropped intermittently on weak WiFi. Fixed by adding exponential backoff reconnect logic on the browser side — the HUD now auto-reconnects within 3 seconds of a drop without losing state.

The APM 2.8 sends MAVLink at 57600 baud by default. At higher rates the Pi's USB serial buffer overflowed. Tuned the message request rates via `MAV_DATA_STREAM` to only pull attitude, GPS, and battery — cut CPU usage on the Pi by ~40%.

## Relation to other projects

Designed to work with any APM 2.8 based drone. The MAVLink bridge here was the foundation for the companion computer logic in [wifi-follow-me-drone](https://github.com/yogesh031020/wifi-follow-me-drone).

## Status

Active. Next: add geofence enforcement layer before takeoff approval.
