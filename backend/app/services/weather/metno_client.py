"""Met.no (Norwegian Meteorological Institute) weather API client"""
import httpx
from datetime import datetime, timezone
from .base import WeatherSourceBase
from ...models.weather import WeatherData
from ...utils.logger import setup_logger
from ...config import settings

logger = setup_logger(__name__)


class MetNoClient(WeatherSourceBase):
    """Client for Met.no weather forecast data"""

    BASE_URL = "https://api.met.no/weatherapi/locationforecast/2.0/compact"

    @property
    def source_name(self) -> str:
        return "met_no"

    async def fetch_data(self, lat: float, lon: float) -> WeatherData:
        """
        Fetch weather data from Met.no.

        Met.no provides detailed Nordic weather forecasts.
        Requires proper User-Agent header.

        Args:
            lat: Latitude
            lon: Longitude

        Returns:
            WeatherData with cloud cover and precipitation
        """
        try:
            params = {
                "lat": lat,
                "lon": lon
            }

            headers = {
                "User-Agent": settings.metno_user_agent
            }

            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.get(
                    self.BASE_URL,
                    params=params,
                    headers=headers
                )
                response.raise_for_status()
                data = response.json()

            # Extract first timeseries entry (current/nearest forecast)
            timeseries = data.get("properties", {}).get("timeseries", [])
            if not timeseries:
                raise ValueError("No timeseries data in Met.no response")

            current = timeseries[0]

            # Parse timestamp
            time_str = current.get("time", "")
            try:
                last_updated = datetime.fromisoformat(time_str.replace("Z", "+00:00"))
            except ValueError:
                logger.warning(f"Could not parse Met.no timestamp: {time_str}")
                last_updated = datetime.now(timezone.utc)

            # Extract instant parameters
            instant = current.get("data", {}).get("instant", {}).get("details", {})

            # Cloud cover (already in percentage)
            cloud_cover = instant.get("cloud_area_fraction", 0)

            # Temperature
            temperature_c = instant.get("air_temperature")

            # Precipitation from next hour forecast
            next_1h = current.get("data", {}).get("next_1_hours", {}).get("details", {})
            precipitation_mm = next_1h.get("precipitation_amount", 0)

            logger.info(
                f"Met.no data fetched: Cloud={cloud_cover}%, "
                f"Precip={precipitation_mm}mm at ({lat}, {lon})"
            )

            return WeatherData(
                source=self.source_name,
                cloud_cover=round(cloud_cover, 1),
                visibility_km=None,
                precipitation_mm=precipitation_mm,
                temperature_c=temperature_c,
                last_updated=last_updated
            )

        except httpx.HTTPError as e:
            logger.error(f"HTTP error fetching Met.no data: {e}")
            raise Exception(f"Failed to fetch Met.no weather data: {e}")
        except (KeyError, IndexError, ValueError, TypeError) as e:
            logger.error(f"Error parsing Met.no data: {e}")
            raise Exception(f"Failed to parse Met.no weather data: {e}")
