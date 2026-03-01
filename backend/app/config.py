from pydantic_settings import BaseSettings
from pathlib import Path


class Settings(BaseSettings):
    # Location
    location_lat: float = 55.7
    location_lon: float = 13.4
    location_name: str = "Södra Sandby"

    # Cache TTL (seconds)
    cache_ttl_weather: int = 1800  # 30 minutes

    # Logging
    log_level: str = "info"

    # API settings
    api_title: str = "Planeter API"
    api_version: str = "1.0.0"
    api_description: str = "Planet visibility calculations for Sweden"

    # Met.no API
    metno_user_agent: str = "PlanetVisibility/1.0 (contact@example.com)"

    # Open-Meteo base URL
    openmeteo_base_url: str = "https://api.open-meteo.com/v1"

    class Config:
        env_file = str(Path(__file__).parent.parent.parent / ".env")
        case_sensitive = False


settings = Settings()
