import ephem
import math
from datetime import datetime, timezone


def calculate_moon_penalty(lat: float, lon: float, dt: datetime = None) -> dict:
    """
    Calculate moon phase penalty contribution to planet visibility score.

    Uses the ephem library (Jean Meeus algorithm) to compute moon illumination
    and elevation at the given location and time.

    Returns a dict with:
        illumination  – fraction 0.0–1.0 (0 = new moon, 1 = full moon)
        elevation_deg – degrees above (+) or below (-) horizon
        azimuth_deg   – azimuth in degrees [0, 360)
    """
    if dt is None:
        dt = datetime.now(timezone.utc).replace(tzinfo=None)
    else:
        # Ensure UTC naive — ephem does not accept tzinfo-aware datetimes
        if dt.tzinfo is not None:
            dt = dt.astimezone(timezone.utc).replace(tzinfo=None)

    observer = ephem.Observer()
    # ephem requires strings for lat/lon; floats would be interpreted as radians
    observer.lat = str(lat)
    observer.lon = str(lon)
    observer.date = dt
    # Disable atmospheric refraction correction for consistency
    observer.pressure = 0

    moon = ephem.Moon()
    moon.compute(observer)

    # moon.phase is illuminated percentage 0.0–100.0
    illumination = moon.phase / 100.0

    # moon.alt is the altitude (elevation) in radians
    elevation_rad = float(moon.alt)
    elevation_deg = math.degrees(elevation_rad)

    # moon.az is the azimuth in radians; normalise to [0, 360)
    azimuth_deg = math.degrees(float(moon.az)) % 360.0

    return {
        "illumination": round(illumination, 3),
        "elevation_deg": round(elevation_deg, 1),
        # % 360.0 must come after round() — floating-point rounding can produce
        # exactly 360.0, which would violate the MoonInfo lt=360 Pydantic constraint.
        "azimuth_deg": round(azimuth_deg, 1) % 360.0,
    }


def compute_moon_rise_set_times(lat: float, lon: float, dt: datetime = None) -> dict:
    """
    Compute today's and next upcoming moonrise/moonset times for the given location.

    Uses refraction-corrected civil horizon (-0:34) so times match what an observer
    on the ground would expect.

    Args:
        lat: Latitude in decimal degrees.
        lon: Longitude in decimal degrees.
        dt:  Reference UTC datetime (naive). Defaults to datetime.utcnow().

    Returns a dict with keys:
        today_rise_time  – UTC ISO 8601 string for moonrise starting from midnight of dt's date, or None
        today_set_time   – UTC ISO 8601 string for moonset starting from midnight of dt's date, or None
        next_rise_time   – UTC ISO 8601 string for next moonrise from dt, or None
        next_set_time    – UTC ISO 8601 string for next moonset from dt, or None
    """
    if dt is None:
        dt = datetime.utcnow()

    # Ensure naive UTC — ephem does not accept tzinfo-aware datetimes.
    if dt.tzinfo is not None:
        dt = dt.astimezone(timezone.utc).replace(tzinfo=None)

    observer = ephem.Observer()
    # ephem requires strings for lat/lon; floats would be interpreted as radians
    observer.lat = str(lat)
    observer.lon = str(lon)
    # Refraction-corrected civil horizon — standard convention for rise/set times
    observer.pressure = 0
    observer.horizon = "-0:34"

    def _format(ephem_date) -> str:
        return ephem.Date(ephem_date).datetime().strftime("%Y-%m-%dT%H:%M:%SZ")

    # --- Today's rise and set: search forward from midnight UTC of dt's date ---
    midnight = datetime(dt.year, dt.month, dt.day, 0, 0, 0)
    observer.date = midnight

    today_rise_time = None
    today_set_time = None
    try:
        today_rise_time = _format(observer.next_rising(ephem.Moon()))
    except (ephem.AlwaysUpError, ephem.NeverUpError, ephem.CircumpolarError):
        pass

    observer.date = midnight
    try:
        today_set_time = _format(observer.next_setting(ephem.Moon()))
    except (ephem.AlwaysUpError, ephem.NeverUpError, ephem.CircumpolarError):
        pass

    # --- Next upcoming rise and set: search forward from dt itself ---
    observer.date = dt

    next_rise_time = None
    next_set_time = None
    try:
        next_rise_time = _format(observer.next_rising(ephem.Moon()))
    except (ephem.AlwaysUpError, ephem.NeverUpError, ephem.CircumpolarError):
        pass

    observer.date = dt
    try:
        next_set_time = _format(observer.next_setting(ephem.Moon()))
    except (ephem.AlwaysUpError, ephem.NeverUpError, ephem.CircumpolarError):
        pass

    return {
        "today_rise_time": today_rise_time,
        "today_set_time": today_set_time,
        "next_rise_time": next_rise_time,
        "next_set_time": next_set_time,
    }


def get_moon_angular_separation(moon_az_deg, moon_alt_deg, planet_az_deg, planet_alt_deg) -> float:
    """Angular separation in degrees between moon and planet."""
    az1, alt1 = math.radians(moon_az_deg), math.radians(moon_alt_deg)
    az2, alt2 = math.radians(planet_az_deg), math.radians(planet_alt_deg)
    cos_sep = (math.sin(alt1) * math.sin(alt2) +
               math.cos(alt1) * math.cos(alt2) * math.cos(az1 - az2))
    return math.degrees(math.acos(max(-1.0, min(1.0, cos_sep))))
