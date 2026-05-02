# Wind Tunnel Control

Windows desktop control app for an Arduino Mega based wind tunnel controller.

## What This Includes

- `wind_tunnel_control/`: the Tkinter + PySerial desktop application
- `firmware/`: Arduino Mega firmware that accepts PC commands and forwards sensor telemetry
- `build_windows.ps1`: builds the one-file Windows `.exe`
- `installer/WindTunnelControl.iss`: optional Inno Setup script for a normal Windows installer

## The File You Give People

The final downloadable app is:

```text
dist\WindTunnelControl.exe
```

That one file includes Python and the app dependencies. The Windows computer does not need Python installed to run it.

The Arduino Mega still needs working USB serial drivers and the correct firmware uploaded first.

## Run During Development

Install Python 3.10 or newer, then run:

```powershell
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m wind_tunnel_control
```

Connect the Arduino Mega by USB, choose its COM port in the app, and click **Connect**.

## Build the One-File Windows App

Run this on Windows. PyInstaller builds for the operating system it is running on, so the Windows `.exe` should be built on a Windows computer:

```powershell
.\build_windows.ps1
```

The script creates:

- `dist\WindTunnelControl.exe`: the one file to download/copy/run
- `dist\installers\WindTunnelControlSetup.exe`: optional installer, only if Inno Setup 6 is installed

For your goal, distribute `dist\WindTunnelControl.exe`.

The first time someone opens an unsigned `.exe`, Windows SmartScreen may show a warning. For a class/project tool this is normal. For a polished public release, buy a Windows code-signing certificate and sign the `.exe`.

## Serial Protocol

The app sends newline-terminated commands:

```text
ON
OFF
0
50
100
```

The Arduino sends status lines starting with `UPDATE:` or `ERROR:`. Sensor readings should be one line with:

```text
static_pressure dynamic_pressure temperature
```

Example:

```text
101325 12.4 22.1
```

The app calculates wind speed from those values.

## Important Hardware Notes

The firmware defaults to `FAN_ENABLE_PIN = 7` and `FAN_PWM_PIN = 9`. Change those before running the tunnel. The app can send commands, but the motor controller wiring, relay logic, sensor baud rate, and safety interlocks must match your actual hardware.
