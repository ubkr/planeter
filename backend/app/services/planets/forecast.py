"""
Forecast module: find the next good observation window for a naked-eye planet.

Scans up to 180 nights from a given start date to find the first night
where the planet clears the quality threshold for comfortable naked-eye
viewing.
"""

import ephem
import math
from datetime import datetime, timedelta, timezone
from typing import Optional, Tuple

# ── Constants ────────────────────────────────────────────────────────────────

# Sampling resolution inside the dark window.
_SAMPLE_INTERVAL_MINUTES = 30

# Minimum planet altitude for a night to qualify.
_MIN_ALTITUDE_DEG = 15.0

# Quality-score thresholds.  Inner planets (Mercury/Venus) benefit even from
# modest apparitions so a lower bar is used.
_THRESHOLD_INNER = 35
_THRESHOLD_OUTER = 50

_INNER_PLANETS = {"Mercury", "Venus"}

# ephem planet class map — title-cased name keys.
_PLANET_CLASSES = {
    "Mercury": ephem.Mercury,
    "Venus": ephem.Venus,
    "Mars": ephem.Mars,
    "Jupiter": ephem.Jupiter,
    "Saturn": ephem.Saturn,
}

# ISO 8601 UTC format used throughout the codebase.
_ISO_FMT = "%Y-%m-%dT%H:%M:%SZ"


# ── Dark-window helper ────────────────────────────────────────────────────────

def _compute_dark_window_for_night(
    lat: float,
    lon: float,
    night_dt: datetime,
) -> Tuple[Optional[datetime], Optional[datetime]]:
    """
    Compute the nautical-darkness window (sun below -12°) for the night that
    *begins* at the UTC midnight closest to night_dt.

    Mirrors the logic in planets.py::_compute_nautical_dark_window() but
    accepts an arbitrary reference datetime rather than always using now().

    Returns (start, end) as timezone-naive UTC datetimes, or (None, None) if
    the sun never dips below -12° that night (midnight sun / polar summer).
    """
    # Anchor to the UTC date of night_dt so we search for sunset from noon UTC
    # on that calendar day — this reliably lands before the evening crossing.
    noon_utc = night_dt.replace(hour=12, minute=0, second=0, microsecond=0)
    if noon_utc.tzinfo is not None:
        noon_utc = noon_utc.replace(tzinfo=None)

    observer = ephem.Observer()
    observer.lat = str(lat)
    observer.lon = str(lon)
    observer.date = noon_utc
    observer.pressure = 0
    observer.horizon = "-12"

    try:
        sunset_ephem = observer.next_setting(ephem.Sun(), use_center=True)
        start = ephem.Date(sunset_ephem).datetime()
    except ephem.AlwaysUpError:
        # Sun never dips below -12° — no nautical dark window (midnight sun).
        return None, None
    except ephem.NeverUpError:
        # Sun always below -12° (deep polar night); treat 24 h from noon as valid.
        start = noon_utc

    # Advance the observer to the start of darkness to find when it ends.
    observer.date = start
    try:
        sunrise_ephem = observer.next_rising(ephem.Sun(), use_center=True)
        end = ephem.Date(sunrise_ephem).datetime()
    except ephem.AlwaysUpError:
        # Degenerate: sun pops back above -12° almost immediately.
        end = start + timedelta(hours=24)
    except ephem.NeverUpError:
        # Polar night: sun never climbs above -12° — dark for a full day.
        end = start + timedelta(hours=24)

    return start, end


# ── Quality-score computation ─────────────────────────────────────────────────

def _quality_score(
    altitude_deg: float,
    magnitude: float,
    moon_sep_deg: float,
    moon_illumination: float,
) -> int:
    """
    Compute an integer quality score using the canonical component weights from
    ARCHITECTURE.md.  The theoretical maximum is 100, but because cloud cover is
    assumed to be 0% (clear sky — see comment below), the variable components
    (altitude + magnitude + moon penalty) span 0–65 pts; the fixed cloud
    contribution of 35 pts raises the baseline so that the combined range is 0–100.

    Components:
      - Altitude  (0–40 pts): linear ramp from 0 pts at 0° to 40 pts at 45°;
                              clamped at 40 pts for altitudes above 45°.
      - Magnitude (0–25 pts): brighter (lower magnitude) = more points; matches
                              the formula used in scoring.py.
      - Cloud     (35 pts):   forecast context has no cloud data, so clear sky
                              (0% cloud cover) is assumed → always 35 pts.
      - Moon      (0 to −10 pts): penalty when the moon is bright and close;
                              mirrors the moon proximity penalty in scoring.py.

    Note: the numeric thresholds (_THRESHOLD_INNER / _THRESHOLD_OUTER) were chosen
    against this scale.  The clear-sky assumption contributes a fixed +35 pts, so
    the effective variable range is 0–65 pts (altitude + magnitude + moon penalty).
    """
    # Altitude component: 0 pts at horizon, 40 pts at 45°, clamped above 45°.
    altitude_component = min(40.0, altitude_deg * 40.0 / 45.0)
    altitude_component = max(0.0, altitude_component)

    # Magnitude component: matches scoring.py.
    # −4.5 → 25 pts; +1.0 → 10 pts; linear interpolation; clamp to [0, 25].
    magnitude_component = 25.0 + (magnitude - (-4.5)) * (10.0 - 25.0) / (1.0 - (-4.5))
    magnitude_component = max(0.0, min(25.0, magnitude_component))

    # Cloud component: no cloud data is available for future forecast nights, so
    # assume clear sky (0% cloud cover) → full 35 pts.
    cloud_component = 35.0

    # Moon proximity penalty: applied only when moon is bright (>0.5) and close
    # (<15°) to the planet.  Mirrors the formula in scoring.py.
    if moon_sep_deg < 15.0 and moon_illumination > 0.5:
        moon_penalty = -10.0 * (1.0 - moon_sep_deg / 15.0) * moon_illumination
        moon_penalty = max(-10.0, min(0.0, moon_penalty))
    else:
        moon_penalty = 0.0

    total = altitude_component + magnitude_component + cloud_component + moon_penalty
    return int(round(max(0.0, min(100.0, total))))


# ── Peak-finder for a single night ───────────────────────────────────────────

def _find_peak_in_window(
    planet_cls,
    observer: ephem.Observer,
    dark_start: datetime,
    dark_end: datetime,
) -> Optional[Tuple[datetime, float, float]]:
    """
    Sample the planet altitude at _SAMPLE_INTERVAL_MINUTES intervals across
    [dark_start, dark_end] and return the sample with the highest altitude.

    Returns (peak_dt, peak_altitude_deg, magnitude) or None if no valid
    sample exists (all magnitudes are NaN/undefined).  The caller is
    responsible for checking that peak_altitude_deg meets the minimum
    altitude threshold; this function does not filter by altitude.

    observer must already have lat/lon/pressure set; its .date is mutated
    during iteration.
    """
    interval = timedelta(minutes=_SAMPLE_INTERVAL_MINUTES)
    best_alt: Optional[float] = None
    best_dt: Optional[datetime] = None
    best_mag: Optional[float] = None

    sample = dark_start
    while sample <= dark_end:
        observer.date = sample

        body = planet_cls()
        body.compute(observer)
        alt_deg = math.degrees(float(body.alt))
        mag = float(body.mag)

        # Guard against NaN or nonsensical magnitudes.
        if math.isnan(mag):
            sample += interval
            continue

        if best_alt is None or alt_deg > best_alt:
            best_alt = alt_deg
            best_dt = sample
            best_mag = mag

        sample += interval

    if best_dt is None or best_alt is None or best_mag is None:
        return None

    return best_dt, best_alt, best_mag


# ── Main exported function ────────────────────────────────────────────────────

def compute_next_good_observation(
    planet_name: str,
    lat: float,
    lon: float,
    start_dt: datetime,
) -> Optional[dict]:
    """
    Scan up to 180 nights from start_dt to find the first night where the
    named planet meets good-observation quality criteria.

    Args:
        planet_name: Title-cased English planet name, e.g. "Mars".
        lat:         Observer latitude in decimal degrees.
        lon:         Observer longitude in decimal degrees.
        start_dt:    Search start (timezone-aware or naive UTC datetime).

    Returns:
        A dict with keys matching NextGoodObservation fields:
          date, start_time, end_time, peak_time, peak_altitude_deg,
          magnitude, quality_score
        or None if no qualifying night is found within 180 days.
    """
    planet_cls = _PLANET_CLASSES.get(planet_name)
    if planet_cls is None:
        return None

    threshold = _THRESHOLD_INNER if planet_name in _INNER_PLANETS else _THRESHOLD_OUTER

    # Normalise to a timezone-naive UTC datetime for ephem compatibility.
    if getattr(start_dt, "tzinfo", None) is not None:
        start_naive = start_dt.replace(tzinfo=None)
    else:
        start_naive = start_dt

    # Shared observer — lat/lon/pressure are fixed; only .date changes.
    observer = ephem.Observer()
    observer.lat = str(lat)
    observer.lon = str(lon)
    observer.pressure = 0

    for day_offset in range(180):
        night_dt = start_naive + timedelta(days=day_offset)

        dark_start, dark_end = _compute_dark_window_for_night(lat, lon, night_dt)

        if dark_start is None:
            # Midnight sun — no usable dark window; skip.
            continue

        # Find the planet's peak altitude within this dark window.
        peak = _find_peak_in_window(planet_cls, observer, dark_start, dark_end)
        if peak is None:
            continue

        peak_dt, peak_alt_deg, peak_mag = peak

        # Apply altitude gate before computing moon metrics.
        if peak_alt_deg < _MIN_ALTITUDE_DEG:
            continue

        # Compute moon separation and illumination at the peak moment.
        # Reset observer.date explicitly: _find_peak_in_window iterates over
        # many sample times and leaves observer.date in an unspecified state
        # after returning.
        observer.date = peak_dt

        moon = ephem.Moon()
        moon.compute(observer)
        moon_illumination = float(moon.phase) / 100.0  # ephem.Moon.phase is 0–100

        planet_body = planet_cls()
        planet_body.compute(observer)

        # Angular separation between moon and planet (ephem returns radians).
        moon_sep_deg = math.degrees(
            ephem.separation(
                (moon.az, moon.alt),
                (planet_body.az, planet_body.alt),
            )
        )

        score = _quality_score(peak_alt_deg, peak_mag, moon_sep_deg, moon_illumination)

        if score < threshold:
            continue

        # This night qualifies — build the return dict.
        # Use the calendar date of dark_start as the "night date" (the evening
        # side of the window, which may roll past midnight UTC).
        night_date_str = dark_start.strftime("%Y-%m-%d")

        return {
            "date": night_date_str,
            "start_time": dark_start.strftime(_ISO_FMT),
            "end_time": dark_end.strftime(_ISO_FMT),
            "peak_time": peak_dt.strftime(_ISO_FMT),
            "peak_altitude_deg": round(peak_alt_deg, 1),
            "magnitude": round(peak_mag, 2),
            "quality_score": score,
        }

    return None
