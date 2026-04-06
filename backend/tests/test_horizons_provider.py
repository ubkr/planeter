"""
Unit tests for the JPL Horizons provider.

All HTTP calls are mocked — no real network requests are made.

asyncio_mode = auto is set in pytest.ini so no @pytest.mark.asyncio
decorator is needed on any async test.

Tests are grouped by the two public surfaces:
  - _parse_horizons_csv  (synchronous parser, tests 1-6)
  - get_horizons_objects (async public API, tests 7-10)
"""

from unittest.mock import AsyncMock, patch

import httpx
import pytest

from app.services.artificial_objects.horizons_provider import (
    _parse_horizons_csv,
    get_horizons_objects,
)

# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------

# Observer coordinates used in every async test.
_LAT = 55.7
_LON = 13.4

# A realistic Horizons OBSERVER CSV snippet. The column header line must
# contain "Azi_(a-app)" and "Elev_(a-app)" (checked by _parse_horizons_csv).
# The data row uses the same column order as the header.
_VALID_HORIZONS_CSV = """\
API VERSION: 1.0
Generator: Horizons
 Date__(UT)__HR:MN:SC.fff, , Azi_(a-app), Elev_(a-app),
$$SOE
 2026-Apr-06 12:00:00.000, ,     142.1234,    23.4567,
$$EOE
"""


# ---------------------------------------------------------------------------
# _parse_horizons_csv — tests 1-6
# ---------------------------------------------------------------------------


def test_parse_valid_csv_returns_floats():
    """Test 1: Valid CSV yields (azimuth_deg, altitude_deg) as floats."""
    result = _parse_horizons_csv(_VALID_HORIZONS_CSV)
    assert result is not None, "Expected a result tuple, got None"
    azimuth_deg, altitude_deg = result
    assert isinstance(azimuth_deg, float)
    assert isinstance(altitude_deg, float)
    assert pytest.approx(altitude_deg, abs=1e-4) == 23.4567
    # Azimuth is normalised to [0, 360).
    assert 0.0 <= azimuth_deg < 360.0
    assert pytest.approx(azimuth_deg, abs=1e-4) == 142.1234


def test_parse_missing_soe_returns_none():
    """Test 2: CSV without $$SOE marker returns None."""
    csv_without_soe = _VALID_HORIZONS_CSV.replace("$$SOE", "")
    result = _parse_horizons_csv(csv_without_soe)
    assert result is None


def test_parse_missing_eoe_returns_none():
    """Test 3: CSV without $$EOE marker returns None."""
    csv_without_eoe = _VALID_HORIZONS_CSV.replace("$$EOE", "")
    result = _parse_horizons_csv(csv_without_eoe)
    assert result is None


def test_parse_empty_data_block_returns_none():
    """Test 4: $$SOE and $$EOE present but nothing between them returns None."""
    empty_block_csv = """\
 Date__(UT)__HR:MN:SC.fff, , Azi_(a-app), Elev_(a-app),
$$SOE
$$EOE
"""
    result = _parse_horizons_csv(empty_block_csv)
    assert result is None


def test_parse_missing_header_columns_returns_none():
    """Test 5: Header line does not contain Azi_(a-app)/Elev_(a-app) returns None."""
    csv_bad_header = """\
 Date__(UT)__HR:MN:SC.fff, , SomeCol, OtherCol,
$$SOE
 2026-Apr-06 12:00:00.000, ,     142.1234,    23.4567,
$$EOE
"""
    result = _parse_horizons_csv(csv_bad_header)
    assert result is None


def test_parse_non_numeric_data_row_returns_none():
    """Test 6: Non-numeric value in azimuth/elevation column returns None."""
    csv_bad_data = """\
 Date__(UT)__HR:MN:SC.fff, , Azi_(a-app), Elev_(a-app),
$$SOE
 2026-Apr-06 12:00:00.000, ,     N/A,    23.4567,
$$EOE
"""
    result = _parse_horizons_csv(csv_bad_data)
    assert result is None


# ---------------------------------------------------------------------------
# get_horizons_objects — tests 7-10
#
# Patch _fetch_horizons_observer directly so both the cache check and the
# HTTP call are bypassed in one step.
# ---------------------------------------------------------------------------

_FETCH_TARGET = (
    "app.services.artificial_objects.horizons_provider._fetch_horizons_observer"
)


async def test_get_horizons_objects_success():
    """Test 7: Valid Horizons response yields ArtificialObject for Artemis II."""
    with patch(_FETCH_TARGET, new=AsyncMock(return_value=_VALID_HORIZONS_CSV)):
        objects = await get_horizons_objects(_LAT, _LON)

    assert len(objects) == 1
    obj = objects[0]
    assert obj.name == "Artemis II"
    assert obj.colour == "#00bfff"
    assert obj.label_sv == "Artemis II"
    assert obj.data_source == "jpl_horizons"
    # altitude 23.4567 > 0 → is_above_horizon must be True.
    assert obj.is_above_horizon is True


async def test_get_horizons_objects_http_500_returns_empty():
    """Test 8: Horizons HTTP 500 returns empty list without raising."""
    # The fetch helper catches all exceptions and returns None; we simulate
    # _fetch_horizons_observer returning None (as it would after a 500).
    with patch(_FETCH_TARGET, new=AsyncMock(return_value=None)):
        objects = await get_horizons_objects(_LAT, _LON)

    assert objects == []


async def test_get_horizons_objects_empty_soe_eoe_returns_empty():
    """Test 9: Valid HTTP response but empty SOE/EOE block returns empty list."""
    empty_block_csv = """\
 Date__(UT)__HR:MN:SC.fff, , Azi_(a-app), Elev_(a-app),
$$SOE
$$EOE
"""
    with patch(_FETCH_TARGET, new=AsyncMock(return_value=empty_block_csv)):
        objects = await get_horizons_objects(_LAT, _LON)

    assert objects == []


async def test_get_horizons_objects_timeout_returns_empty():
    """Test 10: Network timeout raises TimeoutException → returns empty list."""
    with patch(_FETCH_TARGET, new=AsyncMock(side_effect=httpx.TimeoutException("timed out"))):
        objects = await get_horizons_objects(_LAT, _LON)

    assert objects == []


# ---------------------------------------------------------------------------
# _parse_horizons_csv — test 11
# get_horizons_objects — test 12
# ---------------------------------------------------------------------------

_NEGATIVE_ELEV_CSV = """\
API VERSION: 1.0
Generator: Horizons
 Date__(UT)__HR:MN:SC.fff, , Azi_(a-app), Elev_(a-app),
$$SOE
 2026-Apr-06 12:00:00.000, ,     210.5000,   -49.8000,
$$EOE
"""


def test_parse_negative_altitude_returns_negative_float():
    """Test 11: Negative elevation is parsed correctly and is below zero."""
    result = _parse_horizons_csv(_NEGATIVE_ELEV_CSV)
    assert result is not None, "Expected a result tuple, got None"
    _azimuth_deg, altitude_deg = result
    assert altitude_deg == pytest.approx(-49.8)
    # is_above_horizon is derived from altitude_deg > 0 in get_horizons_objects.
    # Verify the raw float signals below-horizon correctly.
    assert altitude_deg < 0


async def test_get_horizons_objects_below_horizon_sets_flag():
    """Test 12: Object with negative elevation produces is_above_horizon=False."""
    with patch(_FETCH_TARGET, new=AsyncMock(return_value=_NEGATIVE_ELEV_CSV)):
        objects = await get_horizons_objects(_LAT, _LON)

    assert len(objects) == 1
    obj = objects[0]
    assert obj.is_above_horizon is False
    assert obj.altitude_deg == pytest.approx(-49.8)
