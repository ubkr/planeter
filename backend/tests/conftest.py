from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.models.weather import WeatherData
from app.models.planet import PlanetPosition


@pytest.fixture
async def async_client():
    """HTTP client wired directly to the FastAPI app via ASGI transport."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        yield client


@pytest.fixture
def mock_weather(monkeypatch):
    """Replace the live weather fetch with a fixed WeatherData response."""
    weather = WeatherData(
        source="mock",
        cloud_cover=20.0,
        precipitation_mm=0.0,
        last_updated=datetime(2026, 3, 1, 22, 0, 0, tzinfo=timezone.utc),
    )
    mock = AsyncMock(return_value=weather)
    monkeypatch.setattr("app.api.routes.planets.get_weather", mock)
    return mock


@pytest.fixture
def mock_forecast(monkeypatch):
    """Replace the live 180-night ephem scan with a no-op returning None.

    Patches the import location in planets.py so the real
    compute_next_good_observation is never called from integration tests.
    Returns None (no qualifying window found) — the simplest valid value.
    """
    monkeypatch.setattr(
        "app.api.routes.planets.compute_next_good_observation",
        lambda *args, **kwargs: None,
    )


@pytest.fixture
def sample_planet_position():
    """Factory that returns a PlanetPosition with sensible defaults.

    Call the returned function with keyword arguments to override any field.
    """
    def _factory(**overrides):
        defaults = dict(
            name="Mars",
            name_sv="Mars",
            altitude_deg=30.0,
            azimuth_deg=180.0,
            direction="S",
            magnitude=-1.0,
            constellation="Gemini",
            is_above_horizon=True,
        )
        defaults.update(overrides)
        return PlanetPosition(**defaults)

    return _factory
