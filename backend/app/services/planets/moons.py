"""
Moon position calculator for Jupiter and Saturn.

Computes the apparent positions of the Galilean moons (Jupiter) and the
major moons of Saturn using the ephem library.  Offsets are expressed in
parent-planet radii, matching the coordinate convention used by ephem's
moon objects (.x east-positive, .y north-positive as seen from Earth).
"""

import ephem
import logging
from datetime import datetime, timezone
from typing import Dict, List

logger = logging.getLogger(__name__)

# Each entry: (English name, Swedish name, ephem class)
_JUPITER_MOONS = [
    ("Io",       "Io",        ephem.Io),
    ("Europa",   "Europa",    ephem.Europa),
    ("Ganymede", "Ganymedes", ephem.Ganymede),
    ("Callisto", "Callisto",  ephem.Callisto),
]

_SATURN_MOONS = [
    ("Titan",     "Titan",     ephem.Titan),
    ("Rhea",      "Rhea",      ephem.Rhea),
    ("Dione",     "Dione",     ephem.Dione),
    ("Tethys",    "Tethys",    ephem.Tethys),
    ("Enceladus", "Enceladus", ephem.Enceladus),
    ("Mimas",     "Mimas",     ephem.Mimas),
    ("Iapetus",   "Iapetus",   ephem.Iapetus),
]


def _compute_moons(
    dt: datetime,
    moon_specs: List,
    planet_label: str,
) -> List[Dict]:
    """
    Compute positions for a list of moon specs and return plain dicts.

    Each successful moon produces a dict with keys: name, name_sv,
    x_offset, y_offset.  Moons whose .compute() raises are skipped with
    a warning; the remaining moons are still returned.
    """
    moons: List[Dict] = []

    for name, name_sv, moon_class in moon_specs:
        try:
            body = moon_class()
            body.compute(dt)
            moons.append(
                {
                    "name": name,
                    "name_sv": name_sv,
                    # .x is east-positive offset in planet radii (float)
                    # .y is north-positive offset in planet radii (float)
                    "x_offset": float(body.x),
                    "y_offset": float(body.y),
                }
            )
        except Exception as exc:
            logger.warning(
                "Failed to compute moon position for %s (%s) at %s: %s",
                name,
                planet_label,
                dt.isoformat(),
                exc,
            )

    return moons


def compute_moon_positions(dt: datetime) -> Dict[str, List[Dict]]:
    """
    Return apparent moon positions for Jupiter and Saturn.

    Args:
        dt: UTC datetime for the calculation.  May be timezone-aware or
            timezone-naive; timezone-aware values are converted to UTC
            before being passed to ephem, which requires naive UTC.

    Returns:
        A dict with exactly two keys, ``"Jupiter"`` and ``"Saturn"``.
        Each maps to a list of moon dicts, where each dict has:
            ``name``      (str)   — English moon name
            ``name_sv``   (str)   — Swedish moon name
            ``x_offset``  (float) — horizontal offset in planet radii,
                                    positive = east as seen from Earth
            ``y_offset``  (float) — vertical offset in planet radii,
                                    positive = north as seen from Earth
        If all moons for a planet fail, the list for that planet is empty.
    """
    # ephem does not accept timezone-aware datetimes.
    if dt.tzinfo is not None:
        dt = dt.astimezone(timezone.utc).replace(tzinfo=None)

    return {
        "Jupiter": _compute_moons(dt, _JUPITER_MOONS, "Jupiter"),
        "Saturn":  _compute_moons(dt, _SATURN_MOONS,  "Saturn"),
    }
