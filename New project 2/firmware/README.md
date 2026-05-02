# Wind Tunnel Arduino Firmware

Open `Wind_Tunnel_Master_Controller/Wind_Tunnel_Master_Controller.ino` in the Arduino IDE, select **Arduino Mega 2560**, choose the Mega's COM port, and upload.

Before running the fan, set these constants for your real hardware:

- `FAN_ENABLE_PIN`
- `FAN_PWM_PIN`
- `FAN_ENABLE_ACTIVE_HIGH`

The Windows app sends these newline-terminated commands:

- `ON`
- `OFF`
- `0` through `100`

The app expects telemetry lines like:

```text
101325 12.4 22.1
```

That means:

- static pressure in pascals
- dynamic pressure in pascals
- temperature in degrees Celsius
