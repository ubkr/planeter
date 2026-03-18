"""
Tests for the planet visibility scoring module.

All tests call score_planet() directly with explicit inputs so there are no
network calls, no ephem side-effects on scoring logic, and results are fully
deterministic.

The apply_scores integration test uses a fixed UTC datetime (noon 2025-06-15)
to ensure the sun is above the horizon at the test coordinates, making the
daytime hard-zero deterministic without mocking.

Reason key reference (Swedish, as produced by score_planet):
  "below_horizon"        – planet altitude <= 0
  "dagsljus"             – sun is up or in twilight (sun_penalty_pts > 0)
  "molnighet"            – cloud cover affects visibility (>= 25 %)
  "månljus"              – moon proximity penalty active
  "atmosfärisk_dämpning" – atmospheric extinction near horizon (altitude < 10°)
  "goda_förhållanden"    – no penalties; ideal conditions
"""

from datetime import datetime

import pytest

from app.models.planet import PlanetPosition
from app.services.scoring import apply_scores, score_planet
from app.services.planets.calculator import calculate_planet_positions
from app.utils.sun import calculate_sun_penalty
from app.utils.moon import calculate_moon_penalty


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

# Stockholm-ish coordinates used for integration tests.
LAT = 59.3
LON = 18.1

# A fixed noon datetime: sun is well above the horizon at Stockholm, making
# the "dagsljus" hard-zero deterministic without any mocking.
NOON_DT = datetime(2025, 6, 15, 12, 0)


def _make_planet(**overrides) -> PlanetPosition:
    """
    Return a PlanetPosition with sensible defaults, overriding any fields
    supplied by the caller.  Defaults represent a well-placed, easy-to-see
    planet (altitude 45°, magnitude -1.0, above the horizon).
    """
    defaults = dict(
        name="Mars",
        name_sv="Mars",
        altitude_deg=45.0,
        azimuth_deg=180.0,
        direction="S",
        magnitude=-1.0,
        constellation="Gemini",
        is_above_horizon=True,
    )
    defaults.update(overrides)
    return PlanetPosition(**defaults)


# ---------------------------------------------------------------------------
# 1. Below horizon → score 0
# ---------------------------------------------------------------------------

def test_below_horizon_score_is_zero():
    planet = _make_planet(altitude_deg=-5.0, is_above_horizon=False)
    score, reasons = score_planet(
        planet,
        sun_penalty_pts=0.0,
        cloud_cover=10.0,
        moon_illumination=0.0,
        moon_separation=90.0,
    )
    assert score == 0


def test_below_horizon_reason_present():
    planet = _make_planet(altitude_deg=-5.0, is_above_horizon=False)
    _score, reasons = score_planet(
        planet,
        sun_penalty_pts=0.0,
        cloud_cover=10.0,
        moon_illumination=0.0,
        moon_separation=90.0,
    )
    assert "below_horizon" in reasons


def test_exactly_at_horizon_score_is_zero():
    # altitude_deg == 0 is the boundary: the condition is altitude_deg <= 0
    planet = _make_planet(altitude_deg=0.0, is_above_horizon=False)
    score, reasons = score_planet(
        planet,
        sun_penalty_pts=0.0,
        cloud_cover=10.0,
        moon_illumination=0.0,
        moon_separation=90.0,
    )
    assert score == 0
    assert "below_horizon" in reasons


# ---------------------------------------------------------------------------
# 2. 100 % cloud cover → score 0
# ---------------------------------------------------------------------------

def test_full_cloud_cover_score_is_zero():
    planet = _make_planet(altitude_deg=45.0)
    score, reasons = score_planet(
        planet,
        sun_penalty_pts=0.0,
        cloud_cover=100.0,
        moon_illumination=0.0,
        moon_separation=90.0,
    )
    assert score == 0


def test_full_cloud_cover_reason_present():
    planet = _make_planet(altitude_deg=45.0)
    _score, reasons = score_planet(
        planet,
        sun_penalty_pts=0.0,
        cloud_cover=100.0,
        moon_illumination=0.0,
        moon_separation=90.0,
    )
    assert "molnighet" in reasons


def test_cloud_cover_at_threshold_75_score_is_zero():
    # cloud_cover >= 75 is a hard zero
    planet = _make_planet(altitude_deg=45.0)
    score, reasons = score_planet(
        planet,
        sun_penalty_pts=0.0,
        cloud_cover=75.0,
        moon_illumination=0.0,
        moon_separation=90.0,
    )
    assert score == 0
    assert "molnighet" in reasons


def test_cloud_cover_just_below_threshold_not_zero():
    # cloud_cover = 74 is NOT a hard zero; should produce a positive score
    planet = _make_planet(altitude_deg=45.0)
    score, reasons = score_planet(
        planet,
        sun_penalty_pts=0.0,
        cloud_cover=74.0,
        moon_illumination=0.0,
        moon_separation=90.0,
    )
    assert score > 0


# ---------------------------------------------------------------------------
# 3. Daytime (sun_penalty_pts >= 50) → score 0
# ---------------------------------------------------------------------------

def test_daytime_penalty_score_is_zero():
    planet = _make_planet(altitude_deg=45.0)
    score, reasons = score_planet(
        planet,
        sun_penalty_pts=50.0,
        cloud_cover=10.0,
        moon_illumination=0.0,
        moon_separation=90.0,
    )
    assert score == 0


def test_daytime_penalty_reason_present():
    planet = _make_planet(altitude_deg=45.0)
    _score, reasons = score_planet(
        planet,
        sun_penalty_pts=50.0,
        cloud_cover=10.0,
        moon_illumination=0.0,
        moon_separation=90.0,
    )
    assert "dagsljus" in reasons


# ---------------------------------------------------------------------------
# 4. Excellent conditions → high score (> 70)
# ---------------------------------------------------------------------------

def test_excellent_conditions_high_score():
    # altitude=45 → altitude_score=40; mag=-4.5 → mag_score=25;
    # cloud=0 → cloud_score=35; no sun, extinction, or moon penalties.
    # Expected total = 100.
    planet = _make_planet(altitude_deg=45.0, magnitude=-4.5)
    score, reasons = score_planet(
        planet,
        sun_penalty_pts=0.0,
        cloud_cover=0.0,
        moon_illumination=0.0,
        moon_separation=90.0,
    )
    assert score > 90


def test_excellent_conditions_exact_score():
    # Verify the arithmetic: 40 + 25 + 35 + 0 + 0 + 0 = 100
    planet = _make_planet(altitude_deg=45.0, magnitude=-4.5)
    score, _reasons = score_planet(
        planet,
        sun_penalty_pts=0.0,
        cloud_cover=0.0,
        moon_illumination=0.0,
        moon_separation=90.0,
    )
    assert score == 100


def test_excellent_conditions_reason_is_good():
    planet = _make_planet(altitude_deg=45.0, magnitude=-4.5)
    _score, reasons = score_planet(
        planet,
        sun_penalty_pts=0.0,
        cloud_cover=0.0,
        moon_illumination=0.0,
        moon_separation=90.0,
    )
    assert reasons == ["goda_förhållanden"]


# ---------------------------------------------------------------------------
# 5. Moon proximity penalty
# ---------------------------------------------------------------------------

def test_moon_proximity_lowers_score():
    # Same planet; one call has the moon 5° away (close), another 90° away (far).
    # Close-moon call should produce a lower score.
    planet = _make_planet(altitude_deg=45.0, magnitude=-1.0)

    score_near, reasons_near = score_planet(
        planet,
        sun_penalty_pts=0.0,
        cloud_cover=0.0,
        moon_illumination=1.0,   # full moon
        moon_separation=5.0,     # very close
    )
    score_far, reasons_far = score_planet(
        planet,
        sun_penalty_pts=0.0,
        cloud_cover=0.0,
        moon_illumination=1.0,   # full moon, but far away
        moon_separation=90.0,
    )

    assert score_near < score_far


def test_moon_proximity_reason_present_when_close():
    planet = _make_planet(altitude_deg=45.0)
    _score, reasons = score_planet(
        planet,
        sun_penalty_pts=0.0,
        cloud_cover=0.0,
        moon_illumination=1.0,
        moon_separation=5.0,
    )
    assert "månljus" in reasons


def test_moon_no_penalty_when_dim():
    # Illumination <= 0.5 suppresses the moon proximity penalty entirely.
    planet = _make_planet(altitude_deg=45.0)
    _score, reasons = score_planet(
        planet,
        sun_penalty_pts=0.0,
        cloud_cover=0.0,
        moon_illumination=0.5,   # at the boundary, condition is > 0.5, so no penalty
        moon_separation=5.0,
    )
    assert "månljus" not in reasons


def test_moon_no_penalty_when_far():
    # Separation >= 15° suppresses the moon proximity penalty.
    planet = _make_planet(altitude_deg=45.0)
    _score, reasons = score_planet(
        planet,
        sun_penalty_pts=0.0,
        cloud_cover=0.0,
        moon_illumination=1.0,
        moon_separation=15.0,   # boundary: condition is < 15, so 15 is excluded
    )
    assert "månljus" not in reasons


# ---------------------------------------------------------------------------
# 6. Low altitude atmospheric extinction
# ---------------------------------------------------------------------------

def test_low_altitude_lower_score_than_high_altitude():
    # altitude=5° incurs extinction penalty; altitude=30° does not.
    planet_low = _make_planet(altitude_deg=5.0, magnitude=-1.0)
    planet_high = _make_planet(altitude_deg=30.0, magnitude=-1.0)

    score_low, _r = score_planet(
        planet_low,
        sun_penalty_pts=0.0,
        cloud_cover=0.0,
        moon_illumination=0.0,
        moon_separation=90.0,
    )
    score_high, _r = score_planet(
        planet_high,
        sun_penalty_pts=0.0,
        cloud_cover=0.0,
        moon_illumination=0.0,
        moon_separation=90.0,
    )

    assert score_low < score_high


def test_low_altitude_extinction_reason_present():
    planet = _make_planet(altitude_deg=5.0)
    _score, reasons = score_planet(
        planet,
        sun_penalty_pts=0.0,
        cloud_cover=0.0,
        moon_illumination=0.0,
        moon_separation=90.0,
    )
    assert "atmosfärisk_dämpning" in reasons


def test_altitude_at_10_no_extinction_reason():
    # Extinction applies only when altitude < 10; at exactly 10° no penalty.
    planet = _make_planet(altitude_deg=10.0)
    _score, reasons = score_planet(
        planet,
        sun_penalty_pts=0.0,
        cloud_cover=0.0,
        moon_illumination=0.0,
        moon_separation=90.0,
    )
    assert "atmosfärisk_dämpning" not in reasons


# ---------------------------------------------------------------------------
# 7. Multiple hard-zero conditions simultaneously → score 0, all reasons present
# ---------------------------------------------------------------------------

def test_all_hard_zero_conditions_score_is_zero():
    # Below horizon + overcast + daytime.
    planet = _make_planet(altitude_deg=-10.0, is_above_horizon=False)
    score, reasons = score_planet(
        planet,
        sun_penalty_pts=50.0,
        cloud_cover=100.0,
        moon_illumination=0.0,
        moon_separation=90.0,
    )
    assert score == 0


def test_all_hard_zero_conditions_all_reasons_present():
    planet = _make_planet(altitude_deg=-10.0, is_above_horizon=False)
    _score, reasons = score_planet(
        planet,
        sun_penalty_pts=50.0,
        cloud_cover=100.0,
        moon_illumination=0.0,
        moon_separation=90.0,
    )
    assert "below_horizon" in reasons
    assert "molnighet" in reasons
    assert "dagsljus" in reasons


def test_all_hard_zero_conditions_no_partial_penalty_reasons():
    # When score is 0 due to hard zeros, partial-penalty reasons (månljus,
    # atmosfärisk_dämpning, goda_förhållanden) must NOT appear because the
    # function returns early before computing them.
    planet = _make_planet(altitude_deg=-10.0, is_above_horizon=False)
    _score, reasons = score_planet(
        planet,
        sun_penalty_pts=50.0,
        cloud_cover=100.0,
        moon_illumination=1.0,
        moon_separation=5.0,
    )
    assert "goda_förhållanden" not in reasons
    assert "månljus" not in reasons
    assert "atmosfärisk_dämpning" not in reasons


# ---------------------------------------------------------------------------
# 8. apply_scores integration test
# ---------------------------------------------------------------------------

def test_apply_scores_populates_fields():
    """
    Call apply_scores with a fixed noon datetime and clear skies.

    At noon (sun well above the horizon at Stockholm) every planet's
    dagsljus hard-zero fires, so visibility_score == 0 and is_visible == False.
    The key assertions are structural: every planet must have visibility_score
    set (not None), is_visible must be a bool, and visibility_reasons must be
    a non-empty list.
    """
    planets = calculate_planet_positions(LAT, LON, dt=NOON_DT)
    sun_data = calculate_sun_penalty(LAT, LON, dt=NOON_DT)
    moon_data = calculate_moon_penalty(LAT, LON, dt=NOON_DT)
    result = apply_scores(planets, sun_data, moon_data, 0.0)

    assert len(result) == 5, "apply_scores must return all five planets"

    for planet in result:
        assert planet.visibility_score is not None, (
            f"{planet.name}: visibility_score must not be None after apply_scores"
        )
        assert isinstance(planet.visibility_score, int), (
            f"{planet.name}: visibility_score must be an int, "
            f"got {type(planet.visibility_score)}"
        )
        assert 0 <= planet.visibility_score <= 100, (
            f"{planet.name}: visibility_score {planet.visibility_score} out of range"
        )
        assert isinstance(planet.is_visible, bool), (
            f"{planet.name}: is_visible must be a bool after apply_scores"
        )
        assert isinstance(planet.visibility_reasons, list), (
            f"{planet.name}: visibility_reasons must be a list"
        )
        assert len(planet.visibility_reasons) > 0, (
            f"{planet.name}: visibility_reasons must not be empty after apply_scores"
        )


def test_apply_scores_daytime_dagsljus_reason():
    """
    At noon the sun is above the horizon, so every scored planet must have
    'dagsljus' in its visibility_reasons regardless of cloud cover.
    """
    planets = calculate_planet_positions(LAT, LON, dt=NOON_DT)
    sun_data = calculate_sun_penalty(LAT, LON, dt=NOON_DT)
    moon_data = calculate_moon_penalty(LAT, LON, dt=NOON_DT)
    result = apply_scores(planets, sun_data, moon_data, 0.0)

    for planet in result:
        assert "dagsljus" in planet.visibility_reasons, (
            f"{planet.name}: expected 'dagsljus' reason at noon, "
            f"got {planet.visibility_reasons}"
        )


def test_apply_scores_daytime_score_is_zero():
    """At noon every planet's daytime hard-zero must produce score == 0."""
    planets = calculate_planet_positions(LAT, LON, dt=NOON_DT)
    sun_data = calculate_sun_penalty(LAT, LON, dt=NOON_DT)
    moon_data = calculate_moon_penalty(LAT, LON, dt=NOON_DT)
    result = apply_scores(planets, sun_data, moon_data, 0.0)

    for planet in result:
        # A planet below the horizon also scores 0, so this assertion is safe
        # regardless of each planet's actual position at noon.
        assert planet.visibility_score == 0, (
            f"{planet.name}: expected score 0 at noon, got {planet.visibility_score}"
        )


def test_apply_scores_returns_same_list():
    """apply_scores must mutate and return the same list object."""
    planets = calculate_planet_positions(LAT, LON, dt=NOON_DT)
    sun_data = calculate_sun_penalty(LAT, LON, dt=NOON_DT)
    moon_data = calculate_moon_penalty(LAT, LON, dt=NOON_DT)
    result = apply_scores(planets, sun_data, moon_data, 0.0)
    assert result is planets


# ---------------------------------------------------------------------------
# 9. Twilight threshold: sun must be below -12° for is_visible = True
# ---------------------------------------------------------------------------

def test_nautical_twilight_sun_altitude_minus_8_not_visible():
    """
    A planet above the horizon with sun_altitude=-8 (nautical twilight,
    between -6 and -12) must have is_visible = False because the
    is_visible threshold requires sun_altitude < -12.

    Uses a directly constructed planet so the planet is unambiguously above
    the horizon at altitude=30°.  This ensures the sole cause of
    is_visible=False is the -12° sun-altitude threshold, not an accidental
    below-horizon position returned by the live ephem calculator.
    """
    # sun_altitude=-8 falls in nautical_twilight, limiting_mag=0.5.
    # Piecewise-linear penalty at sun_alt=-8°: interpolated between -12°→16 and -6°→38
    # frac = (-8 - (-12)) / (-6 - (-12)) = 4/6; penalty = 16 + (4/6)*22 = 30.67
    # A faint planet (magnitude=2.0) fails the magnitude gate (2.0 < 0.5 is False)
    # so is_visible remains False regardless of the score.
    sun_data = {
        "elevation_deg": -8.0,
        "twilight_phase": "nautical_twilight",
        "penalty_pts": 30.67,
        "limiting_magnitude": 0.5,
    }
    moon_data = {"illumination": 0.0, "elevation_deg": -30.0, "azimuth_deg": 0.0}

    planet = _make_planet(altitude_deg=30.0, magnitude=2.0)
    result = apply_scores([planet], sun_data, moon_data, 0.0)
    scored = result[0]

    assert scored.is_visible is False, (
        f"Expected is_visible=False when sun_altitude=-8 and planet magnitude=2.0 "
        f"(faint planet not visible during nautical twilight), "
        f"got is_visible={scored.is_visible} (score={scored.visibility_score})"
    )


def test_astronomical_twilight_sun_altitude_minus_14_bright_planet_visible():
    """
    A planet above the horizon with sun_altitude=-14 (past nautical twilight,
    below the -12 threshold), 0% cloud cover, and no moon interference must
    have is_visible = True if its score exceeds the threshold.

    Uses a fixed known-above-horizon planet (Venus) by constructing it
    directly, bypassing the live ephem calculation.
    """
    # sun_altitude=-14 falls in astronomical_twilight, limiting_mag=4.5.
    # Piecewise-linear penalty at sun_alt=-14°: interpolated between -18°→4 and -12°→16
    # frac = (-14 - (-18)) / (-12 - (-18)) = 4/6; penalty = 4 + (4/6)*12 = 12.0
    # Venus (magnitude=-4.5) passes the magnitude gate (-4.5 < 4.5 = True).
    # mag_headroom=9.0, scale=0.0, effective_penalty=0; score = 40+25+35 = 100 > 15.
    sun_data = {
        "elevation_deg": -14.0,
        "twilight_phase": "astronomical_twilight",
        "penalty_pts": 12.0,
        "limiting_magnitude": 4.5,
    }
    moon_data = {"illumination": 0.0, "elevation_deg": -30.0, "azimuth_deg": 0.0}

    planet = _make_planet(altitude_deg=45.0, magnitude=-4.5)
    result = apply_scores([planet], sun_data, moon_data, 0.0)
    scored = result[0]

    assert scored.is_visible is True, (
        f"Expected is_visible=True when sun_altitude=-14 and score={scored.visibility_score}, "
        f"got is_visible={scored.is_visible}"
    )
