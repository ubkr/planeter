"""
Tests for _is_planet_observable() and _compute_next_visible_time() in
backend/app/api/routes/planets.py.

The functions use a magnitude-aware sky brightness model (limiting_magnitude())
rather than a hard sun-altitude threshold to determine whether a planet is
observable.  These tests verify that the model behaves correctly at key
boundary conditions.

Group A: _is_planet_observable() unit tests — pure boolean logic, no ephem.
Group B: _compute_next_visible_time() integration tests — real ephem, fixed dates.
Group C: Midnight-sun edge case — no dark window returns None for all planets.

All tests use fixed datetimes so results are fully deterministic.

Anchor values used throughout (from app.utils.sun._LIM_MAG_ANCHORS):
  sun=-3°  → limiting_magnitude = -3.5  (between anchors (-2,-4) and (-4,-3))
  sun=-8°  → limiting_magnitude =  0.5  (between anchors (-6,-1) and (-12,3.5))
  sun=-12° → limiting_magnitude =  3.5  (anchor value)
"""

import re
from datetime import datetime, timezone

from app.api.routes.planets import _compute_next_visible_time, _is_planet_observable
from app.utils.sun import limiting_magnitude


# ISO 8601 UTC pattern — must match YYYY-MM-DDTHH:MM:SSZ exactly.
_ISO8601_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")

# Stockholm-ish coordinates (59.3°N, 18.0°E) used for integration tests.
_STOCKHOLM_LAT = 59.3
_STOCKHOLM_LON = 18.0

# Base datetime: evening of 2026-03-22 in UTC.  The sun has already set at
# Stockholm (sun_alt ~-20° at 20:00 UTC), so the 24-hour scan will include
# the next civil-twilight window on the evening of 2026-03-23.
_BASE_DT = datetime(2026, 3, 22, 20, 0, 0, tzinfo=timezone.utc)


# ---------------------------------------------------------------------------
# Helpers — pre-computed anchor values
# ---------------------------------------------------------------------------

def _lim_mag_at(sun_deg: float) -> float:
    """Return limiting_magnitude at the given sun altitude for inline comments."""
    return limiting_magnitude(sun_deg)


# ---------------------------------------------------------------------------
# Group A: _is_planet_observable() unit tests
# ---------------------------------------------------------------------------

def test_venus_observable_at_sun_minus3_with_good_altitude():
    # Venus (mag ~ -4.0) is brighter than the sky limit at sun=-3°.
    # limiting_mag(-3) = -3.5; -4.0 < -3.5 → True.
    # Altitude 15° clears the 5° minimum threshold.
    result = _is_planet_observable(
        sun_alt_deg=-3.0,
        planet_alt_deg=15.0,
        planet_mag=-4.0,
    )
    assert result is True, (
        f"Expected Venus (mag=-4.0) observable at sun=-3° "
        f"(lim_mag={_lim_mag_at(-3.0):.2f}), got False"
    )


def test_saturn_not_observable_at_sun_minus3():
    # Saturn (mag ~ +0.8) is fainter than the sky limit at sun=-3°.
    # limiting_mag(-3) = -3.5; 0.8 < -3.5 → False.
    # Altitude 15° would otherwise pass the altitude threshold.
    result = _is_planet_observable(
        sun_alt_deg=-3.0,
        planet_alt_deg=15.0,
        planet_mag=0.8,
    )
    assert result is False, (
        f"Expected Saturn (mag=0.8) NOT observable at sun=-3° "
        f"(lim_mag={_lim_mag_at(-3.0):.2f}); 0.8 is fainter than -3.5"
    )


def test_planet_not_observable_at_altitude_threshold():
    # planet_alt_deg == 5.0 is exactly at the minimum threshold (<=), so
    # the function returns False regardless of how bright the planet is.
    result = _is_planet_observable(
        sun_alt_deg=-8.0,
        planet_alt_deg=5.0,
        planet_mag=-4.0,
    )
    assert result is False, (
        "Expected False when planet_alt_deg=5.0 equals the min_altitude_deg=5.0 "
        "(the check is <=, so boundary is rejected)"
    )


def test_planet_observable_just_above_altitude_threshold():
    # planet_alt_deg just above 5° clears the boundary.
    # limiting_mag(-8) = 0.5; Venus (-4.0) < 0.5 → True.
    result = _is_planet_observable(
        sun_alt_deg=-8.0,
        planet_alt_deg=5.1,
        planet_mag=-4.0,
    )
    assert result is True, (
        "Expected True when planet_alt_deg=5.1 (just above threshold=5.0) "
        f"and mag=-4.0 < lim_mag={_lim_mag_at(-8.0):.2f}"
    )


def test_no_planet_observable_at_daytime():
    # sun_alt_deg >= 0 must always return False — daytime condition.
    result = _is_planet_observable(
        sun_alt_deg=0.0,
        planet_alt_deg=15.0,
        planet_mag=-4.0,
    )
    assert result is False, (
        "Expected False when sun_alt_deg=0.0 (sun at horizon — daytime)"
    )


def test_no_planet_observable_when_sun_above_horizon():
    # Sun well above horizon: even Venus at peak brightness is blocked.
    result = _is_planet_observable(
        sun_alt_deg=30.0,
        planet_alt_deg=45.0,
        planet_mag=-4.8,
    )
    assert result is False, (
        "Expected False when sun_alt_deg=30.0 (sun well above horizon)"
    )


def test_mars_not_observable_at_sun_minus8():
    # Mars (mag ~ +1.5) is fainter than the sky limit at sun=-8°.
    # limiting_mag(-8) = 0.5 (midpoint between anchors (-6,-1) and (-12,3.5));
    # 1.5 is NOT brighter than lim_mag (0.5) → planet_mag < lim_mag is False → not observable.
    # Altitude 15° is well above the threshold, so altitude is not the cause.
    result = _is_planet_observable(
        sun_alt_deg=-8.0,
        planet_alt_deg=15.0,
        planet_mag=1.5,
    )
    assert result is False, (
        f"Expected Mars (mag=1.5) NOT observable at sun=-8° "
        f"(lim_mag={_lim_mag_at(-8.0):.2f}); 1.5 is fainter than 0.5"
    )


def test_planet_observable_in_full_darkness():
    # Sun well below -18°: limiting_mag is clamped to 6.5.
    # Saturn (mag=0.8) is brighter than 6.5 → True.
    result = _is_planet_observable(
        sun_alt_deg=-25.0,
        planet_alt_deg=30.0,
        planet_mag=0.8,
    )
    assert result is True, (
        f"Expected Saturn (mag=0.8) observable at sun=-25° "
        f"(lim_mag={_lim_mag_at(-25.0):.2f} — full darkness clamp)"
    )


def test_custom_min_altitude_respected():
    # Custom min_altitude_deg=10: planet at 8° must return False even when
    # all other conditions would allow visibility.
    result = _is_planet_observable(
        sun_alt_deg=-20.0,
        planet_alt_deg=8.0,
        planet_mag=-4.0,
        min_altitude_deg=10.0,
    )
    assert result is False, (
        "Expected False when planet_alt_deg=8.0 < custom min_altitude_deg=10.0"
    )


# ---------------------------------------------------------------------------
# Group B: _compute_next_visible_time() integration tests
# ---------------------------------------------------------------------------

def test_venus_returns_non_none_from_stockholm_evening():
    # Venus is the evening star in late March 2026.  Starting from 20:00 UTC
    # on 2026-03-22 (sun already set at Stockholm), the scan should find Venus
    # observable during the civil twilight of the following evening (2026-03-23).
    # Venus mag ~ -3.8 is brighter than limiting_mag at civil twilight depths.
    #
    # Venus is the evening star in late March 2026 (~through mid-2026); if this
    # test fails in future, verify Venus visibility and update _BASE_DT to a
    # known evening-star window.
    result = _compute_next_visible_time("Venus", _STOCKHOLM_LAT, _STOCKHOLM_LON, _BASE_DT)
    assert result is not None, (
        "Expected _compute_next_visible_time('Venus', Stockholm, 2026-03-22T20:00Z) "
        "to return a non-None ISO 8601 string; Venus should be visible during "
        "civil twilight in late March 2026"
    )


def test_venus_result_is_valid_iso8601():
    # The returned string must match YYYY-MM-DDTHH:MM:SSZ exactly.
    result = _compute_next_visible_time("Venus", _STOCKHOLM_LAT, _STOCKHOLM_LON, _BASE_DT)
    assert result is not None, (
        "Prerequisite: Venus must be visible to test ISO 8601 format"
    )
    assert _ISO8601_RE.match(result), (
        f"Expected ISO 8601 UTC string (YYYY-MM-DDTHH:MM:SSZ), got: {result!r}"
    )


def test_venus_result_is_within_24h_window():
    # The function only scans 24 hours ahead, so the result must be within that range.
    from datetime import timedelta
    result = _compute_next_visible_time("Venus", _STOCKHOLM_LAT, _STOCKHOLM_LON, _BASE_DT)
    assert result is not None
    # Parse result and verify it falls within the 24h search window.
    result_dt = datetime.strptime(result, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    window_end = _BASE_DT + timedelta(hours=24)
    assert _BASE_DT <= result_dt <= window_end, (
        f"Expected result {result!r} to be within "
        f"[{_BASE_DT.isoformat()}, {window_end.isoformat()}]"
    )


def test_unknown_planet_name_returns_none():
    # An unrecognised planet name must return None without raising.
    result = _compute_next_visible_time("Pluto", _STOCKHOLM_LAT, _STOCKHOLM_LON, _BASE_DT)
    assert result is None, (
        "Expected None for unknown planet name 'Pluto'"
    )


def test_result_is_deterministic():
    # Two calls with identical arguments must return identical results.
    first = _compute_next_visible_time("Venus", _STOCKHOLM_LAT, _STOCKHOLM_LON, _BASE_DT)
    second = _compute_next_visible_time("Venus", _STOCKHOLM_LAT, _STOCKHOLM_LON, _BASE_DT)
    assert first == second, (
        f"Expected deterministic output; got {first!r} and {second!r}"
    )


# ---------------------------------------------------------------------------
# Group C: Midnight-sun — no dark window returns None for all planets
# ---------------------------------------------------------------------------

# Midsummer at 68°N (northern Sweden above the Arctic Circle): the sun stays
# above the horizon throughout the 24-hour scan window.  The 15-minute sampling
# loop never finds a sample where sun_alt < 0, so every planet returns None.
_MIDSUMMER_DT = datetime(2026, 6, 21, 12, 0, 0, tzinfo=timezone.utc)
_ARCTIC_LAT = 68.0
_ARCTIC_LON = 18.0

_PLANET_NAMES = ["Mercury", "Venus", "Mars", "Jupiter", "Saturn"]


def test_midnight_sun_returns_none_for_mercury():
    result = _compute_next_visible_time("Mercury", _ARCTIC_LAT, _ARCTIC_LON, _MIDSUMMER_DT)
    assert result is None, (
        f"Expected None for Mercury at 68°N on midsummer (midnight sun); got {result!r}"
    )


def test_midnight_sun_returns_none_for_venus():
    result = _compute_next_visible_time("Venus", _ARCTIC_LAT, _ARCTIC_LON, _MIDSUMMER_DT)
    assert result is None, (
        f"Expected None for Venus at 68°N on midsummer (midnight sun); got {result!r}"
    )


def test_midnight_sun_returns_none_for_mars():
    result = _compute_next_visible_time("Mars", _ARCTIC_LAT, _ARCTIC_LON, _MIDSUMMER_DT)
    assert result is None, (
        f"Expected None for Mars at 68°N on midsummer (midnight sun); got {result!r}"
    )


def test_midnight_sun_returns_none_for_jupiter():
    result = _compute_next_visible_time("Jupiter", _ARCTIC_LAT, _ARCTIC_LON, _MIDSUMMER_DT)
    assert result is None, (
        f"Expected None for Jupiter at 68°N on midsummer (midnight sun); got {result!r}"
    )


def test_midnight_sun_returns_none_for_saturn():
    result = _compute_next_visible_time("Saturn", _ARCTIC_LAT, _ARCTIC_LON, _MIDSUMMER_DT)
    assert result is None, (
        f"Expected None for Saturn at 68°N on midsummer (midnight sun); got {result!r}"
    )
