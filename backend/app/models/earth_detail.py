"""Pydantic response model for the Earth/Moon detail endpoint with time slider support."""

from pydantic import BaseModel, Field
from typing import List, Optional

from .planet import EarthSystemInfo, LocationInfo


class EarthDetailObjectInfo(BaseModel):
    """
    Position and metadata for a single tracked object in the Earth system,
    suitable for rendering on the Earth/Moon detail diagram at an arbitrary time.

    Extends EarthDetailPosition with name and colour so the caller receives
    everything needed in a single flat model — no need to join against the
    HORIZONS_OBJECTS registry on the frontend.
    """

    name: str = Field(..., description="English object name (e.g. 'Artemis II')")
    label_sv: str = Field(..., description="Swedish display label (e.g. 'Artemis II')")
    colour: Optional[str] = Field(
        None, description="CSS hex colour string for the diagram dot (e.g. '#00bfff')"
    )
    x_offset_earth_radii: float = Field(
        ..., description="Horizontal offset from Earth centre in Earth radii"
    )
    y_offset_earth_radii: float = Field(
        ..., description="Vertical offset from Earth centre in Earth radii"
    )
    distance_km: float = Field(
        ..., description="Distance from Earth centre in kilometres"
    )


class EarthDetailResponse(BaseModel):
    """Top-level API response for the /earth-detail endpoint."""

    timestamp: str = Field(
        ...,
        description="ISO 8601 UTC timestamp of the requested observation time",
    )
    location: LocationInfo
    earth_system: Optional[EarthSystemInfo] = Field(
        None,
        description="Moon position and illumination data; None when the ephem calculation fails",
    )
    objects: List[EarthDetailObjectInfo] = Field(
        default_factory=list,
        description="Tracked spacecraft/objects in the Earth system at the requested time",
    )

    class Config:
        json_schema_extra = {
            "example": {
                "timestamp": "2026-04-07T18:00:00+00:00",
                "location": {"lat": 59.3, "lon": 18.1, "name": None},
                "earth_system": {
                    "moon": {
                        "name_sv": "Månen",
                        "x_offset_earth_radii": 42.3,
                        "y_offset_earth_radii": -11.2,
                        "distance_km": 384400.0,
                        "illumination": 0.72,
                    }
                },
                "objects": [
                    {
                        "name": "Artemis II",
                        "label_sv": "Artemis II",
                        "colour": "#00bfff",
                        "x_offset_earth_radii": 15.4,
                        "y_offset_earth_radii": 3.1,
                        "distance_km": 99800.0,
                    }
                ],
            }
        }
