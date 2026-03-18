"""
Planet visibility scoring module.

Combines planet position data with sun/moon state and cloud cover to produce
a 0–100 integer visibility score for each planet and an aggregate tonight score.
"""

from typing import List, Tuple

from ..models.planet import PlanetPosition
from ..utils.moon import get_moon_angular_separation


def score_planet(
    planet: PlanetPosition,
    sun_penalty_pts: float,
    cloud_cover: float,
    moon_illumination: float,
    moon_separation: float,
    limiting_mag: float = 6.5,
) -> Tuple[int, List[str]]:
    """
    Compute a 0–100 visibility score for a single planet, with reason keys.

    Collects ALL applicable hard-zero conditions before returning early, so
    a planet that is both below the horizon and in daylight will report both
    "below_horizon" and "dagsljus".

    Hard-zero conditions (score is forced to 0):
      - planet altitude <= 0  → "below_horizon"
      - cloud cover >= 75 %   → "molnighet"
      - sun_penalty_pts >= 50 (daylight) → "dagsljus"

    Partial-penalty reason keys (collected when score > 0):
      - cloud cover in [25, 75) → "molnighet"
      - any effective sun/twilight penalty > 0 → "dagsljus"
      - atmospheric extinction active (altitude < 10°) → "atmosfärisk_dämpning"
      - moon proximity penalty active → "månljus"

    Good-conditions fallback: "goda_förhållanden" when no reason was collected.

    The sun penalty is magnitude-aware: during twilight (0 < sun_penalty_pts < 50)
    a planet whose apparent magnitude is already brighter than the sky background
    (large mag_headroom) receives a reduced effective penalty.  The scale factor
    is derived from how much headroom the planet has relative to the limiting
    magnitude:

        mag_headroom         = limiting_mag - planet.magnitude
        scale                = clamp(1.0 - mag_headroom / 5.0, 0.0, 1.0)
        effective_penalty    = sun_penalty_pts * scale

    Examples:
      Venus (mag −4.0), limiting_mag +1.0 → headroom=5.0, scale=0.0, penalty≈0
      Saturn (mag +0.5), limiting_mag +1.0 → headroom=0.5, scale=0.9, penalty≈90%

    Args:
        planet:            Computed position data for the planet.
        sun_penalty_pts:   Sun/twilight penalty as a positive number (0–50),
                           sourced directly from calculate_sun_penalty()["penalty_pts"].
        cloud_cover:       Cloud cover percentage 0–100.
        moon_illumination: Moon illumination fraction 0.0–1.0.
        moon_separation:   Angular separation between moon and planet in degrees.
        limiting_mag:      Faintest naked-eye magnitude visible at zenith for the
                           current sun altitude, from calculate_sun_penalty()
                           ["limiting_magnitude"].  Defaults to 6.5 (full dark sky)
                           so callers that omit it get no magnitude-aware scaling.

    Returns:
        Tuple of (score, reasons) where score is an integer in range 0–100 and
        reasons is a list of string reason keys.
    """
    reasons: List[str] = []

    # --- Collect ALL hard-zero conditions before deciding to return early ---
    if planet.altitude_deg <= 0:
        reasons.append("below_horizon")

    if cloud_cover >= 75:
        reasons.append("molnighet")

    # Daytime is a hard zero: sun_penalty_pts == 50 means the sun is above the
    # horizon.  (calculate_sun_penalty caps the penalty at 50.)
    # This check uses the ORIGINAL sun_penalty_pts, never the scaled value.
    if sun_penalty_pts >= 50:
        reasons.append("dagsljus")

    if reasons:
        return (0, reasons)

    # --- Magnitude-aware sun penalty ---
    # Scale the penalty by how easily the planet overcomes the sky brightness.
    # A planet much brighter than the sky limit (large positive headroom) gets
    # a near-zero penalty; a faint planet near the sky limit gets the full one.
    # The daylight hard-zero above already handles sun_penalty_pts >= 50, so
    # here we are in the twilight / darkness regime (0 <= sun_penalty_pts < 50).
    mag_headroom = limiting_mag - planet.magnitude
    scale = max(0.0, min(1.0, 1.0 - mag_headroom / 5.0))
    effective_sun_penalty_pts = sun_penalty_pts * scale

    # --- Altitude component (0–40 pts) ---
    # Linear ramp: 0 pts at 0°, 40 pts at 45°; clamped to 40 above 45°.
    altitude_score = min(40.0, (planet.altitude_deg / 45.0) * 40.0)

    # --- Magnitude component (0–25 pts) ---
    # -4.5 → 25 pts; +1.0 → 10 pts; linear interpolation; clamp to [0, 25].
    # Slope: (25 - 10) / (-4.5 - 1.0) = 15 / -5.5 ≈ -2.727 pts per magnitude unit
    # At mag = -4.5: pts = 25; at mag = 1.0: pts = 10; dimmer scales down further.
    mag_score = 25.0 + (planet.magnitude - (-4.5)) * (10.0 - 25.0) / (1.0 - (-4.5))
    mag_score = max(0.0, min(25.0, mag_score))

    # --- Cloud cover component (0–35 pts) ---
    if cloud_cover < 25:
        cloud_score = 35.0
    elif cloud_cover < 50:
        cloud_score = 23.0
    elif cloud_cover < 75:
        cloud_score = 12.0
    else:
        cloud_score = 0.0  # unreachable here; handled by hard-zero above

    # --- Sun penalty (-50 to 0) ---
    # Use the magnitude-aware effective penalty; negate so it subtracts from total.
    sun_penalty = -effective_sun_penalty_pts

    # --- Atmospheric extinction penalty (-10 to 0) ---
    # Linear from -10 at 0° altitude to 0 at 10° altitude; 0 above 10°.
    if planet.altitude_deg >= 10.0:
        extinction_penalty = 0.0
    else:
        extinction_penalty = -10.0 * (1.0 - planet.altitude_deg / 10.0)

    # --- Moon proximity penalty (-10 to 0) ---
    # Applied only when moon is bright (>0.5) and close (<15°) to the planet.
    if moon_separation < 15 and moon_illumination > 0.5:
        moon_penalty = -10.0 * (1.0 - moon_separation / 15.0) * moon_illumination
        moon_penalty = max(-10.0, min(0.0, moon_penalty))
    else:
        moon_penalty = 0.0

    total = (
        altitude_score
        + mag_score
        + cloud_score
        + sun_penalty
        + extinction_penalty
        + moon_penalty
    )

    score = int(max(0, min(100, round(total))))

    # --- Collect partial-penalty reason keys ---
    if cloud_cover >= 25:
        # cloud_cover < 75 is guaranteed here (hard-zero already handled >=75)
        reasons.append("molnighet")

    if effective_sun_penalty_pts > 0:
        # sun_penalty_pts < 50 is guaranteed here (hard-zero already handled >=50)
        reasons.append("dagsljus")

    if extinction_penalty < 0:
        reasons.append("atmosfärisk_dämpning")

    if moon_penalty < 0:
        reasons.append("månljus")

    if not reasons:
        reasons.append("goda_förhållanden")

    return (score, reasons)


def score_tonight(planets: List[PlanetPosition]) -> int:
    """
    Compute an aggregate 0–100 score for tonight's sky.

    Averages the visibility_score across ALL five planets, treating below-horizon
    planets as 0.  This avoids inflating the score when only one planet happens
    to be above the horizon.  Returns 0 when no planet has been scored yet.

    Precondition: apply_scores() must have been called before this function so
    that visibility_score is populated on every planet in the list.  Planets
    whose visibility_score is still None are excluded from the average, which
    will produce an incorrect result if apply_scores() was not called first.

    Args:
        planets: List of PlanetPosition objects with visibility_score already set.

    Returns:
        Integer in range 0–100.
    """
    scored = [p for p in planets if p.visibility_score is not None]
    if not scored:
        return 0
    # Include all planets; below-horizon ones contribute 0 via score_planet.
    total = sum(p.visibility_score for p in scored)
    average = total / len(scored)
    return int(max(0, min(100, round(average))))


def apply_scores(
    planets: List[PlanetPosition],
    sun_data: dict,
    moon_data: dict,
    cloud_cover: float,
) -> List[PlanetPosition]:
    """
    Compute and attach visibility scores to every planet in the list.

    Accepts pre-computed sun and moon data dicts (as returned by
    calculate_sun_penalty() and calculate_moon_penalty() respectively) and
    calls score_planet() for each planet.  Mutates each PlanetPosition in
    place by setting visibility_score, is_visible, and visibility_reasons,
    then returns the list.

    A planet is declared visible when:
        - altitude_deg > 0
        - visibility_score > 15
        - planet.magnitude < limiting_mag  (planet is brighter than the sky limit)

    The limiting_mag is taken from sun_data["limiting_magnitude"] as returned by
    calculate_sun_penalty().  It reflects how faint a zenith object can be and
    still be seen naked-eye at the current sun altitude.

    Args:
        planets:     List of PlanetPosition objects from calculate_planet_positions().
        sun_data:    Dict returned by calculate_sun_penalty(), containing at
                     minimum "elevation_deg", "penalty_pts", and "limiting_magnitude".
        moon_data:   Dict returned by calculate_moon_penalty(), containing at
                     minimum "illumination", "elevation_deg", and "azimuth_deg".
        cloud_cover: Cloud cover percentage 0–100.

    Returns:
        The same list with visibility_score, is_visible, and visibility_reasons
        populated on each item.
    """
    sun_penalty_pts = sun_data["penalty_pts"]
    limiting_mag: float = sun_data["limiting_magnitude"]

    moon_illumination = moon_data["illumination"]
    moon_alt_deg = moon_data["elevation_deg"]
    moon_az_deg = moon_data["azimuth_deg"]

    for planet in planets:
        separation = get_moon_angular_separation(
            moon_az_deg,
            moon_alt_deg,
            planet.azimuth_deg,
            planet.altitude_deg,
        )

        score, reasons = score_planet(
            planet,
            sun_penalty_pts=sun_penalty_pts,
            cloud_cover=cloud_cover,
            moon_illumination=moon_illumination,
            moon_separation=separation,
            limiting_mag=limiting_mag,
        )

        planet.visibility_score = score
        planet.visibility_reasons = reasons
        planet.is_visible = (
            planet.altitude_deg > 0
            and score > 15
            and planet.magnitude < limiting_mag
        )

    return planets
