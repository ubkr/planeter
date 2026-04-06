"""
Generic, config-driven JPL Horizons provider for artificial-object tracking.

Adding a new tracked object requires only appending a dict to HORIZONS_OBJECTS.
No new classes or functions are needed.

Each registry entry is fetched concurrently (up to 3 simultaneous requests),
parsed from the Horizons CSV ephemeris format, and returned as an ArtificialObject.

If a registry entry has ``earth_detail: True``, a second Horizons VECTORS call
(geocentric, CENTER='500@399') is made to populate the ``earth_detail_position``
field.  Failure of the VECTORS call never prevents the sky-map position from
being returned.
"""

import asyncio
import csv
import io
import math
import re
from datetime import datetime, timedelta, timezone
from typing import List, Optional, Tuple

import httpx

from ...models.artificial_object import ArtificialObject, EarthDetailPosition
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
        # earth_detail: True triggers a geocentric VECTORS call so the object
        # can be rendered on the Earth/Moon detail diagram.
        "earth_detail": True,
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

# Unit-conversion constants for VECTORS → Earth-detail position.
_AU_TO_KM = 149_597_870.7  # kilometres per astronomical unit
_EARTH_RADIUS_KM = 6_371.0  # km


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

    if "$$SOE" not in text:
        logger.debug(
            "Horizons response for command_id=%s contains no ephemeris data; not caching",
            command_id,
        )
        return text  # still return for the caller/parser to handle

    await cache.set(cache_key, text, ttl_seconds=_HORIZONS_CACHE_TTL_SECONDS)
    logger.info(f"Horizons response fetched and cached for command_id={command_id}")
    return text


async def _fetch_horizons_vectors(command_id: str) -> Optional[str]:
    """
    Fetch a geocentric VECTORS ephemeris for *command_id* from JPL Horizons.

    Uses CENTER='500@399' (Earth body-centre) and REF_PLANE='FRAME' /
    REF_SYSTEM='J2000' so that the returned X/Y axes align with the
    coordinate convention used in earth_system.py:
        X — toward vernal equinox
        Y — 90 ° east in the equatorial plane

    Caches the raw response text for _HORIZONS_CACHE_TTL_SECONDS seconds.
    The cache key is keyed only on command_id because the geocentric position
    does not depend on the ground observer location.

    Returns:
        Raw response text, or None on any network/HTTP failure.
    """
    cache_key = f"horizons_vectors_{command_id}"
    cached = await cache.get(cache_key)
    if cached is not None:
        logger.info(f"Horizons VECTORS cache hit for command_id={command_id}")
        return cached

    now_utc = datetime.now(timezone.utc).replace(tzinfo=None)
    stop_utc = now_utc + timedelta(minutes=1)
    start_str = now_utc.strftime("%Y-%m-%d %H:%M")
    stop_str = stop_utc.strftime("%Y-%m-%d %H:%M")

    # Quoting convention for Horizons API parameters:
    #   - Free-string values (dates, coordinates, object IDs, unit specifiers,
    #     table selectors) must be wrapped in single quotes, e.g. "'AU-D'".
    #   - Keyword-style enum values (REF_PLANE, REF_SYSTEM) are bare identifiers
    #     in the Horizons API and must NOT be wrapped in single quotes.
    params = {
        "COMMAND": f"'{command_id}'",
        "EPHEM_TYPE": "VECTORS",
        "CENTER": "'500@399'",
        "START_TIME": f"'{start_str}'",
        "STOP_TIME": f"'{stop_str}'",
        "STEP_SIZE": "'1 min'",
        "OUT_UNITS": "'AU-D'",
        "REF_PLANE": "FRAME",
        "REF_SYSTEM": "J2000",
        "VEC_TABLE": "'2'",
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
            f"Horizons VECTORS fetch failed for command_id={command_id}: {exc}"
        )
        return None

    if "$$SOE" not in text:
        logger.debug(
            "Horizons VECTORS response for command_id=%s contains no ephemeris data",
            command_id,
        )
        return text  # return so the caller/parser can log the failure detail

    await cache.set(cache_key, text, ttl_seconds=_HORIZONS_CACHE_TTL_SECONDS)
    logger.info(
        f"Horizons VECTORS response fetched and cached for command_id={command_id}"
    )
    return text


# ---------------------------------------------------------------------------
# Parse
# ---------------------------------------------------------------------------


def _parse_horizons_vectors(raw_text: str) -> Optional[Tuple[float, float, float]]:
    """
    Parse X, Y, Z position components (in AU) from a Horizons VECTORS response.

    Horizons CSV VECTORS format (VEC_TABLE=2) includes a $$SOE/$$EOE block.
    With CSV_FORMAT=YES the columns are:
        JDTDB, Calendar Date (TDB), X, Y, Z, VX, VY, VZ

    The header line just before $$SOE contains 'X' and 'Y' and 'Z' column names.

    Returns:
        (x_au, y_au, z_au) tuple, or None on any parse failure or if any value
        is 'n.a.' (which Horizons returns when data is unavailable).
    """
    soe_marker = "$$SOE"
    eoe_marker = "$$EOE"

    soe_idx = raw_text.find(soe_marker)
    eoe_idx = raw_text.find(eoe_marker)

    if soe_idx == -1 or eoe_idx == -1:
        logger.warning("Horizons VECTORS response missing $$SOE or $$EOE markers")
        return None

    data_block = raw_text[soe_idx + len(soe_marker): eoe_idx]
    if not data_block.strip():
        logger.warning("Horizons VECTORS data block is empty")
        return None

    # Find the header line just before $$SOE that contains X, Y, Z columns.
    pre_soe_lines = raw_text[:soe_idx].splitlines()
    header_line = None
    for line in reversed(pre_soe_lines):
        # The CSV header for VECTORS contains column names like
        # "JDTDB, Calendar Date (TDB), X, Y, Z, VX, VY, VZ,"
        if re.search(r"\bX\b", line) and re.search(r"\bY\b", line) and re.search(r"\bZ\b", line):
            header_line = line
            break

    if header_line is None:
        logger.warning("Horizons VECTORS CSV header line with X/Y/Z columns not found")
        return None

    header_reader = csv.reader(io.StringIO(header_line))
    try:
        header_cols = [col.strip() for col in next(header_reader)]
    except StopIteration:
        logger.warning("Horizons VECTORS CSV header line could not be parsed")
        return None

    try:
        x_col = header_cols.index("X")
        y_col = header_cols.index("Y")
        z_col = header_cols.index("Z")
    except ValueError:
        logger.warning(
            f"Horizons VECTORS CSV header missing X/Y/Z column(s): {header_cols}"
        )
        return None

    data_lines = [line for line in data_block.splitlines() if line.strip()]
    if not data_lines:
        logger.warning("Horizons VECTORS data block has no non-empty lines")
        return None

    data_reader = csv.reader(io.StringIO(data_lines[0]))
    try:
        data_cols = [col.strip() for col in next(data_reader)]
    except StopIteration:
        logger.warning("Horizons VECTORS CSV first data row could not be parsed")
        return None

    # Check for Horizons 'n.a.' sentinel — returned when data is unavailable.
    for col_idx in (x_col, y_col, z_col):
        if col_idx >= len(data_cols):
            logger.warning(
                "Horizons VECTORS data row has fewer columns than expected"
            )
            return None
        if data_cols[col_idx].lower() == "n.a.":
            logger.warning(
                "Horizons VECTORS data contains 'n.a.' — position unavailable"
            )
            return None

    try:
        x_au = float(data_cols[x_col])
        y_au = float(data_cols[y_col])
        z_au = float(data_cols[z_col])
    except (IndexError, ValueError) as exc:
        logger.warning(f"Horizons VECTORS CSV float conversion failed: {exc}")
        return None

    return (x_au, y_au, z_au)


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
# Earth-detail position helper
# ---------------------------------------------------------------------------


async def _compute_earth_detail_position(
    command_id: str, label_sv: str
) -> Optional[EarthDetailPosition]:
    """
    Fetch geocentric VECTORS data and convert to EarthDetailPosition.

    Coordinate convention (matches earth_system.py):
        x_offset — J2000 equatorial X axis (toward vernal equinox)
        y_offset — J2000 equatorial Y axis (90° east in equatorial plane)

    Returns None on any fetch or parse failure so the caller can safely
    ignore the result without disrupting the sky-map response.
    """
    try:
        vectors_text = await _fetch_horizons_vectors(command_id)
        if vectors_text is None:
            logger.warning(
                f"Earth-detail VECTORS fetch returned None for command_id={command_id}"
            )
            return None

        xyz = _parse_horizons_vectors(vectors_text)
        if xyz is None:
            logger.warning(
                f"Earth-detail VECTORS parse failed for command_id={command_id}"
            )
            return None

        x_au, y_au, z_au = xyz

        distance_km = math.sqrt(x_au ** 2 + y_au ** 2 + z_au ** 2) * _AU_TO_KM
        x_offset_er = x_au * _AU_TO_KM / _EARTH_RADIUS_KM
        y_offset_er = y_au * _AU_TO_KM / _EARTH_RADIUS_KM

        logger.info(
            f"Earth-detail position for command_id={command_id}: "
            f"x={x_offset_er:.2f} ER  y={y_offset_er:.2f} ER  "
            f"dist={distance_km:.0f} km"
        )

        return EarthDetailPosition(
            x_offset_earth_radii=round(x_offset_er, 3),
            y_offset_earth_radii=round(y_offset_er, 3),
            distance_km=round(distance_km, 1),
            label_sv=label_sv,
        )
    except Exception as exc:
        logger.warning(
            f"Unexpected error computing Earth-detail position for "
            f"command_id={command_id}: {exc}"
        )
        return None


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

                # ------------------------------------------------------------------
                # Earth-detail position (geocentric VECTORS call, optional).
                # Failure here never prevents the sky-map object from being returned.
                # ------------------------------------------------------------------
                earth_detail_position = None
                if entry.get("earth_detail"):
                    earth_detail_position = await _compute_earth_detail_position(
                        command_id=command_id,
                        label_sv=entry.get("label_sv", entry["name"]),
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
                    earth_detail_position=earth_detail_position,
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
