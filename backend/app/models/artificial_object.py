"""Pydantic models for artificial-object (satellite) tracking responses."""

from pydantic import BaseModel, Field
from typing import List, Optional

from .planet import LocationInfo


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


class ArtificialObjectsResponse(BaseModel):
    """Top-level API response for the artificial-objects endpoint."""

    timestamp: str = Field(..., description="Observation time as ISO 8601 UTC string")
    location: LocationInfo
    objects: List[ArtificialObject]
