"""
ISS and artificial-object position tracker.

Aggregates position data from multiple sources:
- CelesTrak TLE data for satellites (ISS)
- JPL Horizons ephemeris for cislunar spacecraft (Artemis II, future missions)

Fetches from all sources concurrently and merges the results.  If one source
fails, objects from other sources are still returned.
"""

import asyncio
import math
from datetime import datetime, timezone
from typing import List, Optional

import ephem
import httpx

from ...models.artificial_object import ArtificialObject
from ...models.planet import azimuth_to_compass
from ...services.cache_service import cache
from ...utils.logger import setup_logger
from .horizons_provider import get_horizons_objects

logger = setup_logger(__name__)

# CelesTrak TLE endpoint for ISS (ZARYA), NORAD catalogue number 25544.
_ISS_TLE_URL = "https://celestrak.org/NORAD/elements/gp.php?CATNR=25544&FORMAT=TLE"

# Cache key and TTL for the raw TLE text.
_TLE_CACHE_KEY = "tle_iss"
_TLE_CACHE_TTL_SECONDS = 7200  # 2 hours

# Fallback name used when CelesTrak returns only 2 lines (no name line).
_ISS_NAME = "ISS (ZARYA)"

# Timeout for the TLE HTTP fetch in seconds.
_FETCH_TIMEOUT_SECONDS = 5


async def _fetch_tle_text() -> Optional[str]:
    """
    Fetch raw TLE text from CelesTrak, using the cache when available.

    Returns the raw response text (stripped), or None on any network/HTTP failure.
    Cache key: 'tle_iss'; TTL: 7200 seconds.
    """
    cached = await cache.get(_TLE_CACHE_KEY)
    if cached is not None:
        logger.info("TLE cache hit for ISS")
        return cached

    try:
        async with httpx.AsyncClient(timeout=_FETCH_TIMEOUT_SECONDS) as client:
            response = await client.get(_ISS_TLE_URL)
            response.raise_for_status()
            text = response.text.strip()
    except Exception as exc:
        logger.warning(f"Failed to fetch ISS TLE from CelesTrak: {exc}")
        return None

    await cache.set(_TLE_CACHE_KEY, text, ttl_seconds=_TLE_CACHE_TTL_SECONDS)
    logger.info("ISS TLE fetched and cached")
    return text


def _parse_tle_lines(raw_text: str) -> Optional[tuple]:
    """
    Parse raw TLE text into (name, line1, line2).

    CelesTrak may return 2 or 3 lines:
    - 3 lines: lines[0] = name, lines[1] = TLE line 1, lines[2] = TLE line 2
    - 2 lines: lines[0] = TLE line 1, lines[1] = TLE line 2 — prepend _ISS_NAME

    Returns a (name, line1, line2) tuple, or None if the format is unrecognised.
    """
    lines = [line.strip() for line in raw_text.splitlines() if line.strip()]

    if len(lines) == 3:
        return lines[0], lines[1], lines[2]
    elif len(lines) == 2:
        return _ISS_NAME, lines[0], lines[1]
    else:
        logger.warning(f"Unexpected TLE line count: {len(lines)} — cannot parse")
        return None


async def get_iss_position(lat: float, lon: float) -> Optional[ArtificialObject]:
    """
    Return the current position of the ISS for the given observer coordinates.

    Fetches (or retrieves from cache) the ISS TLE, builds an ephem observer,
    computes the current topocentric position, and returns an ArtificialObject.

    Args:
        lat: Observer latitude in decimal degrees.
        lon: Observer longitude in decimal degrees.

    Returns:
        ArtificialObject with current ISS position, or None on any failure.
    """
    raw_text = await _fetch_tle_text()
    if raw_text is None:
        return None

    parsed = _parse_tle_lines(raw_text)
    if parsed is None:
        return None

    name, line1, line2 = parsed

    try:
        iss = ephem.readtle(name, line1, line2)
    except Exception as exc:
        logger.warning(f"ephem.readtle failed for ISS TLE: {exc}")
        return None

    try:
        observer = ephem.Observer()
        # ephem.Observer.lat and .lon accept string degrees (e.g. '59.3') or
        # numeric radians.  The existing calculator.py uses str(lat) throughout,
        # so we follow the same convention here.
        observer.lat = str(lat)
        observer.lon = str(lon)
        # Use current UTC time; strip tzinfo because ephem works with naive UTC.
        observer.date = datetime.now(timezone.utc).replace(tzinfo=None)
        # Disable atmospheric refraction for consistent geometric altitude,
        # matching the convention used in calculate_planet_positions.
        observer.pressure = 0

        iss.compute(observer)

        altitude_deg = float(iss.alt) * 180.0 / math.pi
        azimuth_deg = float(iss.az) * 180.0 / math.pi

        direction = azimuth_to_compass(azimuth_deg)
        is_above_horizon = altitude_deg > 0

    except Exception as exc:
        logger.warning(f"ephem ISS position compute failed for ({lat}, {lon}): {exc}")
        return None

    logger.info(
        f"ISS position for ({lat}, {lon}): alt={altitude_deg:.1f}° az={azimuth_deg:.1f}° "
        f"direction={direction} above_horizon={is_above_horizon}"
    )

    return ArtificialObject(
        name=name,
        category="satellite",
        altitude_deg=round(altitude_deg, 1),
        azimuth_deg=round(azimuth_deg % 360.0, 1) % 360,
        direction=direction,
        is_above_horizon=is_above_horizon,
        data_source="celestrak_tle",
        colour="#ffffff",
        label_sv="ISS",
    )


async def get_all_artificial_objects(lat: float, lon: float) -> List[ArtificialObject]:
    """
    Return the current positions of all tracked artificial objects.

    Fetches from CelesTrak TLE (ISS) and JPL Horizons (Artemis II and future
    cislunar spacecraft) concurrently.  If one source raises or returns nothing,
    the results from the other source are still returned.

    Args:
        lat: Observer latitude in decimal degrees.
        lon: Observer longitude in decimal degrees.

    Returns:
        List of ArtificialObject instances for objects that were successfully
        computed.  Objects that failed to compute are silently omitted.
    """
    iss_result, horizons_result = await asyncio.gather(
        get_iss_position(lat, lon),
        get_horizons_objects(lat, lon),
        return_exceptions=True,
    )

    objects: List[ArtificialObject] = []

    if isinstance(iss_result, Exception):
        logger.warning(f"ISS fetch raised an exception: {iss_result}")
    elif iss_result is not None:
        objects.append(iss_result)

    if isinstance(horizons_result, Exception):
        logger.warning(f"Horizons fetch raised an exception: {horizons_result}")
    elif horizons_result is not None:
        objects.extend(horizons_result)

    logger.info(f"Artificial objects computed for ({lat}, {lon}): {len(objects)} returned")
    return objects
