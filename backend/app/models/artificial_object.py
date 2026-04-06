"""Pydantic models for artificial-object (satellite) tracking responses."""

from pydantic import BaseModel, Field
from typing import List, Optional

from .planet import LocationInfo


class EarthDetailPosition(BaseModel):
    """Position of an artificial object relative to Earth for the Earth/Moon detail diagram."""

    x_offset_earth_radii: float = Field(
        ..., description="Horizontal offset from Earth centre in Earth radii"
    )
    y_offset_earth_radii: float = Field(
        ..., description="Vertical offset from Earth centre in Earth radii"
    )
    distance_km: float = Field(
        ..., description="Distance from Earth centre in km"
    )
    label_sv: str = Field(
        ..., description="Swedish label for the diagram (e.g. 'Artemis II')"
    )


class ArtificialObject(BaseModel):
    """Position data for a single tracked artificial object (satellite)."""

    name: str = Field(..., description="Object name (e.g. 'ISS (ZARYA)')")
    category: str = Field(..., description="Object category (e.g. 'satellite')")
    altitude_deg: float = Field(..., description="Altitude above horizon in degrees")
    azimuth_deg: float = Field(..., ge=0, lt=360, description="Azimuth from North in degrees, half-open interval [0, 360)")
    direction: str = Field(..., description="16-point compass direction derived from azimuth_deg")
    is_above_horizon: bool = Field(..., description="True when altitude_deg > 0")
    data_source: str = Field(..., description="Data source identifier (e.g. 'celestrak_tle')")
    colour: Optional[str] = Field(None, description="CSS hex colour string for the object's dot/sprite (e.g. '#ffffff')")
    label_sv: Optional[str] = Field(None, description="Swedish display label for tooltips and UI (e.g. 'ISS')")
    earth_detail_position: Optional[EarthDetailPosition] = Field(
        None,
        description="Position relative to Earth for the Earth/Moon detail diagram. Null for objects without Earth-proximity data.",
    )


class ArtificialObjectsResponse(BaseModel):
    """Top-level API response for the artificial-objects endpoint."""

    timestamp: str = Field(..., description="Observation time as ISO 8601 UTC string")
    location: LocationInfo
    objects: List[ArtificialObject]
