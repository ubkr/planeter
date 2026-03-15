"""Astronomical events API endpoint."""

from datetime import datetime, timezone, timedelta, date

from fastapi import APIRouter, HTTPException, Query

from ...models.planet import EventsResponse, LocationInfo
from ...services.planets.events import detect_events
from ...services.cache_service import cache
from ...utils.logger import setup_logger

logger = setup_logger(__name__)

router = APIRouter(prefix="/api/v1/events", tags=["events"])

# Cache TTL: 1 hour in seconds.
_CACHE_TTL_SECONDS = 3600

# Look-ahead window for event detection.
_LOOKAHEAD_DAYS = 60


def _cache_key(lat: float, lon: float) -> str:
    """Return a 1-hour cache key rounded to 0.1° and keyed on today's date."""
    rounded_lat = round(lat, 1)
    rounded_lon = round(lon, 1)
    today = date.today().isoformat()
    return f"events:{rounded_lat}:{rounded_lon}:{today}"


@router.get("", response_model=EventsResponse)
async def get_events(
    lat: float = Query(..., ge=-90, le=90, description="Latitude in decimal degrees"),
    lon: float = Query(..., ge=-180, le=180, description="Longitude in decimal degrees"),
) -> EventsResponse:
    """
    Return upcoming astronomical events for the next 60 days.

    Detects conjunctions, oppositions, Mercury elongations, planet alignments,
    Venus brilliancy peaks, and Moon occultations.  Events are sorted by date
    and deduplicated.  Results are cached for 1 hour per 0.1°-rounded location.
    """
    logger.info(f"GET /api/v1/events lat={lat} lon={lon}")

    key = _cache_key(lat, lon)
    cached = await cache.get(key)
    if cached is not None:
        logger.info(f"Cache hit for events at ({lat}, {lon})")
        return cached

    now_utc = datetime.now(timezone.utc)
    timestamp = now_utc.strftime("%Y-%m-%dT%H:%M:%SZ")
    end_utc = now_utc + timedelta(days=_LOOKAHEAD_DAYS)

    try:
        events = detect_events(lat, lon, now_utc, end_utc)
    except Exception as exc:
        logger.error(f"Event detection failed for ({lat}, {lon}): {exc}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Unexpected error during event detection.",
        )

    logger.info(
        f"Events detected for ({lat}, {lon}): {len(events)} events "
        f"over the next {_LOOKAHEAD_DAYS} days"
    )

    response = EventsResponse(
        timestamp=timestamp,
        location=LocationInfo(lat=lat, lon=lon),
        events=events,
    )

    await cache.set(key, response, ttl_seconds=_CACHE_TTL_SECONDS)

    return response
