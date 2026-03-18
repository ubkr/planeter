"""
Tests for twilight-dependent limiting magnitude and magnitude-aware scoring.

Group A: limiting_magnitude() function from app.utils.sun
Group B: score_planet() magnitude-aware sun penalty
Group C: apply_scores() magnitude-dependent is_visible flag

All tests are synchronous unit tests with no network calls and no ephem
side-effects (except for the function under test in Group A, which is a pure
piecewise-linear calculation driven by anchor tables — no ephem involved).
"""

from app.models.planet import PlanetPosition
from app.services.scoring import apply_scores, score_planet
from app.utils.sun import limiting_magnitude


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def _make_planet(**overrides) -> PlanetPosition:
    """
    Return a PlanetPosition with sensible defaults, overriding any fields
    supplied by the caller.  Defaults represent a well-placed planet
    (altitude 45°, magnitude -1.0, above the horizon).
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


def _nautical_twilight_sun_data() -> dict:
    """
    Return a sun_data dict representing nautical twilight at sun_alt=-8°.

    All keys that apply_scores() reads are included.
    """
    return {
        "elevation_deg": -8.0,
        "twilight_phase": "nautical_twilight",
        # Piecewise-linear penalty at sun_alt=-8°: interpolated between -12°→16 and -6°→38
        # frac = (-8 - (-12)) / (-6 - (-12)) = 4/6; penalty = 16 + (4/6)*22 = 30.67
        "penalty_pts": round(16 + (4 / 6) * 22, 2),
        "limiting_magnitude": 0.5,
    }


def _full_darkness_sun_data() -> dict:
    """
    Return a sun_data dict representing full darkness at sun_alt=-20°.

    All keys that apply_scores() reads are included.
    """
    return {
        "elevation_deg": -20.0,
        "twilight_phase": "darkness",
        "penalty_pts": 0.0,
        "limiting_magnitude": 6.5,
    }


def _below_horizon_moon_data() -> dict:
    """
    Return a moon_data dict with the moon well below the horizon.
    apply_scores() reads: illumination, elevation_deg, azimuth_deg.
    """
    return {
        "illumination": 0.1,
        "elevation_deg": -30.0,
        "azimuth_deg": 180.0,
    }


# ---------------------------------------------------------------------------
# Group A: limiting_magnitude() function
# ---------------------------------------------------------------------------

def test_limiting_magnitude_daylight_returns_minus5():
    # Sun at horizon (0°): sky is effectively daytime — clamp_high = -5.0.
    result = limiting_magnitude(0)
    assert abs(result - (-5.0)) <= 0.1, (
        f"Expected limiting_magnitude(0) ≈ -5.0, got {result}"
    )


def test_limiting_magnitude_civil_twilight_end():
    # Sun at -6°: civil twilight boundary; anchor value is -1.0.
    result = limiting_magnitude(-6)
    assert -1.5 <= result <= -0.5, (
        f"Expected limiting_magnitude(-6) in [-1.5, -0.5], got {result}"
    )


def test_limiting_magnitude_nautical_twilight_end():
    # Sun at -12°: nautical twilight boundary; anchor value is 3.5.
    result = limiting_magnitude(-12)
    assert 3.0 <= result <= 4.0, (
        f"Expected limiting_magnitude(-12) in [3.0, 4.0], got {result}"
    )


def test_limiting_magnitude_astronomical_twilight_end():
    # Sun at -18°: astronomical twilight boundary; anchor value is 6.0.
    result = limiting_magnitude(-18)
    assert 5.5 <= result <= 6.5, (
        f"Expected limiting_magnitude(-18) in [5.5, 6.5], got {result}"
    )


def test_limiting_magnitude_full_darkness_clamp():
    # Sun well below -18°: clamp_low = 6.5 applies.
    result = limiting_magnitude(-30)
    assert result <= 6.5, (
        f"Expected limiting_magnitude(-30) ≤ 6.5 (clamped), got {result}"
    )


def test_limiting_magnitude_monotone_increasing():
    # As the sun descends (altitude decreases), the sky darkens and more
    # stars become visible, so limiting_magnitude must be non-decreasing.
    altitudes = [0.0 - 0.5 * i for i in range(51)]  # 0.0, -0.5, ..., -25.0
    values = [limiting_magnitude(a) for a in altitudes]
    for i in range(1, len(values)):
        assert values[i] >= values[i - 1] - 1e-9, (
            f"limiting_magnitude not non-decreasing: "
            f"alt={altitudes[i - 1]:.1f} → {values[i - 1]:.4f}, "
            f"alt={altitudes[i]:.1f} → {values[i]:.4f}"
        )


def test_limiting_magnitude_no_discontinuities():
    # The piecewise linear function must be continuous: no adjacent pair of
    # values (sampled at 0.1° steps) may differ by more than 0.5 mag.
    altitudes = [0.0 - 0.1 * i for i in range(201)]  # 0.0, -0.1, ..., -20.0
    values = [limiting_magnitude(a) for a in altitudes]
    for i in range(1, len(values)):
        diff = abs(values[i] - values[i - 1])
        assert diff < 0.5, (
            f"Discontinuity detected: "
            f"alt={altitudes[i - 1]:.1f} → {values[i - 1]:.4f}, "
            f"alt={altitudes[i]:.1f} → {values[i]:.4f}, diff={diff:.4f}"
        )


# ---------------------------------------------------------------------------
# Group B: score_planet() magnitude-aware penalty
# ---------------------------------------------------------------------------

# Shared conditions for Group B: altitude=30, cloud=10, moon weak and distant.
_GROUP_B_COMMON = dict(
    altitude_deg=30.0,
    azimuth_deg=180.0,
    is_above_horizon=True,
)
_GROUP_B_SCORE_KWARGS = dict(
    cloud_cover=10.0,
    moon_illumination=0.2,
    moon_separation=45.0,
    # Piecewise-linear penalty at sun_alt=-8°: interpolated between -12°→16 and -6°→38
    # frac = (-8 - (-12)) / (-6 - (-12)) = 4/6; penalty = 16 + (4/6)*22 = 30.67
    sun_penalty_pts=round(16 + (4 / 6) * 22, 2),
    limiting_mag=0.5,
)


def test_score_venus_higher_than_saturn_at_same_twilight():
    # Venus is much brighter than the sky limit (large mag_headroom) so the
    # effective sun penalty is near zero.  Saturn is close to the sky limit
    # so it receives nearly the full penalty.
    venus = _make_planet(name="Venus", name_sv="Venus", magnitude=-4.5, **_GROUP_B_COMMON)
    saturn = _make_planet(name="Saturn", name_sv="Saturnus", magnitude=0.5, **_GROUP_B_COMMON)

    venus_score, _ = score_planet(venus, **_GROUP_B_SCORE_KWARGS)
    saturn_score, _ = score_planet(saturn, **_GROUP_B_SCORE_KWARGS)

    assert venus_score > saturn_score, (
        f"Expected Venus score ({venus_score}) > Saturn score ({saturn_score}) "
        f"at nautical twilight with sun_penalty_pts=20, limiting_mag=0.5"
    )


def test_magnitude_aware_no_effect_in_full_darkness():
    # With sun_penalty_pts=0.0 (full darkness), the effective penalty is
    # sun_penalty_pts * scale = 0 * anything = 0 for every planet.
    # Changing limiting_mag must not introduce any penalty.
    venus = _make_planet(name="Venus", name_sv="Venus", magnitude=-4.5, **_GROUP_B_COMMON)
    saturn = _make_planet(name="Saturn", name_sv="Saturnus", magnitude=0.5, **_GROUP_B_COMMON)

    darkness_kwargs = dict(
        cloud_cover=10.0,
        moon_illumination=0.2,
        moon_separation=45.0,
        sun_penalty_pts=0.0,
        limiting_mag=1.0,
    )

    venus_score, venus_reasons = score_planet(venus, **darkness_kwargs)
    saturn_score, saturn_reasons = score_planet(saturn, **darkness_kwargs)

    # "dagsljus" must not appear because effective_sun_penalty_pts == 0.
    assert "dagsljus" not in venus_reasons, (
        f"Expected no 'dagsljus' reason for Venus in full darkness, "
        f"got reasons={venus_reasons}"
    )
    assert "dagsljus" not in saturn_reasons, (
        f"Expected no 'dagsljus' reason for Saturn in full darkness, "
        f"got reasons={saturn_reasons}"
    )


def test_daylight_hard_zero_unaffected_by_limiting_mag():
    # sun_penalty_pts=50.0 triggers the daytime hard-zero before any
    # magnitude-aware scaling.  Changing limiting_mag must not rescue any planet.
    venus = _make_planet(name="Venus", name_sv="Venus", magnitude=-4.5, **_GROUP_B_COMMON)
    jupiter = _make_planet(name="Jupiter", name_sv="Jupiter", magnitude=-2.2, **_GROUP_B_COMMON)

    daylight_kwargs = dict(
        cloud_cover=10.0,
        moon_illumination=0.0,
        moon_separation=90.0,
        sun_penalty_pts=50.0,
        limiting_mag=99.0,  # extreme value: must have no effect on the hard-zero
    )

    venus_score, venus_reasons = score_planet(venus, **daylight_kwargs)
    jupiter_score, jupiter_reasons = score_planet(jupiter, **daylight_kwargs)

    assert venus_score == 0, (
        f"Expected Venus score=0 during daylight, got {venus_score}"
    )
    assert jupiter_score == 0, (
        f"Expected Jupiter score=0 during daylight, got {jupiter_score}"
    )
    assert "dagsljus" in venus_reasons
    assert "dagsljus" in jupiter_reasons


# ---------------------------------------------------------------------------
# Group C: apply_scores() magnitude-dependent visibility
# ---------------------------------------------------------------------------

def test_venus_visible_at_nautical_twilight():
    # Venus (mag=-3.8) is far brighter than the sky limit (0.5).
    # magnitude gate: -3.8 < 0.5 → True.
    # mag_headroom=4.3, scale=max(0,1-4.3/5)=0.14, effective_penalty≈2.8.
    # Score well above 15 → is_visible=True.
    sun_data = _nautical_twilight_sun_data()
    moon_data = _below_horizon_moon_data()

    venus = _make_planet(
        name="Venus", name_sv="Venus",
        altitude_deg=30.0, magnitude=-3.8,
        is_above_horizon=True,
    )
    result = apply_scores([venus], sun_data, moon_data, 10.0)
    scored = result[0]

    assert scored.is_visible is True, (
        f"Expected Venus is_visible=True at nautical twilight "
        f"(score={scored.visibility_score}, mag={venus.magnitude}, "
        f"limiting_mag={sun_data['limiting_magnitude']})"
    )


def test_jupiter_visible_at_nautical_twilight():
    # Jupiter (mag=-2.2) is brighter than the sky limit (0.5).
    # magnitude gate: -2.2 < 0.5 → True.
    # mag_headroom=2.7, scale=max(0,1-2.7/5)=0.46, effective_penalty≈9.2.
    # Score still well above 15 → is_visible=True.
    sun_data = _nautical_twilight_sun_data()
    moon_data = _below_horizon_moon_data()

    jupiter = _make_planet(
        name="Jupiter", name_sv="Jupiter",
        altitude_deg=30.0, magnitude=-2.2,
        is_above_horizon=True,
    )
    result = apply_scores([jupiter], sun_data, moon_data, 10.0)
    scored = result[0]

    assert scored.is_visible is True, (
        f"Expected Jupiter is_visible=True at nautical twilight "
        f"(score={scored.visibility_score}, mag={jupiter.magnitude}, "
        f"limiting_mag={sun_data['limiting_magnitude']})"
    )


def test_saturn_not_visible_at_nautical_twilight():
    # Saturn at magnitude=+0.5, limiting_mag=0.5.
    # magnitude gate: 0.5 < 0.5 → False → is_visible=False regardless of score.
    sun_data = _nautical_twilight_sun_data()
    moon_data = _below_horizon_moon_data()

    saturn = _make_planet(
        name="Saturn", name_sv="Saturnus",
        altitude_deg=30.0, magnitude=0.5,
        is_above_horizon=True,
    )
    result = apply_scores([saturn], sun_data, moon_data, 10.0)
    scored = result[0]

    assert scored.is_visible is False, (
        f"Expected Saturn is_visible=False at nautical twilight "
        f"(score={scored.visibility_score}, mag={saturn.magnitude}, "
        f"limiting_mag={sun_data['limiting_magnitude']}, "
        f"magnitude gate: {saturn.magnitude} < {sun_data['limiting_magnitude']} "
        f"= {saturn.magnitude < sun_data['limiting_magnitude']})"
    )


def test_all_planets_visible_in_full_darkness():
    # Full darkness: penalty_pts=0, limiting_mag=6.5.
    # All three planets are above the horizon at altitude=30 with clear skies.
    # magnitude gate: all magnitudes far below 6.5 → True.
    # Score: altitude=30 → 26.67, cloud=10 → 35, no penalties → well above 15.
    sun_data = _full_darkness_sun_data()
    moon_data = _below_horizon_moon_data()

    venus = _make_planet(
        name="Venus", name_sv="Venus",
        altitude_deg=30.0, magnitude=-3.8,
        is_above_horizon=True,
    )
    jupiter = _make_planet(
        name="Jupiter", name_sv="Jupiter",
        altitude_deg=30.0, magnitude=-2.2,
        is_above_horizon=True,
    )
    saturn = _make_planet(
        name="Saturn", name_sv="Saturnus",
        altitude_deg=30.0, magnitude=0.5,
        is_above_horizon=True,
    )

    result = apply_scores([venus, jupiter, saturn], sun_data, moon_data, 10.0)

    for planet in result:
        assert planet.is_visible is True, (
            f"Expected {planet.name} is_visible=True in full darkness "
            f"(score={planet.visibility_score}, mag={planet.magnitude}, "
            f"limiting_mag={sun_data['limiting_magnitude']})"
        )
