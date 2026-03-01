from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional


class WeatherData(BaseModel):
    """Weather data from a single source"""
    source: str = Field(..., description="Data source name (e.g., 'smhi', 'open_meteo')")
    cloud_cover: float = Field(..., ge=0, le=100, description="Cloud cover percentage (0-100)")
    visibility_km: Optional[float] = Field(None, ge=0, description="Visibility in kilometers")
    precipitation_mm: float = Field(..., ge=0, description="Precipitation in millimeters")
    temperature_c: Optional[float] = Field(None, description="Temperature in Celsius")
    last_updated: datetime = Field(..., description="Timestamp of last data update")

    class Config:
        json_schema_extra = {
            "example": {
                "source": "smhi",
                "cloud_cover": 37.5,
                "visibility_km": 15,
                "precipitation_mm": 0,
                "temperature_c": 2,
                "last_updated": "2026-02-01T22:00:00Z"
            }
        }


class WeatherResponse(BaseModel):
    """Combined weather data from multiple sources"""
    primary: WeatherData
    secondary: Optional[WeatherData] = None
    tertiary: Optional[WeatherData] = None
