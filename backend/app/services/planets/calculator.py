"""
Planet position calculator using the ephem library.

Computes altitude, azimuth, apparent magnitude, constellation, rise/transit/set
times, and compass direction for the five naked-eye planets (Mercury, Venus,
Mars, Jupiter, Saturn) at a given location and UTC time.
"""

import ephem
import math
from datetime import datetime, timezone
from typing import List, Optional

from ...models.planet import PlanetPosition, PLANET_NAMES_SV, azimuth_to_compass


def _ephem_date_to_iso(result) -> str:
    """Convert an ephem.Date value to an ISO 8601 UTC string."""
    return ephem.Date(result).datetime().strftime('%Y-%m-%dT%H:%M:%SZ')


def _compute_rise_time(observer: ephem.Observer, planet_body, dt: datetime) -> Optional[str]:
    """
    Return next rise time as ISO 8601 UTC string, or None if always up or never up.

    observer.date is set to dt for consistency with the other helpers; ephem's next_rising does not mutate the observer.
    """
    observer.date = dt
    try:
        result = observer.next_rising(planet_body)
        return _ephem_date_to_iso(result)
    except ephem.AlwaysUpError:
        return None
    except ephem.NeverUpError:
        return None


def _compute_set_time(observer: ephem.Observer, planet_body, dt: datetime) -> Optional[str]:
    """
    Return next set time as ISO 8601 UTC string, or None if always up or never up.

    observer.date is set to dt for consistency with the other helpers; ephem's next_setting does not mutate the observer.
    """
    observer.date = dt
    try:
        result = observer.next_setting(planet_body)
        return _ephem_date_to_iso(result)
    except ephem.AlwaysUpError:
        return None
    except ephem.NeverUpError:
        return None


def _compute_transit_time(observer: ephem.Observer, planet_body, dt: datetime) -> Optional[str]:
    """
    Return next transit time as ISO 8601 UTC string, or None if always up, never up, or circumpolar.

    observer.date is set to dt for consistency with the rise/set helpers; ephem's next_transit does not mutate the observer.
    """
    observer.date = dt
    try:
        result = observer.next_transit(planet_body)
        return _ephem_date_to_iso(result)
    except ephem.AlwaysUpError:
        return None
    except ephem.NeverUpError:
        return None
    except ephem.CircumpolarError:
        return None


def calculate_planet_positions(lat: float, lon: float, dt: datetime = None) -> List[PlanetPosition]:
    """
    Calculate position and timing data for the five naked-eye planets.

    Uses ephem to compute altitude, azimuth, apparent magnitude, constellation,
    and rise/transit/set times for Mercury, Venus, Mars, Jupiter, and Saturn at
    the given WGS-84 location and UTC time.

    Args:
        lat: Latitude in decimal degrees (positive = North).
        lon: Longitude in decimal degrees (positive = East).
        dt:  UTC datetime for the calculation. If None, uses the current UTC time.
             Must be timezone-naive or timezone-aware UTC; ephem works with naive UTC.

    Returns:
        A list of five PlanetPosition objects in Mercury → Venus → Mars →
        Jupiter → Saturn order.
    """
    if dt is None:
        dt = datetime.now(timezone.utc).replace(tzinfo=None)
    else:
        # ephem does not accept tzinfo-aware datetimes
        if dt.tzinfo is not None:
            dt = dt.astimezone(timezone.utc).replace(tzinfo=None)

    # Base observer used for position calculation only.
    observer = ephem.Observer()
    observer.lat = str(lat)
    observer.lon = str(lon)
    observer.date = dt
    # Disable atmospheric refraction for raw geometric altitude.
    observer.pressure = 0

    planet_classes = [
        ephem.Mercury,
        ephem.Venus,
        ephem.Mars,
        ephem.Jupiter,
        ephem.Saturn,
    ]

    positions: List[PlanetPosition] = []

    for planet_class in planet_classes:
        planet_body = planet_class()
        planet_body.compute(observer)

        altitude_deg = round(math.degrees(float(planet_body.alt)), 1)
        azimuth_deg = round(math.degrees(float(planet_body.az)), 1) % 360
        magnitude = round(float(planet_body.mag), 2)

        # ephem.constellation returns (abbreviation, full_name)
        _abbrev, constellation = ephem.constellation(planet_body)

        direction = azimuth_to_compass(azimuth_deg)
        is_above_horizon = altitude_deg > 0

        name = type(planet_body).__name__
        name_sv = PLANET_NAMES_SV[name]

        # A fresh observer is used for each rise/transit/set call because
        # those methods mutate observer.date.  Resetting before each call
        # is the safest approach and avoids accumulated drift between calls.
        timing_observer = ephem.Observer()
        timing_observer.lat = str(lat)
        timing_observer.lon = str(lon)
        timing_observer.pressure = 0

        rise_time = _compute_rise_time(timing_observer, planet_body, dt)
        set_time = _compute_set_time(timing_observer, planet_body, dt)
        transit_time = _compute_transit_time(timing_observer, planet_body, dt)

        positions.append(PlanetPosition(
            name=name,
            name_sv=name_sv,
            altitude_deg=altitude_deg,
            azimuth_deg=azimuth_deg,
            direction=direction,
            magnitude=magnitude,
            constellation=constellation,
            rise_time=rise_time,
            set_time=set_time,
            transit_time=transit_time,
            is_above_horizon=is_above_horizon,
        ))

    return positions
