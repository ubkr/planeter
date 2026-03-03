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
        "azimuth_deg": round(azimuth_deg, 1),
    }


def get_moon_angular_separation(moon_az_deg, moon_alt_deg, planet_az_deg, planet_alt_deg) -> float:
    """Angular separation in degrees between moon and planet."""
    az1, alt1 = math.radians(moon_az_deg), math.radians(moon_alt_deg)
    az2, alt2 = math.radians(planet_az_deg), math.radians(planet_alt_deg)
    cos_sep = (math.sin(alt1) * math.sin(alt2) +
               math.cos(alt1) * math.cos(alt2) * math.cos(az1 - az2))
    return math.degrees(math.acos(max(-1.0, min(1.0, cos_sep))))
