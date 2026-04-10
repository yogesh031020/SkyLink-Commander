# SkyLink Commander: V1.0 (Flight Confirmed) 🚀🏆

This project enables a Raspberry Pi 4 to act as an autonomous "Mission Commander" for an APM 2.8 flight controller. It includes a web-based HUD for remote operation and proof-of-concept autonomous takeoff logic.

## 🏆 Mission Success!
**Status: FLIGHT CONFIRMED.** 
The drone successfully executed an autonomous takeoff to 1 meter and a controlled autonomous landing. This proves that the isolated power architecture (5A separate adapter + ESC BEC bypass) is the correct foundation for this platform.

## 📂 Project Structure
- `commander.py`: The main flight control logic and FastAPI dashboard.
- `setup_drone.py`: Utility to disable "Spin on Arm" and safety checks for bench testing.
- `docs/wiring_isolation.md`: Detailed guide on hardware power separation.

## 🚀 How to Run
1. **Prepare Hardware:**
   - Remove JP1 Jumper.
   - Remove Red wires from all ESC connectors.
   - Power APM via the Raspberry Pi 5V/GND Pins.
2. **Setup Pi:**
   ```bash
   pip install fastapi uvicorn pymavlink
   python3 setup_drone.py
   ```
3. **Engage Mission:**
   - Run `python3 commander.py`.
   - Open HUD at `http://<pi-ip>:8000`.
   - Wait for barometer calibration, Zero the HUD, and click **Takeoff**.

## ⚠️ Important Note for Phase 2
The APM 2.8 may still require a **1000uF 16V Capacitor** on the power rail if any vibration-induced resets occur during actual flight.
