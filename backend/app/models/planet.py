from pydantic import BaseModel, Field
from typing import Dict, List, Optional

# Maps English planet names (as returned by ephem) to Swedish display names.
PLANET_NAMES_SV: Dict[str, str] = {
    "Mercury": "Merkurius",
    "Venus": "Venus",
    "Mars": "Mars",
    "Jupiter": "Jupiter",
    "Saturn": "Saturnus",
}

# 16-point compass directions in clockwise order starting from North.
# Each sector spans 22.5 degrees; the first sector is centred on North (0°/360°).
_COMPASS_DIRECTIONS = [
    "N", "NNE", "NE", "ENE",
    "E", "ESE", "SE", "SSE",
    "S", "SSW", "SW", "WSW",
    "W", "WNW", "NW", "NNW",
]

# Swedish equivalents for the 16-point compass rose, same order as above.
_COMPASS_DIRECTIONS_SV = [
    "nord",          # N      0°
    "nord-nordost",  # NNE   22.5°
    "nordost",       # NE    45°
    "ost-nordost",   # ENE   67.5°
    "ost",           # E     90°
    "ost-sydost",    # ESE  112.5°
    "sydost",        # SE   135°
    "syd-sydost",    # SSE  157.5°
    "syd",           # S    180°
    "syd-sydväst",   # SSW  202.5°
    "sydväst",       # SW   225°
    "väst-sydväst",  # WSW  247.5°
    "väst",          # W    270°
    "väst-nordväst", # WNW  292.5°
    "nordväst",      # NW   315°
    "nord-nordväst", # NNW  337.5°
]


def azimuth_to_compass(azimuth_deg: float) -> str:
    """
    Convert a 0–360 degree azimuth to a 16-point compass direction string.

    North is 0° (and 360°). Each of the 16 sectors spans 22.5°.
    The sector index is determined by rounding to the nearest 22.5° increment.
    """
    # Normalise to [0, 360)
    azimuth_deg = azimuth_deg % 360.0
    # Each sector is 360 / 16 = 22.5 degrees wide.
    index = round(azimuth_deg / 22.5) % 16
    return _COMPASS_DIRECTIONS[index]


def azimuth_to_compass_sv(azimuth_deg: float) -> str:
    """
    Convert a 0–360 degree azimuth to a Swedish 16-point compass direction string.

    Uses the same binning logic as azimuth_to_compass(): normalise to [0, 360),
    divide by 22.5, round to nearest integer, take mod 16 as the sector index.
    """
    # Normalise to [0, 360)
    azimuth_deg = azimuth_deg % 360.0
    # Each sector is 360 / 16 = 22.5 degrees wide.
    index = round(azimuth_deg / 22.5) % 16
    return _COMPASS_DIRECTIONS_SV[index]


class NextGoodObservation(BaseModel):
    """The next upcoming date/window when a planet will be well-placed for observation."""

    date: str = Field(..., description="ISO 8601 date string (e.g. '2026-05-14')")
    start_time: str = Field(..., description="ISO 8601 UTC datetime string for the start of the dark observing window")
    end_time: str = Field(..., description="ISO 8601 UTC datetime string for the end of the dark observing window")
    peak_time: str = Field(..., description="ISO 8601 UTC datetime string for the best moment to observe within the window")
    peak_altitude_deg: float = Field(..., description="Planet altitude in degrees at peak_time")
    magnitude: float = Field(..., description="Apparent visual magnitude at peak_time")
    quality_score: int = Field(..., ge=0, le=100, description="Quality score 0–100 for this observation window")


class PlanetPosition(BaseModel):
    """Position and visibility data for a single naked-eye planet."""

    name: str = Field(..., description="English planet name (e.g. 'Mars')")
    name_sv: str = Field(..., description="Swedish planet name (e.g. 'Mars')")
    altitude_deg: float = Field(..., ge=-90, le=90, description="Altitude above horizon in degrees (-90 to 90)")
    azimuth_deg: float = Field(..., ge=0, lt=360, description="Azimuth from North in degrees, half-open interval [0, 360)")
    direction: str = Field(..., description="16-point compass direction derived from azimuth_deg")
    magnitude: float = Field(..., description="Apparent visual magnitude (lower = brighter)")
    constellation: str = Field(..., description="Constellation the planet is currently in")
    rise_time: Optional[str] = Field(None, description="Next rise time as ISO 8601 UTC string, or null if circumpolar/never rises")
    set_time: Optional[str] = Field(None, description="Next set time as ISO 8601 UTC string, or null if circumpolar/never sets")
    transit_time: Optional[str] = Field(None, description="Next transit (highest point) as ISO 8601 UTC string, or null if not applicable")
    best_time: Optional[str] = Field(None, description="UTC ISO 8601 timestamp of peak altitude within the nautical-dark window, or null if not computed")
    dark_rise_time: Optional[str] = Field(None, description="UTC ISO 8601 timestamp when the planet first exceeds 10° altitude during the dark window, or null if not computed")
    dark_set_time: Optional[str] = Field(None, description="UTC ISO 8601 timestamp when the planet drops below 10° altitude during the dark window, or null if not computed")
    next_visible_time: Optional[str] = Field(None, description="ISO 8601 UTC timestamp of next visibility window in next 24h, or null if none found")
    is_above_horizon: bool = Field(..., description="True when altitude_deg > 0")
    # Filled by Phase 4 scoring module; None until scoring has been applied.
    visibility_score: Optional[int] = Field(None, ge=0, le=100, description="0–100 visibility score; None before scoring")
    is_visible: Optional[bool] = Field(None, description="True when the planet is practically observable; None before scoring")
    # Filled by the scoring module alongside visibility_score.
    # Known reason keys: "below_horizon", "dagsljus", "molnighet",
    # "månljus", "atmosfärisk_dämpning", "goda_förhållanden".
    visibility_reasons: List[str] = Field(
        default_factory=list,
        description=(
            "Ordered list of reason keys explaining the visibility score. "
            "Possible keys: 'below_horizon' (planet below horizon), "
            "'dagsljus' (too much daylight), "
            "'molnighet' (cloud cover too high), "
            "'månljus' (moonlight interference), "
            "'atmosfärisk_dämpning' (atmospheric dampening near horizon), "
            "'goda_förhållanden' (good observing conditions)."
        ),
    )
    # Filled by the next-good-observation finder; None until that pass has run.
    next_good_observation: Optional[NextGoodObservation] = Field(
        None, description="Next upcoming window when the planet is well-placed for observation, or null if not yet computed"
    )
    # Heliocentric Cartesian coordinates in AU; filled by the solar-system view pipeline.
    heliocentric_x_au: Optional[float] = Field(None, description="Heliocentric Cartesian X coordinate in AU")
    heliocentric_y_au: Optional[float] = Field(None, description="Heliocentric Cartesian Y coordinate in AU")
    heliocentric_z_au: Optional[float] = Field(None, description="Heliocentric Cartesian Z coordinate in AU")

    class Config:
        json_schema_extra = {
            "example": {
                "name": "Venus",
                "name_sv": "Venus",
                "altitude_deg": 25.3,
                "azimuth_deg": 245.0,
                "direction": "WSW",
                "magnitude": -4.2,
                "constellation": "Pisces",
                "rise_time": "2026-02-28T07:15:00Z",
                "set_time": "2026-02-28T20:30:00Z",
                "transit_time": "2026-02-28T13:45:00Z",
                "best_time": "2026-02-28T22:10:00Z",
                "dark_rise_time": "2026-02-28T19:50:00Z",
                "dark_set_time": "2026-03-01T03:20:00Z",
                "next_visible_time": None,
                "is_above_horizon": True,
                "visibility_score": 85,
                "is_visible": True,
                "visibility_reasons": [],
                "next_good_observation": None,
                "heliocentric_x_au": 0.45,
                "heliocentric_y_au": -0.23,
                "heliocentric_z_au": 0.01,
            }
        }


class SunInfo(BaseModel):
    """Current sun position and twilight state."""

    elevation_deg: float = Field(..., description="Sun elevation above horizon in degrees")
    azimuth_deg: float = Field(..., ge=0, lt=360, description="Sun azimuth from North in degrees, half-open interval [0, 360)")
    twilight_phase: str = Field(..., description="Twilight phase label: daylight, civil_twilight, nautical_twilight, astronomical_twilight, or darkness")
    limiting_magnitude: float = Field(..., description="Faintest naked-eye magnitude visible at zenith for the current sun altitude (Schaefer 1993)")


class MoonInfo(BaseModel):
    """Current moon position and illumination."""

    illumination: float = Field(..., ge=0.0, le=1.0, description="Moon illumination fraction (0.0 = new moon, 1.0 = full moon)")
    elevation_deg: float = Field(..., description="Moon elevation above horizon in degrees")
    azimuth_deg: float = Field(..., ge=0, lt=360, description="Moon azimuth from North in degrees, half-open interval [0, 360)")


class WeatherInfo(BaseModel):
    """Cloud cover summary used for visibility scoring."""

    cloud_cover: float = Field(..., ge=0, le=100, description="Cloud cover percentage (0–100)")
    source: str = Field(..., description="Weather data source identifier (e.g. 'met_no', 'open_meteo')")


class LocationInfo(BaseModel):
    """Geographic location for the observation."""

    lat: float = Field(..., ge=-90, le=90, description="Latitude in decimal degrees")
    lon: float = Field(..., ge=-180, le=180, description="Longitude in decimal degrees")
    name: Optional[str] = Field(None, description="Human-readable place name, or null if not provided")


class AstronomicalEvent(BaseModel):
    """A detected astronomical event (conjunction, opposition, elongation, etc.)."""

    event_type: str = Field(
        ...,
        description=(
            "Event category: 'conjunction' | 'opposition' | 'mercury_elongation' | "
            "'alignment' | 'venus_brilliancy' | 'moon_occultation'"
        ),
    )
    bodies: List[str] = Field(
        ...,
        description="English names of the bodies involved, e.g. ['Venus', 'Jupiter'] or ['Mercury']",
    )
    date: str = Field(..., description="ISO 8601 UTC string of the event peak or midpoint")
    description_sv: str = Field(..., description="Full Swedish description for display")
    separation_deg: Optional[float] = Field(
        None, description="Angular separation in degrees (conjunctions and moon occultations)"
    )
    elongation_deg: Optional[float] = Field(
        None, description="Elongation from the Sun in degrees (oppositions and Mercury elongation)"
    )
    magnitude: Optional[float] = Field(
        None, description="Apparent visual magnitude (Venus brilliancy)"
    )
    alignment_count: Optional[int] = Field(
        None, description="Number of planets in the alignment arc"
    )
    days_away: Optional[int] = Field(
        None, description="Days from the query start_dt (0 = today)"
    )
    event_icon: str = Field(
        "",
        description=(
            "Icon key hint: 'conjunction' | 'opposition' | 'elongation' | "
            "'alignment' | 'brilliancy' | 'occultation'"
        ),
    )
    best_time_start: Optional[str] = Field(
        None, description="ISO 8601 UTC string for start of best viewing window"
    )
    best_time_end: Optional[str] = Field(
        None, description="ISO 8601 UTC string for end of best viewing window"
    )
    altitude_deg: Optional[float] = Field(
        None, description="Altitude of primary body at event peak in degrees"
    )
    azimuth_deg: Optional[float] = Field(
        None, description="Azimuth of primary body at event peak in degrees"
    )
    compass_direction_sv: Optional[str] = Field(
        None, description="Swedish compass direction string (e.g. 'sydväst')"
    )
    observation_tip_sv: Optional[str] = Field(
        None, description="Swedish prose observation tip for this event"
    )


class PlanetsResponse(BaseModel):
    """Top-level API response for planet visibility endpoints."""

    timestamp: str = Field(..., description="Observation time as ISO 8601 UTC string")
    location: LocationInfo
    sun: SunInfo
    moon: MoonInfo
    weather: WeatherInfo
    planets: List[PlanetPosition]
    tonight_score: Optional[int] = Field(None, ge=0, le=100, description="Aggregate tonight score 0-100")
    events: List[AstronomicalEvent] = Field(
        default_factory=list,
        description="Upcoming and current astronomical events detected for the observation window",
    )

    class Config:
        json_schema_extra = {
            "example": {
                "timestamp": "2026-02-28T22:00:00Z",
                "location": {"lat": 55.7, "lon": 13.4, "name": "Södra Sandby"},
                "sun": {"elevation_deg": -25.3, "azimuth_deg": 185.0, "twilight_phase": "darkness", "limiting_magnitude": 6.5},
                "moon": {"illumination": 0.45, "elevation_deg": 32.1, "azimuth_deg": 180.0},
                "weather": {"cloud_cover": 15.0, "source": "met_no"},
                "planets": [],
                "events": [],
            }
        }


class EventsResponse(BaseModel):
    """Dedicated API response for the events endpoint."""

    timestamp: str = Field(..., description="Query time as ISO 8601 UTC string")
    location: LocationInfo
    events: List[AstronomicalEvent]
