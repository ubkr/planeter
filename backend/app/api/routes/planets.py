"""Planet visibility API endpoints."""

import ephem
import math
from datetime import datetime, timezone, timedelta
from typing import List, Optional, Tuple

from fastapi import APIRouter, HTTPException, Query

from ...models.planet import (
    LocationInfo,
    MoonInfo,
    PlanetPosition,
    PlanetsResponse,
    SunInfo,
    WeatherInfo,
)
from ...services.aggregator import get_weather
from ...services.planets.calculator import calculate_planet_positions
from ...services.planets.events import detect_events
from ...services.scoring import apply_scores, score_tonight
from ...utils.logger import setup_logger
from ...utils.moon import calculate_moon_penalty
from ...utils.sun import calculate_sun_penalty, limiting_magnitude

logger = setup_logger(__name__)

router = APIRouter(prefix="/api/v1/planets", tags=["planets"])

# Valid naked-eye planet names (lower-cased for case-insensitive lookup).
_VALID_PLANET_NAMES = {"mercury", "venus", "mars", "jupiter", "saturn"}

# How many hours to sample across the night window for the /tonight endpoint.
_TONIGHT_SAMPLE_INTERVAL_HOURS = 1

# Minimum planet altitude in degrees for "useful" viewing during the dark window.
_MIN_ALTITUDE_DEG = 10

# Sampling interval in minutes for best-viewing-time calculations.
_BEST_TIME_SAMPLE_INTERVAL_MINUTES = 15


def _utc_iso() -> str:
    """Return the current UTC time as an ISO 8601 string."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _build_sun_info(sun_data: dict) -> SunInfo:
    """Construct a SunInfo model from a pre-computed sun data dict."""
    return SunInfo(
        elevation_deg=sun_data["elevation_deg"],
        azimuth_deg=sun_data["azimuth_deg"],
        twilight_phase=sun_data["twilight_phase"],
    )


def _build_moon_info(moon_data: dict) -> MoonInfo:
    """Construct a MoonInfo model from a pre-computed moon data dict."""
    return MoonInfo(
        illumination=moon_data["illumination"],
        elevation_deg=moon_data["elevation_deg"],
        azimuth_deg=moon_data["azimuth_deg"],
    )


def _is_planet_observable(
    sun_alt_deg: float,
    planet_alt_deg: float,
    planet_mag: float,
    min_altitude_deg: float = 5.0,
) -> bool:
    """Check if a planet is observable given current sky conditions.

    Uses the same magnitude-aware limiting magnitude model as the scoring system.
    A planet is observable when:
    - It is above min_altitude_deg (default 5°, avoids horizon extinction)
    - The sun is below the horizon (sun_alt_deg < 0)
    - The planet is brighter than the sky's limiting magnitude at the current
      sun altitude

    Note: the 5° altitude minimum here is intentionally stricter than the
    altitude_deg > 0° gate used by apply_scores in the scoring pipeline.  The
    extra margin avoids extreme horizon extinction, which can make even a bright
    planet undetectable in the lowest degree or two above the horizon.
    """
    if planet_alt_deg <= min_altitude_deg:
        return False
    if sun_alt_deg >= 0:
        return False
    lim_mag = limiting_magnitude(sun_alt_deg)
    return planet_mag < lim_mag


def _compute_next_visible_time(
    planet_name: str, lat: float, lon: float, current_dt: datetime
) -> Optional[str]:
    """
    Return the first upcoming moment (within 24 hours) when the planet is
    observable, using the same magnitude-aware sky-brightness model as the
    scoring system.

    A sample qualifies when _is_planet_observable() returns True, which
    requires the planet to be above 5° altitude, the sun to be below the
    horizon, and the planet to be brighter than the sky's limiting magnitude
    at the current sun altitude (derived from limiting_magnitude()).  This
    allows bright planets such as Venus to qualify during civil or nautical
    twilight, while faint planets like Saturn require a darker sky.

    Samples at _BEST_TIME_SAMPLE_INTERVAL_MINUTES intervals starting from
    current_dt.  Returns an ISO 8601 UTC string on the first qualifying sample,
    or None if no qualifying sample is found within 24 hours.

    Returns None naturally for midnight-sun conditions and for planets that
    stay below the horizon or are always outshone by the sky.

    Args:
        planet_name: English title-cased planet name (e.g. "Mars").
        lat:         Observer latitude in decimal degrees.
        lon:         Observer longitude in decimal degrees.
        current_dt:  Search start (timezone-aware UTC datetime).
    """
    planet_classes = {
        "Mercury": ephem.Mercury,
        "Venus": ephem.Venus,
        "Mars": ephem.Mars,
        "Jupiter": ephem.Jupiter,
        "Saturn": ephem.Saturn,
    }

    planet_cls = planet_classes.get(planet_name)
    if planet_cls is None:
        return None

    observer = ephem.Observer()
    observer.lat = str(lat)
    observer.lon = str(lon)
    observer.pressure = 0

    # Strip timezone for ephem (it works with naive UTC datetimes).
    start_naive = current_dt.replace(tzinfo=None)
    interval = timedelta(minutes=_BEST_TIME_SAMPLE_INTERVAL_MINUTES)
    end_naive = start_naive + timedelta(hours=24)

    fmt = "%Y-%m-%dT%H:%M:%SZ"
    sample = start_naive
    while sample <= end_naive:
        observer.date = sample

        sun = ephem.Sun()
        sun.compute(observer)
        sun_alt_deg = math.degrees(float(sun.alt))

        # Quick-skip daytime samples — no need to compute planet position.
        if sun_alt_deg >= 0:
            sample += interval
            continue

        body = planet_cls()
        body.compute(observer)
        planet_alt_deg = math.degrees(float(body.alt))
        planet_mag = float(body.mag)

        # Guard against invalid magnitudes returned by ephem.  ephem can return
        # nonsensical magnitudes for planets near inferior conjunction or at
        # extreme orbital geometry; magnitudes above 6.0 are beyond naked-eye
        # visibility anyway, so skip those samples.
        if math.isnan(planet_mag) or planet_mag > 6.0:
            sample += interval
            continue

        if _is_planet_observable(sun_alt_deg, planet_alt_deg, planet_mag):
            return sample.strftime(fmt)

        sample += interval

    return None


def _compute_tonight_window(lat: float, lon: float) -> tuple:
    """
    Compute tonight's darkness window as (start_utc, end_utc).

    Returns a tuple of (start, end) datetime objects (timezone-naive UTC).

    Edge cases:
      - ephem.AlwaysUpError: midnight sun — returns (None, None) indicating no
        dark window at all.
      - ephem.NeverUpError: polar night — uses a 24-hour window starting now.
    """
    now_naive = datetime.now(timezone.utc).replace(tzinfo=None)

    observer = ephem.Observer()
    observer.lat = str(lat)
    observer.lon = str(lon)
    observer.date = now_naive
    observer.pressure = 0

    # Use standard −0°34′ horizon (default) so that sunset/sunrise match civil
    # expectations rather than the geometric 0° used for planet positions.
    observer.horizon = "-0:34"

    try:
        sunset_ephem = observer.next_setting(ephem.Sun())
        start = ephem.Date(sunset_ephem).datetime()
    except ephem.AlwaysUpError:
        # Midnight sun — no dark window tonight.
        logger.info(f"Midnight sun at ({lat}, {lon}); no tonight window.")
        return None, None
    except ephem.NeverUpError:
        # Polar night — sun never rises; treat the whole 24h as a valid window.
        logger.info(f"Polar night at ({lat}, {lon}); using 24h window.")
        start = now_naive

    # Reset observer date to compute sunrise from the start of the window.
    observer.date = start
    try:
        sunrise_ephem = observer.next_rising(ephem.Sun())
        end = ephem.Date(sunrise_ephem).datetime()
    except ephem.AlwaysUpError:
        # Sun immediately rises again (degenerate case at extreme latitudes in
        # summer with a very short dip below horizon).  Extend to 24h.
        end = start + timedelta(hours=24)
    except ephem.NeverUpError:
        # Polar night: sun never rises — end the window 24h after start.
        end = start + timedelta(hours=24)

    return start, end


def _compute_nautical_dark_window(
    lat: float, lon: float
) -> Tuple[Optional[datetime], Optional[datetime]]:
    """
    Compute the nautical-darkness window as (start_utc, end_utc).

    Nautical darkness is the period when the sun is below -12° altitude.
    Returns a tuple of (start, end) timezone-naive UTC datetime objects,
    following the same conventions as _compute_tonight_window().

    Edge cases:
      - ephem.AlwaysUpError: midnight sun / sun never dips below -12° —
        returns (None, None) to signal no dark window.
      - ephem.NeverUpError: polar night / sun always below -12° —
        returns a 24-hour window starting from now.
    """
    now_naive = datetime.now(timezone.utc).replace(tzinfo=None)

    observer = ephem.Observer()
    observer.lat = str(lat)
    observer.lon = str(lon)
    observer.date = now_naive
    observer.pressure = 0
    # Nautical twilight threshold: sun 12° below horizon.
    observer.horizon = "-12"

    try:
        sunset_ephem = observer.next_setting(ephem.Sun(), use_center=True)
        start = ephem.Date(sunset_ephem).datetime()
    except ephem.AlwaysUpError:
        # Sun never dips below -12° — no nautical dark window (midnight sun).
        logger.info(
            f"Sun never below -12° at ({lat}, {lon}); no nautical dark window."
        )
        return None, None
    except ephem.NeverUpError:
        # Sun always below -12° (deep polar night); treat 24h from now as valid.
        logger.info(
            f"Sun always below -12° at ({lat}, {lon}); using 24h dark window."
        )
        start = now_naive

    # Reset observer to the start of darkness to find when it ends.
    observer.date = start
    try:
        sunrise_ephem = observer.next_rising(ephem.Sun(), use_center=True)
        end = ephem.Date(sunrise_ephem).datetime()
    except ephem.AlwaysUpError:
        # Degenerate case: sun pops back up almost immediately.
        end = start + timedelta(hours=24)
    except ephem.NeverUpError:
        # Polar night: sun never climbs above -12° — dark for a full day.
        end = start + timedelta(hours=24)

    return start, end


def _compute_best_viewing_times(
    planets: List[PlanetPosition],
    lat: float,
    lon: float,
    dark_start: datetime,
    dark_end: datetime,
) -> None:
    """
    Populate best_time, dark_rise_time, and dark_set_time on each PlanetPosition.

    Samples planet altitudes at _BEST_TIME_SAMPLE_INTERVAL_MINUTES intervals
    across the nautical dark window [dark_start, dark_end].  For each planet,
    qualifying sample times are those where altitude exceeds _MIN_ALTITUDE_DEG.

    If qualifying samples exist:
      - dark_rise_time: first qualifying sample (ISO 8601 UTC string)
      - dark_set_time:  last qualifying sample (ISO 8601 UTC string)
      - best_time:      sample with the highest altitude (ISO 8601 UTC string)

    If no qualifying samples exist, all three fields remain None.

    Mutates the PlanetPosition objects in-place.  dark_start and dark_end must
    be timezone-naive UTC datetimes (as returned by _compute_nautical_dark_window).

    Args:
        planets:    List of PlanetPosition objects to annotate.
        lat:        Observer latitude in decimal degrees.
        lon:        Observer longitude in decimal degrees.
        dark_start: Start of the nautical dark window (naive UTC).
        dark_end:   End of the nautical dark window (naive UTC).
    """
    interval = timedelta(minutes=_BEST_TIME_SAMPLE_INTERVAL_MINUTES)

    # Build the list of sample datetimes.
    sample_times: List[datetime] = []
    current = dark_start
    while current <= dark_end:
        sample_times.append(current)
        current += interval

    if not sample_times:
        return

    # Build a mapping from planet name to index so we can update in-place.
    planet_index = {p.name: i for i, p in enumerate(planets)}

    # Per-planet accumulators: list of (altitude_deg, sample_datetime).
    planet_samples: dict = {p.name: [] for p in planets}

    # Ephem observer for altitude lookups — pressure=0 for geometric altitude,
    # matching the convention used in calculate_planet_positions.
    observer = ephem.Observer()
    observer.lat = str(lat)
    observer.lon = str(lon)
    observer.pressure = 0

    planet_classes = {
        "Mercury": ephem.Mercury,
        "Venus": ephem.Venus,
        "Mars": ephem.Mars,
        "Jupiter": ephem.Jupiter,
        "Saturn": ephem.Saturn,
    }

    for sample_dt in sample_times:
        observer.date = sample_dt
        for name, planet_cls in planet_classes.items():
            if name not in planet_index:
                # Planet not present in the input list; skip.
                continue
            body = planet_cls()
            body.compute(observer)
            alt_deg = math.degrees(float(body.alt))
            if alt_deg > _MIN_ALTITUDE_DEG:
                planet_samples[name].append((alt_deg, sample_dt))

    # Annotate each PlanetPosition with the computed window times.
    for planet in planets:
        qualifying = planet_samples.get(planet.name, [])
        if not qualifying:
            # No qualifying samples — leave best_time/dark_rise_time/dark_set_time as None.
            continue

        dark_rise_dt = qualifying[0][1]
        dark_set_dt = qualifying[-1][1]
        best_dt = max(qualifying, key=lambda t: t[0])[1]

        fmt = "%Y-%m-%dT%H:%M:%SZ"
        planet.dark_rise_time = dark_rise_dt.strftime(fmt)
        planet.dark_set_time = dark_set_dt.strftime(fmt)
        planet.best_time = best_dt.strftime(fmt)


def _sample_times(start: datetime, end: datetime, interval_hours: int) -> List[datetime]:
    """
    Return a list of equally-spaced UTC datetime samples between start and end.

    Always includes start and end in the list.  If the window is shorter than
    interval_hours, only start and end are returned.
    """
    samples = [start]
    current = start + timedelta(hours=interval_hours)
    while current < end:
        samples.append(current)
        current += timedelta(hours=interval_hours)
    if samples[-1] != end:
        samples.append(end)
    return samples


def _pick_best_positions(
    samples: List[List[PlanetPosition]],
) -> List[PlanetPosition]:
    """
    For each planet, pick the sample time that gives the highest altitude.

    Returns a list of five PlanetPosition objects (one per planet), each taken
    from the sample time at which that planet reaches its peak altitude.  This
    ensures the /tonight endpoint reflects the best viewing opportunity across
    the night, rather than the position at a single fixed time.

    Args:
        samples: A list of per-sample planet lists, e.g.
                 [[mercury_t0, venus_t0, ...], [mercury_t1, venus_t1, ...], ...]

    Returns:
        One PlanetPosition per planet, chosen from whichever sample has the
        highest altitude_deg for that planet.
    """
    if not samples:
        return []

    # Number of planets is constant (always 5).
    n_planets = len(samples[0])
    best: List[PlanetPosition] = list(samples[0])  # initialise with first sample

    for sample in samples[1:]:
        for i in range(n_planets):
            if sample[i].altitude_deg > best[i].altitude_deg:
                best[i] = sample[i]

    return best


def _filter_above_horizon(events):
    """Remove events confirmed below the horizon (altitude_deg < 0).

    Events with altitude_deg = None are retained as a conservative pass-through.
    NaN altitudes fail the >= 0 check and are treated as below-horizon and filtered out.
    """
    return [e for e in events if e.altitude_deg is None or e.altitude_deg >= 0]


@router.get("/visible", response_model=PlanetsResponse)
async def get_visible_planets(
    lat: float = Query(..., ge=-90, le=90, description="Latitude in decimal degrees"),
    lon: float = Query(..., ge=-180, le=180, description="Longitude in decimal degrees"),
) -> PlanetsResponse:
    """
    Return all five naked-eye planets scored for current conditions.

    Fetches live planet positions, weather, and sun/moon state for the given
    coordinates, then computes per-planet visibility scores.  All five planets
    are returned regardless of whether they are above the horizon.
    """
    logger.info(f"GET /visible lat={lat} lon={lon}")

    now_utc = datetime.now(timezone.utc)
    timestamp = now_utc.strftime("%Y-%m-%dT%H:%M:%SZ")

    planets = calculate_planet_positions(lat, lon)
    weather_data = await get_weather(lat, lon)

    sun_data = calculate_sun_penalty(lat, lon)
    moon_data = calculate_moon_penalty(lat, lon)

    planets = apply_scores(planets, sun_data, moon_data, weather_data.cloud_cover)

    # Compute next visible time for non-visible planets.
    for planet in planets:
        if not planet.is_visible:
            planet.next_visible_time = _compute_next_visible_time(
                planet.name, lat, lon, now_utc
            )

    # Compute best viewing times within the nautical dark window.
    dark_start, dark_end = _compute_nautical_dark_window(lat, lon)
    if dark_start is not None:
        _compute_best_viewing_times(planets, lat, lon, dark_start, dark_end)

    try:
        events = detect_events(lat, lon, now_utc - timedelta(days=1), now_utc + timedelta(days=2))
    except Exception as exc:
        logger.warning(f"detect_events failed for ({lat}, {lon}): {exc}")
        events = []

    events = _filter_above_horizon(events)

    sun_info = _build_sun_info(sun_data)
    moon_info = _build_moon_info(moon_data)

    logger.info(
        f"Visibility computed for ({lat}, {lon}): "
        f"sun={sun_info.twilight_phase}, cloud_cover={weather_data.cloud_cover}%"
    )

    return PlanetsResponse(
        timestamp=timestamp,
        location=LocationInfo(lat=lat, lon=lon),
        sun=sun_info,
        moon=moon_info,
        weather=WeatherInfo(
            cloud_cover=weather_data.cloud_cover,
            source=weather_data.source,
        ),
        planets=planets,
        events=events,
    )


@router.get("/tonight", response_model=PlanetsResponse)
async def get_tonight_planets(
    lat: float = Query(..., ge=-90, le=90, description="Latitude in decimal degrees"),
    lon: float = Query(..., ge=-180, le=180, description="Longitude in decimal degrees"),
) -> PlanetsResponse:
    """
    Return all five naked-eye planets scored for tonight's best visibility.

    Samples planet positions at hourly intervals across tonight's darkness window
    (sunset to sunrise).  For each planet the sample with the highest altitude is
    selected, so the response reflects the best observable position during the
    night rather than the current moment.

    Edge cases handled:
      - Midnight sun (ephem.AlwaysUpError): no dark window; all planets returned
        with score 0 and is_visible=False.
      - Polar night (ephem.NeverUpError): 24-hour window used.
    """
    logger.info(f"GET /tonight lat={lat} lon={lon}")

    timestamp = _utc_iso()
    weather_data = await get_weather(lat, lon)

    window_start, window_end = _compute_tonight_window(lat, lon)

    if window_start is None:
        # Midnight sun — no dark window.  Return all planets with score 0.
        # apply_scores' hard-zero guards produce score 0 for all planets when
        # the sun is up, so this naturally yields the correct result without
        # duplicating scoring logic here.
        logger.info(f"No tonight window for ({lat}, {lon}); returning zero scores.")
        sun_data = calculate_sun_penalty(lat, lon)
        moon_data = calculate_moon_penalty(lat, lon)
        planets = calculate_planet_positions(lat, lon)
        planets = apply_scores(planets, sun_data, moon_data, weather_data.cloud_cover)
        tonight = 0
    else:
        sample_times = _sample_times(window_start, window_end, _TONIGHT_SAMPLE_INTERVAL_HOURS)

        all_samples: List[List[PlanetPosition]] = []
        for sample_dt in sample_times:
            positions = calculate_planet_positions(lat, lon, dt=sample_dt)
            all_samples.append(positions)

        planets = _pick_best_positions(all_samples)

        # Score using the midpoint of the night for sun/moon context.
        mid_dt = window_start + (window_end - window_start) / 2

        sun_data = calculate_sun_penalty(lat, lon, mid_dt)
        moon_data = calculate_moon_penalty(lat, lon, mid_dt)

        planets = apply_scores(planets, sun_data, moon_data, weather_data.cloud_cover)
        tonight = score_tonight(planets)

        # next_visible_time is intentionally not computed here.
        # The /tonight endpoint projects best positions across tonight's window,
        # not the current moment — computing "next visible time" relative to now
        # would be misleading.  The frontend renders planet cards exclusively
        # from the /visible endpoint (fetchVisiblePlanets in api.js), so this
        # field is never read from /tonight responses and the UI is unaffected.

        # Compute best viewing times within the nautical dark window.
        dark_start, dark_end = _compute_nautical_dark_window(lat, lon)
        if dark_start is not None:
            _compute_best_viewing_times(planets, lat, lon, dark_start, dark_end)

        logger.info(
            f"Tonight scored for ({lat}, {lon}): tonight_score={tonight}, "
            f"window={window_start.isoformat()}Z to {window_end.isoformat()}Z, "
            f"samples={len(sample_times)}"
        )

    now_utc = datetime.now(timezone.utc)
    try:
        events = detect_events(lat, lon, now_utc - timedelta(days=1), now_utc + timedelta(days=2))
    except Exception as exc:
        logger.warning(f"detect_events failed for ({lat}, {lon}): {exc}")
        events = []

    events = _filter_above_horizon(events)

    # Use the pre-computed sun/moon data so metadata reflects the same moment
    # used for scoring, not the wall-clock time of the HTTP request.
    sun_info = _build_sun_info(sun_data)
    moon_info = _build_moon_info(moon_data)

    return PlanetsResponse(
        timestamp=timestamp,
        location=LocationInfo(lat=lat, lon=lon),
        sun=sun_info,
        moon=moon_info,
        weather=WeatherInfo(
            cloud_cover=weather_data.cloud_cover,
            source=weather_data.source,
        ),
        planets=planets,
        tonight_score=tonight,
        events=events,
    )


# WARNING: This wildcard route MUST remain the last route in this file.
# Any fixed-path route registered after it (e.g. "/foo") would be silently
# shadowed by this pattern and never reachable.
@router.get("/{name}", response_model=PlanetPosition)
async def get_planet(
    name: str,
    lat: float = Query(..., ge=-90, le=90, description="Latitude in decimal degrees"),
    lon: float = Query(..., ge=-180, le=180, description="Longitude in decimal degrees"),
) -> PlanetPosition:
    """
    Return current position and score for a single named planet.

    The planet name is case-insensitive.  Valid names: mercury, venus, mars,
    jupiter, saturn.  Returns HTTP 404 for unrecognised names.
    """
    name_lower = name.lower()

    if name_lower not in _VALID_PLANET_NAMES:
        raise HTTPException(
            status_code=404,
            detail=f"Planet '{name}' not found. Valid names: mercury, venus, mars, jupiter, saturn.",
        )

    logger.info(f"GET /{name} lat={lat} lon={lon}")

    planets = calculate_planet_positions(lat, lon)
    weather_data = await get_weather(lat, lon)

    sun_data = calculate_sun_penalty(lat, lon)
    moon_data = calculate_moon_penalty(lat, lon)

    planets = apply_scores(planets, sun_data, moon_data, weather_data.cloud_cover)

    # Planet names from the calculator are title-cased English names.
    for planet in planets:
        if planet.name.lower() == name_lower:
            logger.info(
                f"Returning {planet.name}: altitude={planet.altitude_deg}°, "
                f"score={planet.visibility_score}"
            )
            return planet

    # This branch is only reachable if calculate_planet_positions omits a
    # planet that is in _VALID_PLANET_NAMES — which should never happen.
    raise HTTPException(
        status_code=500,
        detail=f"Planet '{name}' is valid but was not returned by the calculator.",
    )
