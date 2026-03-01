"""Open-Meteo weather API client"""
import httpx
from datetime import datetime, timezone
from .base import WeatherSourceBase
from ...models.weather import WeatherData
from ...utils.logger import setup_logger
from ...config import settings

logger = setup_logger(__name__)


class OpenMeteoClient(WeatherSourceBase):
    """Client for Open-Meteo weather forecast data"""

    @property
    def base_url(self) -> str:
        return settings.openmeteo_base_url + "/forecast"

    @property
    def source_name(self) -> str:
        return "open_meteo"

    async def fetch_data(self, lat: float, lon: float) -> WeatherData:
        """
        Fetch weather data from Open-Meteo.

        Free API with 10,000 calls/day limit.
        Provides hourly forecasts with 1-2km resolution.

        Args:
            lat: Latitude
            lon: Longitude

        Returns:
            WeatherData with cloud cover, visibility, precipitation
        """
        try:
            params = {
                "latitude": lat,
                "longitude": lon,
                "hourly": "cloud_cover,visibility,precipitation,temperature_2m",
                "forecast_days": 1,
                "timezone": "Europe/Stockholm"
            }

            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(self.base_url, params=params)
                response.raise_for_status()
                data = response.json()

            # Get current hour data (first entry in hourly arrays)
            hourly = data.get("hourly", {})

            # Parse timestamp
            time_str = hourly.get("time", [""])[0]
            try:
                last_updated = datetime.fromisoformat(time_str).replace(tzinfo=timezone.utc)
            except ValueError:
                logger.warning(f"Could not parse Open-Meteo timestamp: {time_str}")
                last_updated = datetime.now(timezone.utc)

            # Extract values (first entry = current/nearest hour)
            cloud_cover = hourly.get("cloud_cover", [0])[0]  # Percentage
            visibility_m = hourly.get("visibility", [10000])[0]  # Meters
            precipitation = hourly.get("precipitation", [0])[0]  # mm
            temperature = hourly.get("temperature_2m", [None])[0]  # Celsius

            # Convert visibility to km
            visibility_km = visibility_m / 1000.0

            logger.info(
                f"Open-Meteo data fetched: Cloud={cloud_cover}%, "
                f"Vis={visibility_km:.1f}km, Precip={precipitation}mm at ({lat}, {lon})"
            )

            return WeatherData(
                source=self.source_name,
                cloud_cover=round(cloud_cover, 1),
                visibility_km=round(visibility_km, 1),
                precipitation_mm=precipitation,
                temperature_c=temperature,
                last_updated=last_updated
            )

        except httpx.HTTPError as e:
            logger.error(f"HTTP error fetching Open-Meteo data: {e}")
            raise Exception(f"Failed to fetch Open-Meteo weather data: {e}")
        except (KeyError, IndexError, ValueError, TypeError) as e:
            logger.error(f"Error parsing Open-Meteo data: {e}")
            raise Exception(f"Failed to parse Open-Meteo weather data: {e}")
