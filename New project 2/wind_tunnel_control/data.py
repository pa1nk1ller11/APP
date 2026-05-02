"""Parsing and calculations for wind tunnel telemetry."""

from __future__ import annotations

from dataclasses import dataclass
import math
import re
from typing import Optional


AIR_GAS_CONSTANT = 287.05  # J/(kg*K), dry air


@dataclass(frozen=True)
class TunnelReading:
    static_pressure_pa: float
    dynamic_pressure_pa: float
    temperature_c: float
    wind_speed_mps: Optional[float]


def calculate_wind_speed_mps(
    dynamic_pressure_pa: float,
    static_pressure_pa: float,
    temperature_c: float,
) -> Optional[float]:
    """Calculate wind speed from pressure and temperature.

    The formula assumes absolute static pressure in pascals. If the sensor is
    reporting gauge pressure, set the firmware/sensor output to absolute
    pressure before relying on this value.
    """

    if dynamic_pressure_pa <= 0:
        return 0.0

    temperature_k = temperature_c + 273.15
    if static_pressure_pa <= 0 or temperature_k <= 0:
        return None

    air_density = static_pressure_pa / (AIR_GAS_CONSTANT * temperature_k)
    if air_density <= 0:
        return None

    return math.sqrt((2.0 * dynamic_pressure_pa) / air_density)


def parse_tunnel_reading(line: str) -> Optional[TunnelReading]:
    """Parse telemetry lines in the format: static_pressure dynamic_pressure temp."""

    clean_line = line.strip()
    if not clean_line:
        return None

    if clean_line.upper().startswith(("UPDATE:", "ERROR:")):
        return None

    parts = re.split(r"[\s,]+", clean_line)
    if len(parts) < 3:
        return None

    try:
        static_pressure = float(parts[0])
        dynamic_pressure = float(parts[1])
        temperature = float(parts[2])
    except ValueError:
        return None

    wind_speed = calculate_wind_speed_mps(dynamic_pressure, static_pressure, temperature)
    return TunnelReading(static_pressure, dynamic_pressure, temperature, wind_speed)
