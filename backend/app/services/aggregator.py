"""Weather aggregation with Met.no primary source and Open-Meteo fallback"""
from datetime import datetime, timezone

from ..models.weather import WeatherData
from ..utils.logger import setup_logger
from ..config import settings
from .cache_service import cache
from .weather.metno_client import MetNoClient
from .weather.openmeteo_client import OpenMeteoClient

logger = setup_logger(__name__)

_metno = MetNoClient()
_openmeteo = OpenMeteoClient()

# Fallback TTL is shorter so the app retries sooner after a full outage
_FALLBACK_TTL_SECONDS = 300


def _fallback_weather() -> WeatherData:
    """Return a neutral WeatherData object used when all sources are unavailable."""
    return WeatherData(
        source="fallback",
        cloud_cover=50.0,
        precipitation_mm=0.0,
        last_updated=datetime.now(timezone.utc),
    )


async def get_weather(lat: float, lon: float) -> WeatherData:
    """
    Fetch weather data for the given coordinates.

    Tries Met.no first, falls back to Open-Meteo, and if both fail returns a
    neutral WeatherData with cloud_cover=50 so the rest of the app degrades
    gracefully rather than crashing.

    Results are cached in memory with a TTL from settings.cache_ttl_weather
    (default 1800 s).  The fallback result uses a shorter TTL so the app
    retries a live source sooner after a transient outage.

    Args:
        lat: Latitude in decimal degrees.
        lon: Longitude in decimal degrees.

    Returns:
        WeatherData instance from whichever source succeeded (or fallback).
    """
    cache_key = f"weather:{lat:.4f}:{lon:.4f}"

    cached = await cache.get(cache_key)
    if cached is not None:
        logger.info(
            f"Weather cache hit for ({lat:.4f}, {lon:.4f}), source={cached.source}"
        )
        return cached

    # --- Try Met.no ---
    try:
        data = await _metno.fetch_data(lat, lon)
        logger.info(
            f"Weather fetched from Met.no for ({lat:.4f}, {lon:.4f}), "
            f"cloud_cover={data.cloud_cover}%"
        )
        await cache.set(cache_key, data, ttl_seconds=settings.cache_ttl_weather)
        return data
    except Exception as exc:
        logger.warning(
            f"Met.no failed for ({lat:.4f}, {lon:.4f}), trying Open-Meteo. "
            f"Reason: {exc}"
        )

    # --- Try Open-Meteo ---
    try:
        data = await _openmeteo.fetch_data(lat, lon)
        logger.info(
            f"Weather fetched from Open-Meteo for ({lat:.4f}, {lon:.4f}), "
            f"cloud_cover={data.cloud_cover}%"
        )
        await cache.set(cache_key, data, ttl_seconds=settings.cache_ttl_weather)
        return data
    except Exception as exc:
        logger.warning(
            f"Open-Meteo failed for ({lat:.4f}, {lon:.4f}), using fallback. "
            f"Reason: {exc}"
        )

    # --- Both sources failed: return neutral fallback ---
    fallback = _fallback_weather()
    logger.warning(
        f"All weather sources failed for ({lat:.4f}, {lon:.4f}). "
        f"Returning fallback (cloud_cover={fallback.cloud_cover}%)"
    )
    await cache.set(cache_key, fallback, ttl_seconds=_FALLBACK_TTL_SECONDS)
    return fallback
