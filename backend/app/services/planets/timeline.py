"""
Altitude timeline calculator for the five naked-eye planets, the Sun, and the Moon.

Returns 96 altitude samples per body, spaced 15 minutes apart (24 hours total),
starting from the given UTC datetime.
"""

import ephem
import math
from datetime import datetime, timedelta, timezone
from typing import List, Optional, Dict, Any


# Bodies in the required output order.
_BODY_MAP = {
    "Mercury": ephem.Mercury,
    "Venus": ephem.Venus,
    "Mars": ephem.Mars,
    "Jupiter": ephem.Jupiter,
    "Saturn": ephem.Saturn,
    "Sun": ephem.Sun,
    "Moon": ephem.Moon,
}

_STEP_MINUTES = 15
_NUM_STEPS = 96  # 96 * 15 min = 24 hours


def compute_altitude_timeline(
    lat: float,
    lon: float,
    dt: datetime = None,
) -> List[Dict[str, Any]]:
    """
    Compute altitude over time for the five naked-eye planets, the Sun, and the Moon.

    Samples altitude every 15 minutes for 96 steps (24 hours) starting from dt.
    Atmospheric refraction is disabled (pressure=0) for raw geometric altitude,
    matching the pattern used in calculator.py.

    Args:
        lat: Latitude in decimal degrees (positive = North).
        lon: Longitude in decimal degrees (positive = East).
        dt:  UTC datetime for the start of the timeline. Defaults to now (UTC).
             Timezone-aware datetimes are converted to naive UTC before use,
             because ephem does not accept tzinfo-aware datetimes.

    Returns:
        A list of 7 dicts, one per body, in Mercury → Venus → Mars → Jupiter →
        Saturn → Sun → Moon order.  Each dict has the shape:
            {
                "name": "Mercury",
                "samples": [
                    {"time_offset_minutes": 0, "altitude_deg": 12.3},
                    ...  # 96 entries total
                ]
            }
        altitude_deg is rounded to 1 decimal place and is None if the computed
        value is NaN.
    """
    if dt is None:
        dt = datetime.now(timezone.utc)

    # ephem does not accept timezone-aware datetimes; strip tzinfo after
    # normalising to UTC — same pattern as calculator.py.
    if dt.tzinfo is not None:
        dt = dt.astimezone(timezone.utc).replace(tzinfo=None)

    observer = ephem.Observer()
    observer.lat = str(lat)
    observer.lon = str(lon)
    observer.pressure = 0  # disable atmospheric refraction (geometric altitude)

    series: List[Dict[str, Any]] = []

    for name, body_class in _BODY_MAP.items():
        body = body_class()  # one instance per body; reused across all 96 sample steps
        samples: List[Dict[str, Any]] = []

        for i in range(_NUM_STEPS):
            offset_minutes = i * _STEP_MINUTES
            step_dt = dt + timedelta(minutes=offset_minutes)

            # ephem.Date accepts a naive Python datetime directly; wrapping in
            # ephem.Date is explicit and safe for computed offsets.
            observer.date = ephem.Date(step_dt)

            body.compute(observer)

            alt: Optional[float] = round(math.degrees(float(body.alt)), 1)
            if math.isnan(alt):
                alt = None

            samples.append({
                "time_offset_minutes": offset_minutes,
                "altitude_deg": alt,
            })

        series.append({"name": name, "samples": samples})

    return series
