import ephem
import math
from datetime import datetime, timezone
from typing import List, Tuple


# ---------------------------------------------------------------------------
# Anchor tables for piecewise linear interpolation
# ---------------------------------------------------------------------------

# Each table is a list of (sun_altitude_deg, value) pairs sorted from highest
# altitude (least negative) to lowest.  The interpolation helper reads them in
# this order so the first matching interval is used.

# Empirical limiting magnitude visible at zenith vs sun altitude (Schaefer 1993).
# < -18° the sky is fully dark; the clamp value (6.5) is returned directly.
_LIM_MAG_ANCHORS: List[Tuple[float, float]] = [
    (0.0,   -5.0),
    (-2.0,  -4.0),
    (-4.0,  -3.0),
    (-6.0,  -1.0),
    (-12.0,  3.5),
    (-15.0,  5.0),
    (-18.0,  6.5),
]

# Sun penalty contribution to visibility score vs sun altitude.
# Above 0° the sky is daytime; below -18° the penalty drops to zero.
_PENALTY_ANCHORS: List[Tuple[float, float]] = [
    (0.0,   50.0),
    (-6.0,  38.0),
    (-12.0, 16.0),
    (-18.0,  4.0),
]


def _piecewise_linear(
    alt: float,
    anchors: List[Tuple[float, float]],
    clamp_high: float,
    clamp_low: float,
) -> float:
    """
    Interpolate `alt` against a table of (altitude, value) anchor pairs.

    Anchors must be sorted from highest altitude to lowest (descending).
    Values at the upper boundary are clamped to `clamp_high`.
    Values at the lower boundary are clamped to `clamp_low`.
    Between adjacent anchors, the result is linearly interpolated.
    """
    # Upper clamp: alt at or above the first anchor
    if alt >= anchors[0][0]:
        return clamp_high

    # Lower clamp: alt below the last anchor
    if alt < anchors[-1][0]:
        return clamp_low

    # Find the interval [anchors[i], anchors[i-1]) that contains alt
    for i in range(1, len(anchors)):
        alt_lo, val_lo = anchors[i]
        alt_hi, val_hi = anchors[i - 1]
        if alt >= alt_lo:
            # Linear interpolation within this segment
            span = alt_hi - alt_lo          # always > 0 (anchors descend)
            frac = (alt - alt_lo) / span    # 0.0 at alt_lo, 1.0 at alt_hi
            return val_lo + frac * (val_hi - val_lo)

    # Unreachable given the clamp checks above, but satisfies type checker
    return clamp_low


def limiting_magnitude(sun_altitude_deg: float) -> float:
    """
    Return the faintest naked-eye magnitude visible at zenith for the given
    sun altitude in degrees.

    Based on Schaefer (1993) empirical anchor points:
      >=  0 deg  → -5.0  (only Venus near peak brilliance is visible)
      −18 deg    → +6.5
      <  -18 deg → +6.5 (full dark sky; clamped)
    Between anchors the value is linearly interpolated.
    """
    return _piecewise_linear(
        sun_altitude_deg,
        _LIM_MAG_ANCHORS,
        clamp_high=-5.0,
        clamp_low=6.5,
    )


def calculate_sun_penalty(lat: float, lon: float, dt: datetime = None) -> dict:
    """
    Calculate sun/twilight penalty contribution to planet visibility score.

    Uses ephem to compute sun elevation at the given location and UTC time.

    Penalty is interpolated continuously by twilight phase:
    - daylight   (elevation >= 0):   50 pts (clamped)
    - civil      (-6 <= elev < 0):   interpolated 38–50 pts
    - nautical   (-12 <= elev < -6): interpolated 16–38 pts
    - astro      (-18 <= elev < -12): interpolated 4–16 pts
    - darkness   (elevation < -18):  0 pts (clamped)

    The `twilight_phase` string labels reflect the traditional band boundaries
    and are used for display only.

    Returns a dict with:
        elevation_deg      – sun elevation in degrees
        azimuth_deg        – sun azimuth in degrees, [0, 360)
        twilight_phase     – twilight phase label
        penalty_pts        – continuous score deduction (0.0–50.0)
        limiting_magnitude – faintest zenith magnitude visible at this altitude
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

    # Twilight phase label — band boundaries are unchanged (display only)
    if elevation_deg >= 0:
        twilight_phase = "daylight"
    elif elevation_deg >= -6:
        twilight_phase = "civil_twilight"
    elif elevation_deg >= -12:
        twilight_phase = "nautical_twilight"
    elif elevation_deg >= -18:
        twilight_phase = "astronomical_twilight"
    else:
        twilight_phase = "darkness"

    # Continuous penalty: linearly interpolated, clamped to [0.0, 50.0]
    penalty_pts = _piecewise_linear(
        elevation_deg,
        _PENALTY_ANCHORS,
        clamp_high=50.0,
        clamp_low=0.0,
    )

    # sun.az is the azimuth in radians; normalise to [0, 360)
    azimuth_deg = math.degrees(float(sun.az))

    return {
        "elevation_deg": round(elevation_deg, 1),
        # % 360.0 must come after round() — floating-point rounding can produce
        # exactly 360.0, which would violate the SunInfo lt=360 Pydantic constraint.
        "azimuth_deg": round(azimuth_deg, 1) % 360.0,
        "twilight_phase": twilight_phase,
        "penalty_pts": penalty_pts,
        "limiting_magnitude": limiting_magnitude(elevation_deg),
    }
