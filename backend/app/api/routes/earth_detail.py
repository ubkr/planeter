"""Earth/Moon detail endpoint with time-slider support (±7 days from now)."""

from datetime import datetime, timedelta, timezone
from typing import List, Optional

from fastapi import APIRouter, Query

from ...models.earth_detail import EarthDetailObjectInfo, EarthDetailResponse
from ...models.planet import EarthSystemInfo, EarthSystemMoon, LocationInfo
from ...services.artificial_objects.horizons_provider import compute_horizons_earth_detail
from ...services.planets.earth_system import compute_earth_system
from ...utils.logger import setup_logger

logger = setup_logger(__name__)

router = APIRouter(prefix="/api/v1", tags=["earth-detail"])


@router.get("/earth-detail", response_model=EarthDetailResponse)
async def get_earth_detail(
    lat: float = Query(..., ge=-90, le=90, description="Latitude in decimal degrees"),
    lon: float = Query(..., ge=-180, le=180, description="Longitude in decimal degrees"),
    offset_hours: int = Query(
        0,
        ge=-168,
        le=168,
        description=(
            "Hour offset from now (negative = past, positive = future). "
            "Valid range: -168 to +168 (±7 days). "
            "FastAPI returns HTTP 422 for out-of-range values."
        ),
    ),
) -> EarthDetailResponse:
    """
    Return Moon and tracked spacecraft positions for the Earth/Moon detail view
    at an arbitrary time offset from now.

    The *offset_hours* parameter drives the time slider on the frontend:
    0 means right now, negative values go into the past, positive into the future.
    The valid range (±168 h = ±7 days) matches the frontend slider bounds.

    Earth-system (Moon) data is computed via ephem; spacecraft positions are
    fetched from JPL Horizons.  Both calls are fault-tolerant: a failure in
    either produces a null/empty field rather than an error response.
    """
    target_dt = datetime.now(timezone.utc) + timedelta(hours=offset_hours)

    logger.info(
        f"GET /api/v1/earth-detail lat={lat} lon={lon} "
        f"offset_hours={offset_hours} target_dt={target_dt.isoformat()}"
    )

    # --- Earth-system (Moon) --------------------------------------------------
    earth_system: Optional[EarthSystemInfo] = None
    try:
        earth_system_dict = compute_earth_system(target_dt)
        if earth_system_dict is not None:
            earth_system = EarthSystemInfo(
                moon=EarthSystemMoon(**earth_system_dict["moon"])
            )
    except Exception as exc:
        logger.warning(
            f"compute_earth_system failed for earth-detail "
            f"({lat}, {lon}) offset={offset_hours}h: {exc}"
        )

    # --- Horizons spacecraft positions ----------------------------------------
    objects: List[EarthDetailObjectInfo] = []
    try:
        raw_objects = await compute_horizons_earth_detail(target_dt)
        objects = [EarthDetailObjectInfo(**obj) for obj in raw_objects]
    except Exception as exc:
        logger.warning(
            f"compute_horizons_earth_detail failed for earth-detail "
            f"({lat}, {lon}) offset={offset_hours}h: {exc}"
        )

    logger.info(
        f"earth-detail response: moon={'ok' if earth_system else 'null'} "
        f"objects={len(objects)} target={target_dt.isoformat()}"
    )

    return EarthDetailResponse(
        timestamp=target_dt.isoformat(),
        location=LocationInfo(lat=lat, lon=lon),
        earth_system=earth_system,
        objects=objects,
    )
