"""Base class for weather data sources"""
from abc import ABC, abstractmethod
from ...models.weather import WeatherData


class WeatherSourceBase(ABC):
    """Abstract base class for weather data sources"""

    @property
    @abstractmethod
    def source_name(self) -> str:
        """Return the source name"""
        pass

    @abstractmethod
    async def fetch_data(self, lat: float, lon: float) -> WeatherData:
        """
        Fetch weather data for a specific location.

        Args:
            lat: Latitude
            lon: Longitude

        Returns:
            WeatherData object

        Raises:
            Exception: If data fetch fails
        """
        pass
