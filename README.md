# SkyLink Commander: V1.0 (Flight Confirmed) 🚀🏆

This project enables a Raspberry Pi 4 to act as an autonomous "Mission Commander" for an APM 2.8 flight controller. It includes a web-based HUD for remote operation and proof-of-concept autonomous takeoff logic.

## 🏆 Mission Success

**Status: FLIGHT CONFIRMED.**
The drone successfully executed an autonomous takeoff to 1 meter and a controlled autonomous landing. This proves that the isolated power architecture is the correct foundation for this platform.

## 🛠️ Complete Hardware Inventory

### 🧠 Computing & Control
* **Flight Controller:** APM 2.8 (Flight Brain)
* **Companion Computer:** Raspberry Pi 4 (Edge Compute Manager)
* **Radio Receiver:** Standard PWM/PPM Receiver

### 🔌 Power Architecture (Stability Isolated)
* **Motor Power:** 11.1V 3S 2200mAh LiPo Battery
* **Logic Power:** Dedicated 5V 5A Power Supply (Filtered)
* **Isolation Jumper:** JP1 Jumper Removed
* **BEC Override:** Red (+5V) wires removed from all 4 ESC-to-APM signal cables

### ⚙️ Propulsion
* **Motors:** 4x Brushless DC Motors
* **ESCs:** 4x 30A Electronic Speed Controllers
* **Frame:** Standard Quadcopter Frame (F450 style)

### 🛰️ Sensors & Telemetry
* **Telemetry Link:** UART Serial Connection (Pi GPIO 14/15 ↔ APM Telemetry Port)
* **Altitude Sensor:** Internal MS5611 Barometer
* **Stability Sensor:** Internal MPU6000 Accelerometer/Gyro

## 📂 Project Structure

* `commander.py`: The main flight control logic and FastAPI dashboard.
* `setup_drone.py`: Utility to disable "Spin on Arm" and safety checks for bench testing.
* `docs/wiring_isolation.md`: Detailed guide on hardware power separation.

## 🚀 How to Run

1. **Prepare Hardware:**
   * Remove JP1 Jumper.
   * Remove Red wires from all ESC connectors.
   * Power APM via the Raspberry Pi 5V/GND Pins (connected to the Inputs rail).

2. **Setup Pi:**
   ```bash
   pip install fastapi uvicorn pymavlink
   python3 setup_drone.py
   ```

3. **Engage Mission:**
   * Run `python3 commander.py`.
   * Open HUD at `http://<pi-ip>:8000`.
   * Click **AUTONOMOUS TAKEOFF** (The HUD will say "PLEASE ARM NOW").
   * **Arm your drone manually** with your transmitter stick (Bottom-Right corner).
   * Once detected, the Pi will automatically switch to Alt-Hold and Takeoff!

## ⚠️ Important Note for Phase 2
The APM 2.8 may still require a **1000uF 16V Capacitor** on the power rail if any vibration-induced resets occur during high-throttle maneuvers.
