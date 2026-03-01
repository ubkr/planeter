"""Planet visibility API endpoints."""

import ephem
from datetime import datetime, timezone, timedelta
from typing import List

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
from ...services.scoring import apply_scores, score_tonight
from ...utils.logger import setup_logger
from ...utils.moon import calculate_moon_penalty
from ...utils.sun import calculate_sun_penalty

logger = setup_logger(__name__)

router = APIRouter(prefix="/api/v1/planets", tags=["planets"])

# Valid naked-eye planet names (lower-cased for case-insensitive lookup).
_VALID_PLANET_NAMES = {"mercury", "venus", "mars", "jupiter", "saturn"}

# How many hours to sample across the night window for the /tonight endpoint.
_TONIGHT_SAMPLE_INTERVAL_HOURS = 1


def _utc_iso() -> str:
    """Return the current UTC time as an ISO 8601 string."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _build_sun_info(lat: float, lon: float, dt: datetime = None) -> SunInfo:
    """Call calculate_sun_penalty and convert its dict to a SunInfo model."""
    data = calculate_sun_penalty(lat, lon, dt)
    return SunInfo(
        elevation_deg=data["elevation_deg"],
        twilight_phase=data["twilight_phase"],
    )


def _build_moon_info(lat: float, lon: float, dt: datetime = None) -> MoonInfo:
    """Call calculate_moon_penalty and convert its dict to a MoonInfo model."""
    data = calculate_moon_penalty(lat, lon, dt)
    return MoonInfo(
        illumination=data["illumination"],
        elevation_deg=data["elevation_deg"],
        azimuth_deg=data["azimuth_deg"],
    )


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

    planets = apply_scores(planets, lat, lon, weather_data.cloud_cover)

    sun_info = _build_sun_info(lat, lon)
    moon_info = _build_moon_info(lat, lon)

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
        mid_dt = datetime.now(timezone.utc)
        planets = calculate_planet_positions(lat, lon)
        planets = apply_scores(planets, lat, lon, weather_data.cloud_cover)
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

        planets = apply_scores(planets, lat, lon, weather_data.cloud_cover, dt=mid_dt)
        tonight = score_tonight(planets)

        logger.info(
            f"Tonight scored for ({lat}, {lon}): tonight_score={tonight}, "
            f"window={window_start.isoformat()}Z to {window_end.isoformat()}Z, "
            f"samples={len(sample_times)}"
        )

    # Use mid_dt so sun/moon metadata reflects the same moment used for scoring,
    # not the wall-clock time of the HTTP request.
    sun_info = _build_sun_info(lat, lon, dt=mid_dt)
    moon_info = _build_moon_info(lat, lon, dt=mid_dt)

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
    planets = apply_scores(planets, lat, lon, weather_data.cloud_cover)

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
