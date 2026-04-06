"""
Generic, config-driven JPL Horizons provider for artificial-object tracking.

Adding a new tracked object requires only appending a dict to HORIZONS_OBJECTS.
No new classes or functions are needed.

Each registry entry is fetched concurrently (up to 3 simultaneous requests),
parsed from the Horizons CSV ephemeris format, and returned as an ArtificialObject.
"""

import asyncio
import csv
import io
from datetime import datetime, timedelta, timezone
from typing import List, Optional, Tuple

import httpx

from ...models.artificial_object import ArtificialObject
from ...models.planet import azimuth_to_compass
from ...services.cache_service import cache
from ...utils.logger import setup_logger

logger = setup_logger(__name__)

# ---------------------------------------------------------------------------
# Registry — add new objects here; no other code changes required.
# ---------------------------------------------------------------------------

HORIZONS_OBJECTS = [
    {
        "name": "Artemis II",
        "command_id": "-1024",
        "category": "spacecraft",
        "label_sv": "Artemis II",
        "colour": "#00bfff",
        "data_source": "jpl_horizons",
    },
]

# ---------------------------------------------------------------------------
# Internal constants
# ---------------------------------------------------------------------------

_HORIZONS_API_URL = "https://ssd.jpl.nasa.gov/api/horizons.api"
_HORIZONS_FETCH_TIMEOUT_SECONDS = 10
_HORIZONS_CACHE_TTL_SECONDS = 300  # 5 minutes

# Maximum simultaneous requests to the JPL Horizons API.
_HORIZONS_SEMAPHORE = asyncio.Semaphore(3)


# ---------------------------------------------------------------------------
# Fetch
# ---------------------------------------------------------------------------


async def _fetch_horizons_observer(
    command_id: str, lat: float, lon: float
) -> Optional[str]:
    """
    Fetch an OBSERVER ephemeris for *command_id* from the JPL Horizons API.

    Caches the raw response text for _HORIZONS_CACHE_TTL_SECONDS seconds.
    The cache key includes `command_id`, `round(lat, 1)`, and `round(lon, 1)`
    so that observers at different locations receive correctly positioned
    ephemerides.

    Args:
        command_id: Horizons COMMAND parameter (e.g. '-1024' for Artemis II).
        lat: Observer latitude in decimal degrees (north-positive).
        lon: Observer longitude in decimal degrees (east-positive).

    Returns:
        Raw response text from the API, or None on any network/HTTP failure.
    """
    cache_key = f"horizons_{command_id}_{round(lat, 1)}_{round(lon, 1)}"
    cached = await cache.get(cache_key)
    if cached is not None:
        logger.info(f"Horizons cache hit for command_id={command_id}")
        return cached

    now_utc = datetime.now(timezone.utc).replace(tzinfo=None)
    stop_utc = now_utc + timedelta(minutes=2)
    start_str = now_utc.strftime("%Y-%m-%d %H:%M")
    stop_str = stop_utc.strftime("%Y-%m-%d %H:%M")

    # Horizons requires string params wrapped in single quotes.
    params = {
        "COMMAND": f"'{command_id}'",
        "EPHEM_TYPE": "OBSERVER",
        "CENTER": "coord@399",
        "COORD_TYPE": "GEODETIC",
        # Horizons GEODETIC expects east-longitude first, then latitude.
        # Swedish longitudes are already east-positive, so no sign flip needed.
        "SITE_COORD": f"'{lon},{lat},0'",
        "START_TIME": f"'{start_str}'",
        "STOP_TIME": f"'{stop_str}'",
        "STEP_SIZE": "'1 min'",
        # Quantity 4: apparent azimuth + elevation (airmass table).
        "QUANTITIES": "'4'",
        "CSV_FORMAT": "YES",
        "OBJ_DATA": "NO",
        "CAL_FORMAT": "CAL",
    }

    try:
        async with httpx.AsyncClient(timeout=_HORIZONS_FETCH_TIMEOUT_SECONDS) as client:
            response = await client.get(_HORIZONS_API_URL, params=params)
            response.raise_for_status()
            text = response.text
    except Exception as exc:
        logger.warning(
            f"Horizons fetch failed for command_id={command_id} "
            f"lat={lat} lon={lon}: {exc}"
        )
        return None

    await cache.set(cache_key, text, ttl_seconds=_HORIZONS_CACHE_TTL_SECONDS)
    logger.info(f"Horizons response fetched and cached for command_id={command_id}")
    return text


# ---------------------------------------------------------------------------
# Parse
# ---------------------------------------------------------------------------


def _parse_horizons_csv(raw_text: str) -> Optional[Tuple[float, float]]:
    """
    Parse azimuth and elevation from a Horizons OBSERVER CSV ephemeris response.

    The response contains a block delimited by $$SOE / $$EOE markers.  The
    column header line appears just before $$SOE and contains 'Azi_(a-app)'
    and 'Elev_(a-app)'.  Only the first data row is used.

    Returns:
        (azimuth_deg, altitude_deg) tuple, or None on any parse failure.
    """
    soe_marker = "$$SOE"
    eoe_marker = "$$EOE"

    soe_idx = raw_text.find(soe_marker)
    eoe_idx = raw_text.find(eoe_marker)

    if soe_idx == -1 or eoe_idx == -1:
        logger.warning("Horizons CSV missing $$SOE or $$EOE markers")
        return None

    # Extract the data block between the markers (exclusive of the markers).
    data_block = raw_text[soe_idx + len(soe_marker): eoe_idx]

    if not data_block.strip():
        logger.warning("Horizons CSV data block between $$SOE and $$EOE is empty")
        return None

    # Find the header line just before $$SOE — scan backwards through lines.
    pre_soe_text = raw_text[:soe_idx]
    pre_soe_lines = pre_soe_text.splitlines()
    header_line = None
    for line in reversed(pre_soe_lines):
        if "Azi_(a-app)" in line and "Elev_(a-app)" in line:
            header_line = line
            break

    if header_line is None:
        logger.warning("Horizons CSV header line with Azi_(a-app)/Elev_(a-app) not found")
        return None

    # Parse header columns.
    header_reader = csv.reader(io.StringIO(header_line))
    try:
        header_cols = [col.strip() for col in next(header_reader)]
    except StopIteration:
        logger.warning("Horizons CSV header line could not be parsed")
        return None

    try:
        azi_col = header_cols.index("Azi_(a-app)")
        elev_col = header_cols.index("Elev_(a-app)")
    except ValueError:
        logger.warning(
            "Horizons CSV header missing expected column(s): "
            f"Azi_(a-app) or Elev_(a-app) in {header_cols}"
        )
        return None

    # Parse the first data row from the block.
    data_lines = [line for line in data_block.splitlines() if line.strip()]
    if not data_lines:
        logger.warning("Horizons CSV data block has no non-empty lines")
        return None

    data_reader = csv.reader(io.StringIO(data_lines[0]))
    try:
        data_cols = [col.strip() for col in next(data_reader)]
    except StopIteration:
        logger.warning("Horizons CSV first data row could not be parsed")
        return None

    try:
        azimuth_deg = float(data_cols[azi_col])
        altitude_deg = float(data_cols[elev_col])
    except (IndexError, ValueError) as exc:
        logger.warning(f"Horizons CSV float conversion failed: {exc}")
        return None

    # Normalise azimuth to [0, 360) to satisfy the Pydantic model constraint.
    azimuth_deg = azimuth_deg % 360.0

    return (azimuth_deg, altitude_deg)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


async def get_horizons_objects(lat: float, lon: float) -> List[ArtificialObject]:
    """
    Return current sky positions for all objects registered in HORIZONS_OBJECTS.

    Fetches all objects concurrently (max 3 simultaneous Horizons requests).
    Objects that fail to fetch or parse are silently omitted from the result.

    Args:
        lat: Observer latitude in decimal degrees.
        lon: Observer longitude in decimal degrees.

    Returns:
        List of successfully computed ArtificialObject instances (may be empty).
    """

    async def _fetch_one(entry: dict) -> Optional[ArtificialObject]:
        """Fetch and parse a single registry entry, returning None on failure."""
        command_id = entry["command_id"]
        async with _HORIZONS_SEMAPHORE:
            try:
                raw_text = await _fetch_horizons_observer(command_id, lat, lon)
                if raw_text is None:
                    return None

                result = _parse_horizons_csv(raw_text)
                if result is None:
                    return None

                azimuth_deg, altitude_deg = result
                direction = azimuth_to_compass(azimuth_deg)
                is_above_horizon = altitude_deg > 0

                logger.info(
                    f"Horizons position for {entry['name']} ({lat}, {lon}): "
                    f"alt={altitude_deg:.1f}° az={azimuth_deg:.1f}° "
                    f"direction={direction} above_horizon={is_above_horizon}"
                )

                return ArtificialObject(
                    name=entry["name"],
                    category=entry["category"],
                    altitude_deg=round(altitude_deg, 1),
                    azimuth_deg=round(azimuth_deg, 1),
                    direction=direction,
                    is_above_horizon=is_above_horizon,
                    data_source=entry["data_source"],
                    colour=entry.get("colour"),
                    label_sv=entry.get("label_sv"),
                )
            except Exception as exc:
                logger.warning(
                    f"Unexpected error computing Horizons position for "
                    f"{entry.get('name', command_id)}: {exc}"
                )
                return None

    tasks = [_fetch_one(entry) for entry in HORIZONS_OBJECTS]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    objects: List[ArtificialObject] = []
    for entry, result in zip(HORIZONS_OBJECTS, results):
        if isinstance(result, Exception):
            logger.warning(
                f"Horizons gather exception for {entry.get('name')}: {result}"
            )
        elif result is not None:
            objects.append(result)

    logger.info(
        f"Horizons objects computed for ({lat}, {lon}): {len(objects)} returned"
    )
    return objects
