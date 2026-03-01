"""
Planet visibility scoring module.

Combines planet position data with sun/moon state and cloud cover to produce
a 0–100 integer visibility score for each planet and an aggregate tonight score.
"""

from datetime import datetime
from typing import List

from ..models.planet import PlanetPosition
from ..utils.sun import calculate_sun_penalty
from ..utils.moon import calculate_moon_penalty, get_moon_angular_separation


def score_planet(
    planet: PlanetPosition,
    sun_penalty_pts: float,
    cloud_cover: float,
    moon_illumination: float,
    moon_separation: float,
) -> int:
    """
    Compute a 0–100 visibility score for a single planet.

    Returns 0 immediately when:
      - the planet is at or below the horizon,
      - cloud cover is 75 % or higher (matches the ">75% → 0 pts" cloud table
        boundary; at ≥75% the cloud component is already 0, so the total score
        can only ever be 0 or negative),
      - the sun is above the horizon (sun_penalty_pts == 50.0, i.e. daylight).

    Args:
        planet:            Computed position data for the planet.
        sun_penalty_pts:   Sun/twilight penalty as a positive number (0–50),
                           sourced directly from calculate_sun_penalty()["penalty_pts"].
        cloud_cover:       Cloud cover percentage 0–100.
        moon_illumination: Moon illumination fraction 0.0–1.0.
        moon_separation:   Angular separation between moon and planet in degrees.

    Returns:
        Integer score in range 0–100.
    """
    if planet.altitude_deg <= 0:
        return 0

    # Cloud cover ≥75 % maps to 0 pts in the cloud table, so the total can only
    # be 0 or negative — return early for consistency.
    if cloud_cover >= 75:
        return 0

    # Daytime is a hard zero: no planet observation is possible.
    if sun_penalty_pts >= 50:
        return 0

    # --- Altitude component (0–30 pts) ---
    # Linear ramp: 0 pts at 0°, 30 pts at 45°; clamped to 30 above 45°.
    altitude_score = min(30.0, (planet.altitude_deg / 45.0) * 30.0)

    # --- Magnitude component (0–20 pts) ---
    # -4.5 → 20 pts; +1.0 → 10 pts; linear interpolation; clamp to [0, 20].
    # Slope: (20 - 10) / (-4.5 - 1.0) = 10 / -5.5 ≈ -1.818 pts per magnitude unit
    # At mag = -4.5: pts = 20; at mag = 1.0: pts = 10; dimmer scales down further.
    mag_score = 20.0 + (planet.magnitude - (-4.5)) * (10.0 - 20.0) / (1.0 - (-4.5))
    mag_score = max(0.0, min(20.0, mag_score))

    # --- Cloud cover component (0–30 pts) ---
    if cloud_cover < 25:
        cloud_score = 30.0
    elif cloud_cover < 50:
        cloud_score = 20.0
    elif cloud_cover < 75:
        cloud_score = 10.0
    else:
        cloud_score = 0.0

    # --- Sun penalty (-50 to 0) ---
    # sun_penalty_pts is a positive number (0–50) supplied by the caller;
    # negate it so it subtracts from the total.
    sun_penalty = -sun_penalty_pts

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

    return int(max(0, min(100, round(total))))


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
    lat: float,
    lon: float,
    cloud_cover: float,
    dt: datetime = None,
) -> List[PlanetPosition]:
    """
    Compute and attach visibility scores to every planet in the list.

    Retrieves sun and moon data for the given location and time, then calls
    score_planet() for each planet.  Mutates each PlanetPosition in place by
    setting visibility_score and is_visible, then returns the list.

    A planet is declared visible when:
        - altitude_deg > 0
        - visibility_score > 15
        - sun_altitude < -6  (nautical twilight or darker)

    Args:
        planets:     List of PlanetPosition objects from calculate_planet_positions().
        lat:         Observer latitude in decimal degrees.
        lon:         Observer longitude in decimal degrees.
        cloud_cover: Cloud cover percentage 0–100.
        dt:          UTC datetime for sun/moon calculations.  Defaults to now.

    Returns:
        The same list with visibility_score and is_visible populated on each item.
    """
    sun_data = calculate_sun_penalty(lat, lon, dt)
    sun_altitude = sun_data["elevation_deg"]
    sun_penalty_pts = sun_data["penalty_pts"]

    moon_data = calculate_moon_penalty(lat, lon, dt)
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

        score = score_planet(
            planet,
            sun_penalty_pts=sun_penalty_pts,
            cloud_cover=cloud_cover,
            moon_illumination=moon_illumination,
            moon_separation=separation,
        )

        planet.visibility_score = score
        planet.is_visible = (
            planet.altitude_deg > 0
            and score > 15
            and sun_altitude < -6
        )

    return planets
