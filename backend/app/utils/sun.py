import ephem
import math
from datetime import datetime, timezone


def calculate_sun_penalty(lat: float, lon: float, dt: datetime = None) -> dict:
    """
    Calculate sun/twilight penalty contribution to planet visibility score.

    Uses ephem to compute sun elevation at the given location and UTC time.

    Penalty is stepped by twilight phase:
    - daylight (elevation >= 0): 50 pts
    - civil_twilight (-6 <= elevation < 0): 40 pts
    - nautical_twilight (-12 <= elevation < -6): 20 pts
    - astronomical_twilight (-18 <= elevation < -12): 8 pts
    - darkness (elevation < -18): 0 pts

    Returns a dict with:
        elevation_deg   – sun elevation in degrees
        twilight_phase  – twilight phase label
        penalty_pts     – points deducted from total score (0–50)
    """
    if dt is None:
        dt = datetime.now(timezone.utc).replace(tzinfo=None)
    else:
        # Ensure UTC naive — ephem does not accept tzinfo-aware datetimes
        if dt.tzinfo is not None:
            dt = dt.astimezone(timezone.utc).replace(tzinfo=None)

    observer = ephem.Observer()
    observer.lat = str(lat)
    observer.lon = str(lon)
    observer.date = dt
    observer.pressure = 0

    sun = ephem.Sun()
    sun.compute(observer)

    elevation_rad = float(sun.alt)
    elevation_deg = math.degrees(elevation_rad)

    if elevation_deg >= 0:
        twilight_phase = "daylight"
        penalty_pts = 50.0
    elif elevation_deg >= -6:
        twilight_phase = "civil_twilight"
        penalty_pts = 40.0
    elif elevation_deg >= -12:
        twilight_phase = "nautical_twilight"
        penalty_pts = 20.0
    elif elevation_deg >= -18:
        twilight_phase = "astronomical_twilight"
        penalty_pts = 8.0
    else:
        twilight_phase = "darkness"
        penalty_pts = 0.0

    return {
        "elevation_deg": round(elevation_deg, 1),
        "twilight_phase": twilight_phase,
        "penalty_pts": penalty_pts,
    }
