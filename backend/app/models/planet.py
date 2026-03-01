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
                "is_above_horizon": True,
                "visibility_score": 85,
                "is_visible": True,
                "visibility_reasons": [],
            }
        }


class SunInfo(BaseModel):
    """Current sun position and twilight state."""

    elevation_deg: float = Field(..., description="Sun elevation above horizon in degrees")
    twilight_phase: str = Field(..., description="Twilight phase label: daylight, civil_twilight, nautical_twilight, astronomical_twilight, or darkness")


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


class PlanetsResponse(BaseModel):
    """Top-level API response for planet visibility endpoints."""

    timestamp: str = Field(..., description="Observation time as ISO 8601 UTC string")
    location: LocationInfo
    sun: SunInfo
    moon: MoonInfo
    weather: WeatherInfo
    planets: List[PlanetPosition]
    tonight_score: Optional[int] = Field(None, ge=0, le=100, description="Aggregate tonight score 0-100")

    class Config:
        json_schema_extra = {
            "example": {
                "timestamp": "2026-02-28T22:00:00Z",
                "location": {"lat": 55.7, "lon": 13.4, "name": "Södra Sandby"},
                "sun": {"elevation_deg": -25.3, "twilight_phase": "darkness"},
                "moon": {"illumination": 0.45, "elevation_deg": 32.1, "azimuth_deg": 180.0},
                "weather": {"cloud_cover": 15.0, "source": "met_no"},
                "planets": [],
            }
        }
