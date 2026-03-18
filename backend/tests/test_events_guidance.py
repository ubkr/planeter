"""
Tests for observation guidance helpers in events.py.

Covers:
  1. Integration: detect_events() returns at least one event with non-null
     guidance fields for a known nighttime window at Stockholm.
  2. azimuth_to_compass_sv() covers all 16 compass points correctly.
  3. _compute_observation_guidance() returns a below-horizon tip when the
     observer's horizon is forced to +45° so the body is always "below".
  4. Unknown body name raises ValueError (caught gracefully by the helper).

All tests use real ephem computation — no mocking of astronomical calculations.
The fixed dates are chosen so that at least some of the 60-day look-ahead
window includes observable events.
"""

import copy
from datetime import datetime, timedelta, timezone
from typing import Optional

import ephem
import pytest

from app.models.planet import azimuth_to_compass_sv
from app.services.planets.events import (
    _compute_observation_guidance,
    detect_events,
)

# ---------------------------------------------------------------------------
# Constants shared across tests
# ---------------------------------------------------------------------------

# Stockholm approximate coordinates.
STOCKHOLM_LAT = 59.3
STOCKHOLM_LON = 18.1

# A fixed 60-day look-ahead window starting 2026-04-01 (spring — many events).
WINDOW_START = datetime(2026, 4, 1, 0, 0, 0)
WINDOW_END = WINDOW_START + timedelta(days=60)

# A nighttime UTC datetime in Stockholm (local midnight is ~22 UTC in summer).
NIGHTTIME_DT = datetime(2026, 4, 15, 22, 0, 0)


# ---------------------------------------------------------------------------
# Test 1: detect_events() integration — guidance fields are populated
# ---------------------------------------------------------------------------

def test_detect_events_guidance_fields_populated():
    """
    Over a 60-day window at Stockholm at least one event must have non-null
    altitude_deg, azimuth_deg, compass_direction_sv, and observation_tip_sv.

    This is an integration test: real ephem computations are used and no
    mocking is performed.  The 60-day window is wide enough that the
    assertion is robust to small orbital variations.
    """
    events = detect_events(STOCKHOLM_LAT, STOCKHOLM_LON, WINDOW_START, WINDOW_END)

    assert len(events) > 0, "Expected at least one event in a 60-day window"

    guidance_populated = [
        e for e in events
        if (
            e.altitude_deg is not None
            and e.azimuth_deg is not None
            and e.compass_direction_sv is not None
            and e.observation_tip_sv is not None
        )
    ]

    assert len(guidance_populated) > 0, (
        "Expected at least one event with all four guidance fields non-null; "
        f"found {len(events)} events total but none with full guidance"
    )


# ---------------------------------------------------------------------------
# Test 2: azimuth_to_compass_sv() — all 16 compass points are valid Swedish
# ---------------------------------------------------------------------------

_EXPECTED_SWEDISH_DIRECTIONS = {
    "nord",
    "nord-nordost",
    "nordost",
    "ost-nordost",
    "ost",
    "ost-sydost",
    "sydost",
    "syd-sydost",
    "syd",
    "syd-sydväst",
    "sydväst",
    "väst-sydväst",
    "väst",
    "väst-nordväst",
    "nordväst",
    "nord-nordväst",
}

# The 16 exact sector centres, one per 22.5° starting at North.
_COMPASS_AZIMUTHS = [i * 22.5 for i in range(16)]


@pytest.mark.parametrize("azimuth", _COMPASS_AZIMUTHS)
def test_azimuth_to_compass_sv_all_16_points(azimuth: float):
    """
    Each of the 16 sector-centre azimuths must map to a known Swedish direction.
    """
    result = azimuth_to_compass_sv(azimuth)
    assert result in _EXPECTED_SWEDISH_DIRECTIONS, (
        f"azimuth {azimuth}° produced unexpected direction: {result!r}"
    )


def test_azimuth_to_compass_sv_returns_16_distinct_values():
    """
    The 16 sector centres must collectively produce all 16 distinct Swedish labels.
    """
    results = {azimuth_to_compass_sv(az) for az in _COMPASS_AZIMUTHS}
    assert results == _EXPECTED_SWEDISH_DIRECTIONS, (
        f"Expected all 16 Swedish directions; got {results}"
    )


def test_azimuth_to_compass_sv_normalises_360():
    """360° must map to the same direction as 0° (both are North)."""
    assert azimuth_to_compass_sv(360.0) == azimuth_to_compass_sv(0.0)


def test_azimuth_to_compass_sv_south():
    """180° must map to 'syd'."""
    assert azimuth_to_compass_sv(180.0) == "syd"


def test_azimuth_to_compass_sv_east():
    """90° must map to 'ost'."""
    assert azimuth_to_compass_sv(90.0) == "ost"


# ---------------------------------------------------------------------------
# Test 3: _compute_observation_guidance() — below-horizon tip
# ---------------------------------------------------------------------------

def _make_observer(lat: float, lon: float) -> ephem.Observer:
    obs = ephem.Observer()
    obs.lat = str(lat)
    obs.lon = str(lon)
    obs.pressure = 0
    return obs


def test_guidance_below_horizon_tip():
    """
    When observer.horizon is set to '+45:00', most bodies are forced "below
    the horizon" from ephem's perspective.  However, _compute_observation_guidance
    uses body.alt (geometric altitude) against 0° for the tip, not ephem's
    horizon setting.

    To reliably produce a below-zero altitude we pick a daytime UTC moment
    for Jupiter: Jupiter is below the horizon somewhere over Stockholm during
    a daytime observation window.  Instead of relying on a specific date, we
    test that when Jupiter's computed altitude is negative, the tip contains
    "under horisonten".

    Strategy: scan 24 hours in 1-hour steps from 2026-04-01 until we find a
    moment where Jupiter is below the horizon at Stockholm, then call
    _compute_observation_guidance and assert the tip.
    """
    obs = _make_observer(STOCKHOLM_LAT, STOCKHOLM_LON)
    scan_start = datetime(2026, 4, 1, 0, 0, 0)

    below_horizon_dt: Optional[datetime] = None
    for hour in range(24):
        candidate_dt = scan_start + timedelta(hours=hour)
        obs.date = ephem.Date(candidate_dt)
        jupiter = ephem.Jupiter()
        jupiter.compute(obs)
        alt_deg = float(jupiter.alt) * (180.0 / 3.141592653589793)
        if alt_deg < 0:
            below_horizon_dt = candidate_dt
            break

    assert below_horizon_dt is not None, (
        "Could not find a time when Jupiter is below the horizon at Stockholm "
        "within the 24-hour scan window — test setup assumption failed"
    )

    fresh_obs = _make_observer(STOCKHOLM_LAT, STOCKHOLM_LON)
    guidance = _compute_observation_guidance(fresh_obs, below_horizon_dt, "Jupiter", "opposition")

    assert guidance["observation_tip_sv"] is not None
    assert "under horisonten" in guidance["observation_tip_sv"], (
        f"Expected 'under horisonten' in tip but got: {guidance['observation_tip_sv']!r}"
    )


# ---------------------------------------------------------------------------
# Test 4: Guidance fields structure is always a dict with the six expected keys
# ---------------------------------------------------------------------------

def test_guidance_result_always_has_all_keys():
    """
    _compute_observation_guidance must always return a dict containing the
    six expected keys, even when the computation is partially failing.
    """
    obs = _make_observer(STOCKHOLM_LAT, STOCKHOLM_LON)
    result = _compute_observation_guidance(obs, NIGHTTIME_DT, "Mars", "opposition")

    expected_keys = {
        "altitude_deg",
        "azimuth_deg",
        "compass_direction_sv",
        "observation_tip_sv",
        "best_time_start",
        "best_time_end",
    }
    assert set(result.keys()) == expected_keys, (
        f"Unexpected keys in guidance result: {set(result.keys())}"
    )


# ---------------------------------------------------------------------------
# Test 5: Unknown body name is handled gracefully (all fields remain None)
# ---------------------------------------------------------------------------

def test_guidance_unknown_body_returns_all_none():
    """
    Passing an unknown body name to _compute_observation_guidance must not
    raise — the helper catches the ValueError internally and returns all-None.
    """
    obs = _make_observer(STOCKHOLM_LAT, STOCKHOLM_LON)
    result = _compute_observation_guidance(obs, NIGHTTIME_DT, "Pluto", "conjunction")

    for key, value in result.items():
        assert value is None, (
            f"Expected None for {key!r} with unknown body, got {value!r}"
        )
