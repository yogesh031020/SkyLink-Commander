\# 📡 SkyLink Commander: Web-Based UAV GCS

\*\*High-Level Companion Computer (RPi 4) \& MAVLink Integration\*\*



\### 📝 Project Overview

SkyLink Commander is a custom \*\*Ground Control Station (GCS)\*\* and companion computer interface designed to bridge the gap between legacy flight controllers (APM 2.8) and modern web-based monitoring.



\### 🛠️ System Architecture

```mermaid

graph LR

&#x20;   User\[Web HUD] -->|WebSocket/HTTP| RPi\[Raspberry Pi 4]

&#x20;   RPi -->|MAVLink/Serial| FC\[APM 2.8 Flight Controller]

&#x20;   FC -->|PWM| Motors\[UAV Motors]



