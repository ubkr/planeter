"""
Heliocentric position calculator for the five naked-eye planets.

Computes each planet's position in a Sun-centred Cartesian coordinate system
(ecliptic plane, J2000 epoch) using the ephem library.  The resulting XYZ
values are expressed in Astronomical Units (AU) and are intended for the
solar-system overview rendering in the frontend sky map.

Coordinate convention:
  - X axis points toward the vernal equinox (ecliptic longitude = 0).
  - Y axis is 90 degrees east in the ecliptic plane.
  - Z axis points toward the ecliptic north pole.
"""

import ephem
import logging
import math
from datetime import datetime, timezone
from typing import Dict, Optional

logger = logging.getLogger(__name__)

# Ordered list of (English name, ephem class) pairs matching the planet order
# used throughout the rest of the codebase.
_PLANET_CLASSES = [
    ("Mercury", ephem.Mercury),
    ("Venus",   ephem.Venus),
    ("Mars",    ephem.Mars),
    ("Jupiter", ephem.Jupiter),
    ("Saturn",  ephem.Saturn),
]


def compute_heliocentric_positions(dt: datetime) -> Dict[str, Dict[str, float]]:
    """
    Return heliocentric Cartesian positions for the five naked-eye planets.

    Each planet is computed without an observer (Sun-centred frame).  The
    ephem attributes ``hlon``, ``hlat``, and ``sun_distance`` give the
    heliocentric ecliptic longitude (radians), latitude (radians), and
    distance from the Sun (AU) respectively.  These are converted to
    Cartesian XYZ using standard spherical-to-Cartesian formulae.

    Args:
        dt: UTC datetime for the calculation.  May be timezone-aware or
            timezone-naive; timezone-aware values are converted to UTC before
            being passed to ephem, which requires naive UTC.

    Returns:
        A dict keyed by English planet name (``"Mercury"``, ``"Venus"``,
        ``"Mars"``, ``"Jupiter"``, ``"Saturn"``).  Each value is a dict with:
            ``heliocentric_x_au`` (float)
            ``heliocentric_y_au`` (float)
            ``heliocentric_z_au`` (float)
        If a planet's calculation fails, its key is omitted rather than
        raising an exception.
    """
    # ephem does not accept timezone-aware datetimes.
    if dt.tzinfo is not None:
        dt = dt.astimezone(timezone.utc).replace(tzinfo=None)

    result: Dict[str, Dict[str, float]] = {}

    for name, planet_class in _PLANET_CLASSES:
        try:
            body = planet_class()
            # Compute without an observer — this populates heliocentric attrs.
            body.compute(dt)

            hlon = float(body.hlon)          # radians, heliocentric ecliptic longitude
            hlat = float(body.hlat)          # radians, heliocentric ecliptic latitude
            dist = float(body.sun_distance)  # AU

            cos_lat = math.cos(hlat)
            x = dist * cos_lat * math.cos(hlon)
            y = dist * cos_lat * math.sin(hlon)
            z = dist * math.sin(hlat)

            result[name] = {
                "heliocentric_x_au": x,
                "heliocentric_y_au": y,
                "heliocentric_z_au": z,
            }
        except Exception as exc:
            logger.warning(
                "Failed to compute heliocentric position for %s at %s: %s",
                name,
                dt.isoformat(),
                exc,
            )

    return result


def compute_earth_heliocentric(dt: datetime) -> Optional[Dict[str, float]]:
    """
    Return Earth's heliocentric position computed via ephem.Sun().

    ephem.Sun() without an observer exposes Earth's heliocentric ecliptic
    longitude (hlon), latitude (hlat), and Sun distance (earth_distance) in
    the same coordinate system used for the planets.  These are converted to
    Cartesian XYZ in AU using the same spherical-to-Cartesian formula as
    compute_heliocentric_positions().

    Args:
        dt: UTC datetime for the calculation.  May be timezone-aware or
            timezone-naive; timezone-aware values are converted to UTC before
            being passed to ephem, which requires naive UTC.

    Returns:
        A dict with keys ``heliocentric_x_au``, ``heliocentric_y_au``,
        ``heliocentric_z_au``, and ``distance_au`` (all floats), or None if
        the calculation fails.
    """
    # ephem does not accept timezone-aware datetimes.
    if dt.tzinfo is not None:
        dt = dt.astimezone(timezone.utc).replace(tzinfo=None)

    try:
        body = ephem.Sun()
        # Compute without an observer — populates heliocentric attrs for Earth.
        body.compute(dt)

        hlon = float(body.hlon)             # radians, Earth heliocentric ecliptic longitude
        hlat = float(body.hlat)             # radians, Earth heliocentric ecliptic latitude
        dist = float(body.earth_distance)   # AU, Earth-Sun distance

        cos_lat = math.cos(hlat)
        x = dist * cos_lat * math.cos(hlon)
        y = dist * cos_lat * math.sin(hlon)
        z = dist * math.sin(hlat)

        return {
            "heliocentric_x_au": x,
            "heliocentric_y_au": y,
            "heliocentric_z_au": z,
            "distance_au": dist,
        }
    except Exception as exc:
        logger.warning(
            "Failed to compute Earth heliocentric position at %s: %s",
            dt.isoformat(),
            exc,
        )
        return None
