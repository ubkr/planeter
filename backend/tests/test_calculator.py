"""
Tests for the planet position calculator.

All tests use a fixed UTC datetime (2025-06-15T00:00:00) so results are
deterministic and no network calls are made.
"""

import re
from datetime import datetime

import pytest

from app.services.planets.calculator import calculate_planet_positions
from app.models.planet import PlanetPosition, azimuth_to_compass

FIXED_DT = datetime(2025, 6, 15, 0, 0)
LAT = 55.7
LON = 13.4

EXPECTED_NAMES = ["Mercury", "Venus", "Mars", "Jupiter", "Saturn"]

# ISO 8601 UTC pattern: YYYY-MM-DDTHH:MM:SSZ
_ISO8601_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")


def test_returns_five_planets():
    positions = calculate_planet_positions(LAT, LON, dt=FIXED_DT)
    assert len(positions) == 5
    assert [p.name for p in positions] == EXPECTED_NAMES


def test_all_positions_are_pydantic_models():
    positions = calculate_planet_positions(LAT, LON, dt=FIXED_DT)
    for planet in positions:
        assert isinstance(planet, PlanetPosition)


def test_altitude_in_valid_range():
    positions = calculate_planet_positions(LAT, LON, dt=FIXED_DT)
    for planet in positions:
        assert -90 <= planet.altitude_deg <= 90, (
            f"{planet.name}: altitude_deg {planet.altitude_deg} is out of [-90, 90]"
        )


def test_azimuth_in_valid_range():
    positions = calculate_planet_positions(LAT, LON, dt=FIXED_DT)
    for planet in positions:
        assert 0 <= planet.azimuth_deg < 360, (
            f"{planet.name}: azimuth_deg {planet.azimuth_deg} is out of [0, 360)"
        )


def test_rise_set_times_format():
    positions = calculate_planet_positions(LAT, LON, dt=FIXED_DT)
    for planet in positions:
        for field_name in ("rise_time", "set_time", "transit_time"):
            value = getattr(planet, field_name)
            if value is not None:
                assert _ISO8601_RE.match(value), (
                    f"{planet.name}.{field_name} = {value!r} does not match "
                    f"expected format YYYY-MM-DDTHH:MM:SSZ"
                )


def test_azimuth_to_compass_cardinal():
    # azimuth_to_compass lives in app.models.planet, not in calculator.py.
    # The compass table uses English abbreviations; West is "W", not "V".
    assert azimuth_to_compass(0) == "N"
    assert azimuth_to_compass(90) == "E"
    assert azimuth_to_compass(180) == "S"
    assert azimuth_to_compass(270) == "W"


def test_direction_field_not_empty():
    positions = calculate_planet_positions(LAT, LON, dt=FIXED_DT)
    for planet in positions:
        assert isinstance(planet.direction, str) and len(planet.direction) > 0, (
            f"{planet.name}: direction field is empty"
        )


def test_deterministic_output():
    first = calculate_planet_positions(LAT, LON, dt=FIXED_DT)
    second = calculate_planet_positions(LAT, LON, dt=FIXED_DT)
    for p1, p2 in zip(first, second):
        assert abs(p1.altitude_deg - p2.altitude_deg) < 0.001, (
            f"{p1.name}: altitude_deg differs between calls "
            f"({p1.altitude_deg} vs {p2.altitude_deg})"
        )
