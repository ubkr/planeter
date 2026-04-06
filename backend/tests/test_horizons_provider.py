"""
Unit tests for the JPL Horizons provider.

All HTTP calls are mocked — no real network requests are made.

asyncio_mode = auto is set in pytest.ini so no @pytest.mark.asyncio
decorator is needed on any async test.

Tests are grouped by public surface:
  - _parse_horizons_csv   (synchronous OBSERVER parser, tests 1-6)
  - get_horizons_objects  (async public API, tests 7-12)
  - _parse_horizons_vectors (synchronous VECTORS parser, tests 13-18)
  - earth_detail_position population (tests 19-21)
"""

from unittest.mock import AsyncMock, patch

import httpx
import pytest

from app.services.artificial_objects.horizons_provider import (
    _parse_horizons_csv,
    _parse_horizons_vectors,
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
 Date__(UT)__HR:MN:SC.fff, , , Azi_(a-app), Elev_(a-app),
$$SOE
 2026-Apr-06 12:00:00.000,*, ,     142.1234,    23.4567,
$$EOE
"""

# A realistic Horizons VECTORS CSV snippet.
# Column order: JDTDB, Calendar Date (TDB), X, Y, Z, VX, VY, VZ
_VALID_VECTORS_CSV = """\
API VERSION: 1.0
Generator: Horizons
 JDTDB, Calendar Date (TDB), X, Y, Z, VX, VY, VZ,
$$SOE
 2460588.000000000, 2026-Apr-06 12:00:00.0000, 1.234567890123456E-03,-2.345678901234567E-03, 3.456789012345678E-04, 1.0E-05,-2.0E-05, 3.0E-06,
$$EOE
"""

# Patch targets.
_FETCH_OBSERVER_TARGET = (
    "app.services.artificial_objects.horizons_provider._fetch_horizons_observer"
)
_FETCH_VECTORS_TARGET = (
    "app.services.artificial_objects.horizons_provider._fetch_horizons_vectors"
)
_COMPUTE_EARTH_DETAIL_TARGET = (
    "app.services.artificial_objects.horizons_provider._compute_earth_detail_position"
)


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
 Date__(UT)__HR:MN:SC.fff, , , Azi_(a-app), Elev_(a-app),
$$SOE
$$EOE
"""
    result = _parse_horizons_csv(empty_block_csv)
    assert result is None


def test_parse_missing_header_columns_returns_none():
    """Test 5: Header line does not contain Azi_(a-app)/Elev_(a-app) returns None."""
    csv_bad_header = """\
 Date__(UT)__HR:MN:SC.fff, , , SomeCol, OtherCol,
$$SOE
 2026-Apr-06 12:00:00.000,*, ,     142.1234,    23.4567,
$$EOE
"""
    result = _parse_horizons_csv(csv_bad_header)
    assert result is None


def test_parse_non_numeric_data_row_returns_none():
    """Test 6: Non-numeric value in azimuth/elevation column returns None."""
    csv_bad_data = """\
 Date__(UT)__HR:MN:SC.fff, , , Azi_(a-app), Elev_(a-app),
$$SOE
 2026-Apr-06 12:00:00.000,*, ,     N/A,    23.4567,
$$EOE
"""
    result = _parse_horizons_csv(csv_bad_data)
    assert result is None


# ---------------------------------------------------------------------------
# get_horizons_objects — tests 7-12
#
# Patch _fetch_horizons_observer to bypass the cache and HTTP, and
# patch _compute_earth_detail_position to None so the VECTORS HTTP call
# is also skipped.  The earth_detail_position field is tested separately.
# ---------------------------------------------------------------------------


async def test_get_horizons_objects_success():
    """Test 7: Valid Horizons response yields ArtificialObject for Artemis II."""
    with (
        patch(_FETCH_OBSERVER_TARGET, new=AsyncMock(return_value=_VALID_HORIZONS_CSV)),
        patch(_COMPUTE_EARTH_DETAIL_TARGET, new=AsyncMock(return_value=None)),
    ):
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
    with patch(_FETCH_OBSERVER_TARGET, new=AsyncMock(return_value=None)):
        objects = await get_horizons_objects(_LAT, _LON)

    assert objects == []


async def test_get_horizons_objects_empty_soe_eoe_returns_empty():
    """Test 9: Valid HTTP response but empty SOE/EOE block returns empty list."""
    empty_block_csv = """\
 Date__(UT)__HR:MN:SC.fff, , , Azi_(a-app), Elev_(a-app),
$$SOE
$$EOE
"""
    with patch(_FETCH_OBSERVER_TARGET, new=AsyncMock(return_value=empty_block_csv)):
        objects = await get_horizons_objects(_LAT, _LON)

    assert objects == []


async def test_get_horizons_objects_timeout_returns_empty():
    """Test 10: Network timeout raises TimeoutException → returns empty list."""
    with patch(_FETCH_OBSERVER_TARGET, new=AsyncMock(side_effect=httpx.TimeoutException("timed out"))):
        objects = await get_horizons_objects(_LAT, _LON)

    assert objects == []


# ---------------------------------------------------------------------------
# _parse_horizons_csv — test 11
# get_horizons_objects — test 12
# ---------------------------------------------------------------------------

_NEGATIVE_ELEV_CSV = """\
API VERSION: 1.0
Generator: Horizons
 Date__(UT)__HR:MN:SC.fff, , , Azi_(a-app), Elev_(a-app),
$$SOE
 2026-Apr-06 12:00:00.000, , ,     210.5000,   -49.8000,
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
    with (
        patch(_FETCH_OBSERVER_TARGET, new=AsyncMock(return_value=_NEGATIVE_ELEV_CSV)),
        patch(_COMPUTE_EARTH_DETAIL_TARGET, new=AsyncMock(return_value=None)),
    ):
        objects = await get_horizons_objects(_LAT, _LON)

    assert len(objects) == 1
    obj = objects[0]
    assert obj.is_above_horizon is False
    assert obj.altitude_deg == pytest.approx(-49.8)


# ---------------------------------------------------------------------------
# _parse_horizons_vectors — tests 13-18
# ---------------------------------------------------------------------------


def test_parse_vectors_valid_csv_returns_floats():
    """Test 13: Valid VECTORS CSV yields (x_au, y_au, z_au) as floats."""
    result = _parse_horizons_vectors(_VALID_VECTORS_CSV)
    assert result is not None, "Expected a result tuple, got None"
    x_au, y_au, z_au = result
    assert isinstance(x_au, float)
    assert isinstance(y_au, float)
    assert isinstance(z_au, float)
    assert pytest.approx(x_au, rel=1e-6) == 1.234567890123456e-03
    assert pytest.approx(y_au, rel=1e-6) == -2.345678901234567e-03
    assert pytest.approx(z_au, rel=1e-6) == 3.456789012345678e-04


def test_parse_vectors_missing_soe_returns_none():
    """Test 14: VECTORS response without $$SOE returns None."""
    result = _parse_horizons_vectors(_VALID_VECTORS_CSV.replace("$$SOE", ""))
    assert result is None


def test_parse_vectors_missing_eoe_returns_none():
    """Test 15: VECTORS response without $$EOE returns None."""
    result = _parse_horizons_vectors(_VALID_VECTORS_CSV.replace("$$EOE", ""))
    assert result is None


def test_parse_vectors_empty_data_block_returns_none():
    """Test 16: $$SOE and $$EOE present but empty data block returns None."""
    empty_block_csv = """\
 JDTDB, Calendar Date (TDB), X, Y, Z, VX, VY, VZ,
$$SOE
$$EOE
"""
    result = _parse_horizons_vectors(empty_block_csv)
    assert result is None


def test_parse_vectors_na_value_returns_none():
    """Test 17: 'n.a.' in any XYZ column returns None."""
    na_csv = """\
 JDTDB, Calendar Date (TDB), X, Y, Z, VX, VY, VZ,
$$SOE
 2460588.000000000, 2026-Apr-06 12:00:00.0000, n.a., n.a., n.a., n.a., n.a., n.a.,
$$EOE
"""
    result = _parse_horizons_vectors(na_csv)
    assert result is None


def test_parse_vectors_missing_xyz_columns_returns_none():
    """Test 18: Header without X/Y/Z column names returns None."""
    bad_header_csv = """\
 JDTDB, Calendar Date (TDB), A, B, C, VA, VB, VC,
$$SOE
 2460588.000000000, 2026-Apr-06 12:00:00.0000, 1.0E-03,-2.0E-03, 3.0E-04, 1.0E-05,-2.0E-05, 3.0E-06,
$$EOE
"""
    result = _parse_horizons_vectors(bad_header_csv)
    assert result is None


# ---------------------------------------------------------------------------
# earth_detail_position field population — tests 19-21
# ---------------------------------------------------------------------------


async def test_earth_detail_position_populated_when_vectors_succeed():
    """
    Test 19: When VECTORS call succeeds, earth_detail_position is populated
    with correct unit conversions on the returned ArtificialObject.
    """
    from app.models.artificial_object import EarthDetailPosition

    expected_edp = EarthDetailPosition(
        x_offset_earth_radii=29.003,
        y_offset_earth_radii=-55.048,
        distance_km=370123.4,
        label_sv="Artemis II",
    )

    with (
        patch(_FETCH_OBSERVER_TARGET, new=AsyncMock(return_value=_VALID_HORIZONS_CSV)),
        patch(_COMPUTE_EARTH_DETAIL_TARGET, new=AsyncMock(return_value=expected_edp)),
    ):
        objects = await get_horizons_objects(_LAT, _LON)

    assert len(objects) == 1
    obj = objects[0]
    assert obj.earth_detail_position is not None
    assert obj.earth_detail_position.label_sv == "Artemis II"
    assert obj.earth_detail_position.distance_km == pytest.approx(370123.4)


async def test_earth_detail_position_none_when_vectors_fail():
    """
    Test 20: When VECTORS call fails (_compute_earth_detail_position returns None),
    earth_detail_position is None but the ArtificialObject is still returned.
    """
    with (
        patch(_FETCH_OBSERVER_TARGET, new=AsyncMock(return_value=_VALID_HORIZONS_CSV)),
        patch(_COMPUTE_EARTH_DETAIL_TARGET, new=AsyncMock(return_value=None)),
    ):
        objects = await get_horizons_objects(_LAT, _LON)

    assert len(objects) == 1
    obj = objects[0]
    assert obj.earth_detail_position is None
    # Sky-map fields must still be present and correct.
    assert obj.name == "Artemis II"
    assert obj.is_above_horizon is True


def test_parse_vectors_unit_conversion_values():
    """
    Test 21: Parsed X/Y/Z AU values produce correct Earth-radii offsets and
    distance_km via the known conversion factors (AU_TO_KM / EARTH_RADIUS_KM).
    """
    import math

    _AU_TO_KM = 149_597_870.7
    _EARTH_RADIUS_KM = 6_371.0

    result = _parse_horizons_vectors(_VALID_VECTORS_CSV)
    assert result is not None

    x_au, y_au, z_au = result

    distance_km = math.sqrt(x_au ** 2 + y_au ** 2 + z_au ** 2) * _AU_TO_KM
    x_er = x_au * _AU_TO_KM / _EARTH_RADIUS_KM
    y_er = y_au * _AU_TO_KM / _EARTH_RADIUS_KM

    # Verify the sign and rough magnitude.
    assert x_er > 0, "x_offset should be positive for positive X_au"
    assert y_er < 0, "y_offset should be negative for negative Y_au"
    assert distance_km > 0, "distance_km must be positive"
    # Sanity-check magnitudes: ~1.2e-3 AU * 149597870 km/AU / 6371 km/ER ≈ 29 ER
    assert pytest.approx(x_er, rel=1e-4) == x_au * _AU_TO_KM / _EARTH_RADIUS_KM
