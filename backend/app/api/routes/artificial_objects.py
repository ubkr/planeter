"""Artificial-object (satellite) tracking API endpoints."""

from datetime import datetime, timezone

from fastapi import APIRouter, Query

from ...models.artificial_object import ArtificialObjectsResponse
from ...models.planet import LocationInfo
from ...services.artificial_objects.tracker import get_all_artificial_objects
from ...utils.logger import setup_logger

logger = setup_logger(__name__)

router = APIRouter(prefix="/api/v1/artificial-objects", tags=["artificial-objects"])


@router.get("", response_model=ArtificialObjectsResponse)
async def get_artificial_objects(
    lat: float = Query(..., ge=-90, le=90, description="Latitude in decimal degrees"),
    lon: float = Query(..., ge=-180, le=180, description="Longitude in decimal degrees"),
) -> ArtificialObjectsResponse:
    """
    Return current positions of tracked artificial objects (satellites).

    Fetches live TLE data (cached for 2 hours) and computes topocentric position
    for the ISS at the given observer coordinates.  Additional objects will be
    added in a future phase.
    """
    logger.info(f"GET /api/v1/artificial-objects lat={lat} lon={lon}")

    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    objects = await get_all_artificial_objects(lat, lon)

    return ArtificialObjectsResponse(
        timestamp=timestamp,
        location=LocationInfo(lat=lat, lon=lon, name=None),
        objects=objects,
    )
