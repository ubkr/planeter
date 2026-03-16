"""
Regression tests for backend/app/utils/sun.py and backend/app/utils/moon.py.

These tests guard against a specific bug where `round(azimuth_deg, 1)` could
produce exactly `360.0` (e.g. when the raw value is 359.95 or higher), which
would violate the Pydantic `lt=360` constraint on `SunInfo.azimuth_deg` and
`MoonInfo.azimuth_deg`.

The fix: `% 360.0` is applied *after* `round()` so 360.0 becomes 0.0.

Test strategy:
  1. Monkeypatch `math.degrees` inside each utils module to inject a raw value
     of 359.95 — this rounds to 360.0 before the fix and 0.0 after.
  2. Assert the returned `azimuth_deg` is in [0, 360) regardless.
  3. Add a parametrised integration test across real ephem outputs for a grid
     of dates and coordinates, checking the invariant on each call.
"""

from datetime import datetime
from unittest.mock import patch

import pytest

from app.utils.sun import calculate_sun_penalty
from app.utils.moon import calculate_moon_penalty
from app.models.planet import SunInfo, MoonInfo


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _assert_azimuth_valid(azimuth_deg: float, label: str) -> None:
    """Assert azimuth is in the half-open interval [0, 360)."""
    assert 0.0 <= azimuth_deg < 360.0, (
        f"{label}: azimuth_deg {azimuth_deg} is outside [0, 360)"
    )


# ---------------------------------------------------------------------------
# 1. Sun: edge-case injection — raw azimuth rounds to 360.0
# ---------------------------------------------------------------------------

def test_sun_azimuth_never_360_after_round_edge_case():
    """
    Inject a raw radian value whose degree equivalent is 359.951 so that
    round(..., 1) produces 360.0 without the post-round `% 360.0` fix.
    The returned azimuth_deg must be 0.0 (i.e. 360.0 % 360.0), not 360.0.

    Note: round(359.95, 1) = 359.9 due to Python's banker's rounding and
    floating-point representation, but round(359.951, 1) reliably = 360.0.
    """
    import math
    # 359.951 degrees — round(359.951, 1) == 360.0 in Python 3.9.
    raw_degrees = 359.951
    assert round(359.951, 1) == 360.0, "Platform rounding assumption must hold for this test to be meaningful"

    # Patch math.degrees *inside the sun module* so it returns our crafted value
    # for the azimuth conversion only.  The patched callable records calls and
    # returns raw_degrees for every call (elevation conversion also goes through
    # math.degrees, so we return a safe elevation on the first call and our
    # edge-case azimuth on the second call).
    # call 1: elevation (sun.alt), call 2: azimuth (sun.az)
    call_results = iter([-20.0, raw_degrees])

    def fake_degrees(radians_val):
        return next(call_results)

    with patch("app.utils.sun.math.degrees", side_effect=fake_degrees):
        result = calculate_sun_penalty(59.3, 18.1, dt=datetime(2025, 6, 15, 22, 0))

    _assert_azimuth_valid(result["azimuth_deg"], "sun edge-case 359.95")


def test_sun_azimuth_edge_case_value_is_zero():
    """
    Same injection as above: when round(359.951, 1) == 360.0, the % 360.0
    normalisation must produce exactly 0.0.
    """
    import math
    raw_degrees = 359.951
    assert round(359.951, 1) == 360.0, "Platform rounding assumption must hold for this test to be meaningful"
    # call 1: elevation (sun.alt), call 2: azimuth (sun.az)
    call_results = iter([-20.0, raw_degrees])

    def fake_degrees(radians_val):
        return next(call_results)

    with patch("app.utils.sun.math.degrees", side_effect=fake_degrees):
        result = calculate_sun_penalty(59.3, 18.1, dt=datetime(2025, 6, 15, 22, 0))

    assert result["azimuth_deg"] == 0.0, (
        f"Expected 0.0 after normalising 360.0, got {result['azimuth_deg']}"
    )


# ---------------------------------------------------------------------------
# 2. Moon: edge-case injection — raw azimuth rounds to 360.0
# ---------------------------------------------------------------------------

def test_moon_azimuth_never_360_after_round_edge_case():
    """
    Inject 359.951 degrees as the raw moon azimuth.  The % 360.0 applied after
    round() must prevent the return value from being 360.0.

    Note: round(359.951, 1) == 360.0 in Python 3.9 — this is the trigger value.
    """
    import math
    raw_degrees = 359.951
    assert round(359.951, 1) == 360.0, "Platform rounding assumption must hold for this test to be meaningful"
    # call 1: elevation (moon.alt), call 2: azimuth (moon.az)
    call_results = iter([15.0, raw_degrees])

    def fake_degrees(radians_val):
        return next(call_results)

    with patch("app.utils.moon.math.degrees", side_effect=fake_degrees):
        result = calculate_moon_penalty(59.3, 18.1, dt=datetime(2025, 6, 15, 22, 0))

    _assert_azimuth_valid(result["azimuth_deg"], "moon edge-case 359.95")


def test_moon_azimuth_edge_case_value_is_zero():
    """
    Confirm the exact value: round(359.951, 1) % 360.0 must be 0.0.
    """
    import math
    raw_degrees = 359.951
    assert round(359.951, 1) == 360.0, "Platform rounding assumption must hold for this test to be meaningful"
    # call 1: elevation (moon.alt), call 2: azimuth (moon.az)
    call_results = iter([15.0, raw_degrees])

    def fake_degrees(radians_val):
        return next(call_results)

    with patch("app.utils.moon.math.degrees", side_effect=fake_degrees):
        result = calculate_moon_penalty(59.3, 18.1, dt=datetime(2025, 6, 15, 22, 0))

    assert result["azimuth_deg"] == 0.0, (
        f"Expected 0.0 after normalising 360.0, got {result['azimuth_deg']}"
    )


# ---------------------------------------------------------------------------
# 3. Pydantic model accepts the normalised values without ValidationError
# ---------------------------------------------------------------------------

def test_sun_info_pydantic_rejects_360():
    """
    Confirm that SunInfo.azimuth_deg rejects 360.0 — this documents why the
    normalisation is necessary and prevents the constraint from being relaxed.
    """
    from pydantic import ValidationError
    with pytest.raises(ValidationError):
        SunInfo(elevation_deg=-20.0, azimuth_deg=360.0, twilight_phase="darkness")


def test_moon_info_pydantic_rejects_360():
    """
    Confirm that MoonInfo.azimuth_deg rejects 360.0.
    """
    from pydantic import ValidationError
    with pytest.raises(ValidationError):
        MoonInfo(illumination=0.5, elevation_deg=15.0, azimuth_deg=360.0)


def test_sun_info_pydantic_accepts_zero():
    """After normalisation 360.0 becomes 0.0; Pydantic must accept 0.0."""
    info = SunInfo(elevation_deg=-20.0, azimuth_deg=0.0, twilight_phase="darkness")
    assert info.azimuth_deg == 0.0


def test_moon_info_pydantic_accepts_zero():
    """After normalisation 360.0 becomes 0.0; Pydantic must accept 0.0."""
    info = MoonInfo(illumination=0.5, elevation_deg=15.0, azimuth_deg=0.0)
    assert info.azimuth_deg == 0.0


# ---------------------------------------------------------------------------
# 4. Integration: real ephem output stays in [0, 360) across date/location grid
# ---------------------------------------------------------------------------

# A spread of Swedish latitudes, longitudes, and datetimes chosen to exercise
# different solar and lunar positions including near-horizon edge cases.
_INTEGRATION_PARAMS = [
    (55.7, 13.4, datetime(2025, 6, 15, 0, 0)),   # Malmö, midsummer midnight
    (59.3, 18.1, datetime(2025, 12, 21, 12, 0)),  # Stockholm, winter solstice noon
    (67.8, 20.2, datetime(2025, 3, 20, 6, 0)),    # Kiruna, spring equinox dawn
    (57.7, 11.9, datetime(2025, 9, 23, 18, 0)),   # Gothenburg, autumn equinox dusk
    (63.8, 20.3, datetime(2025, 1, 1, 3, 0)),     # Umeå, new year pre-dawn
    (56.0, 14.0, datetime(2025, 6, 21, 23, 59)),  # Blekinge, solstice late night
]


@pytest.mark.parametrize("lat,lon,dt", _INTEGRATION_PARAMS)
def test_sun_azimuth_in_valid_range_real_ephem(lat, lon, dt):
    """
    Call calculate_sun_penalty with real ephem computation and assert
    azimuth_deg is in [0, 360) for each coordinate/date combination.
    """
    result = calculate_sun_penalty(lat, lon, dt=dt)
    _assert_azimuth_valid(result["azimuth_deg"], f"sun lat={lat} lon={lon} dt={dt}")


@pytest.mark.parametrize("lat,lon,dt", _INTEGRATION_PARAMS)
def test_moon_azimuth_in_valid_range_real_ephem(lat, lon, dt):
    """
    Call calculate_moon_penalty with real ephem computation and assert
    azimuth_deg is in [0, 360) for each coordinate/date combination.
    """
    result = calculate_moon_penalty(lat, lon, dt=dt)
    _assert_azimuth_valid(result["azimuth_deg"], f"moon lat={lat} lon={lon} dt={dt}")
