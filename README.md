# ?? SkyLink Commander: Web-Based UAV GCS
**High-Level Companion Computer (RPi 4) & MAVLink Integration**

### ?? Project Overview
SkyLink Commander is a custom **Ground Control Station (GCS)** and companion computer interface designed to bridge the gap between legacy flight controllers (APM 2.8) and modern web-based monitoring.

### ??? System Architecture
\\\mermaid
graph LR
    User[Web HUD] -->|WebSocket/HTTP| RPi[Raspberry Pi 4]
    RPi -->|MAVLink/Serial| FC[APM 2.8 Flight Controller]
    FC -->|PWM| Motors[UAV Motors]
\\\

### ?? Technical Specifications
*   **MCU:** Raspberry Pi 4 (Model B).
*   **Protocols:** MAVLink v1.0, WebSockets.
*   **Stack:** Python, Flask/FastAPI, HTML5 Canvas HUD.
