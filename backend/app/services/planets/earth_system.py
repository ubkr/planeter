"""Computes the Earth-Moon system snapshot for the Solsystemet detail view."""
import math
import logging
from datetime import datetime
from typing import Optional

import ephem

logger = logging.getLogger(__name__)

# Physical constants (fall back to these if ephem attributes are absent)
_EARTH_RADIUS_M = 6_371_000.0       # metres
_METERS_PER_AU = 149_597_870_700.0  # metres per astronomical unit


def compute_earth_system(dt: datetime) -> Optional[dict]:
    """
    Return a dict describing the Moon's position relative to Earth, suitable
    for populating EarthSystemInfo / EarthSystemMoon.

    The x/y offsets use a geocentric top-down projection:
        x = distance_ER * cos(hlat) * cos(hlon)   (toward vernal equinox)
        y = distance_ER * cos(hlat) * sin(hlon)   (90° east)

    Note: for PyEphem's Moon body, hlon/hlat carry geocentric semantics
    (Earth-centred longitude/latitude), not heliocentric ecliptic as they
    do for planet bodies.

    Returns None on any computation failure.
    """
    try:
        # Strip tzinfo — ephem does not accept aware datetimes
        naive_dt = dt.replace(tzinfo=None)
        ephem_date = ephem.Date(naive_dt)

        moon = ephem.Moon()
        moon.compute(ephem_date)

        # ephem constants (with hardcoded fallbacks for safety)
        meters_per_au = getattr(ephem, "meters_per_au", _METERS_PER_AU)
        earth_radius_m = getattr(ephem, "earth_radius", _EARTH_RADIUS_M)

        distance_m = float(moon.earth_distance) * meters_per_au
        distance_km = distance_m / 1000.0
        distance_er = distance_m / earth_radius_m  # in Earth radii

        hlon = float(moon.hlon)   # geocentric longitude (radians) — Moon-specific; differs from heliocentric ecliptic used for planets
        hlat = float(moon.hlat)   # geocentric latitude (radians)

        x_offset = distance_er * math.cos(hlat) * math.cos(hlon)
        y_offset = distance_er * math.cos(hlat) * math.sin(hlon)

        illumination = float(moon.phase) / 100.0  # fraction 0.0–1.0

        return {
            "moon": {
                "name_sv": "Månen",
                "x_offset_earth_radii": round(x_offset, 3),
                "y_offset_earth_radii": round(y_offset, 3),
                "distance_km": round(distance_km, 1),
                "illumination": round(illumination, 4),
            }
        }
    except Exception as exc:
        logger.warning("Failed to compute earth_system: %s", exc)
        return None
