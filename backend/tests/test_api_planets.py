"""
Integration tests for the /api/v1/planets endpoints.

All tests use:
  - async_client  — httpx AsyncClient wired to the FastAPI ASGI app.
  - mock_weather  — monkeypatches app.api.routes.planets.get_weather so no
                    live HTTP calls are made to Met.no or Open-Meteo.

asyncio_mode = auto is set in pytest.ini so no @pytest.mark.asyncio is needed.

Endpoint summary (prefix: /api/v1/planets):
  GET /visible        — all five planets scored for current conditions.
  GET /tonight        — all five planets scored for tonight's best window.
  GET /{name}         — single planet by case-insensitive name.

PlanetsResponse top-level keys: timestamp, location, sun, moon, weather,
planets, tonight_score.

lat/lon are declared with ge/le constraints in Query(), so FastAPI returns 422
for values outside [-90, 90] and [-180, 180] respectively.
"""

import pytest
from datetime import datetime, timezone
from unittest.mock import patch, MagicMock

# Coordinates for Malmö, Sweden — well within the valid lat/lon ranges.
LAT = 55.6
LON = 13.0


# ---------------------------------------------------------------------------
# 1. GET /visible — happy-path status
# ---------------------------------------------------------------------------

async def test_visible_returns_200(async_client, mock_weather, mock_forecast):
    response = await async_client.get(
        "/api/v1/planets/visible",
        params={"lat": LAT, "lon": LON},
    )
    assert response.status_code == 200


# ---------------------------------------------------------------------------
# 2. GET /visible — response shape
# ---------------------------------------------------------------------------

async def test_visible_response_keys(async_client, mock_weather, mock_forecast):
    response = await async_client.get(
        "/api/v1/planets/visible",
        params={"lat": LAT, "lon": LON},
    )
    body = response.json()
    # PlanetsResponse fields (tonight_score is Optional so may be null/absent,
    # but Pydantic serialises Optional fields as null — the key is present).
    expected_keys = {"timestamp", "location", "sun", "moon", "weather", "planets"}
    assert expected_keys.issubset(body.keys()), (
        f"Missing keys: {expected_keys - body.keys()}"
    )


# ---------------------------------------------------------------------------
# 3. GET /visible — planets array length
# ---------------------------------------------------------------------------

async def test_visible_returns_five_planets(async_client, mock_weather, mock_forecast):
    response = await async_client.get(
        "/api/v1/planets/visible",
        params={"lat": LAT, "lon": LON},
    )
    body = response.json()
    assert len(body["planets"]) == 5


# ---------------------------------------------------------------------------
# 4. GET /tonight — happy-path status
# ---------------------------------------------------------------------------

async def test_tonight_returns_200(async_client, mock_weather):
    response = await async_client.get(
        "/api/v1/planets/tonight",
        params={"lat": LAT, "lon": LON},
    )
    assert response.status_code == 200


# ---------------------------------------------------------------------------
# 5. GET /{name} — known planet (lower-case)
# ---------------------------------------------------------------------------

async def test_planet_by_name_returns_200(async_client, mock_weather):
    response = await async_client.get(
        "/api/v1/planets/jupiter",
        params={"lat": LAT, "lon": LON},
    )
    assert response.status_code == 200
    body = response.json()
    # The router returns a PlanetPosition; name is the English title-cased name.
    assert body["name"].lower() == "jupiter"


# ---------------------------------------------------------------------------
# 6. GET /{name} — name is case-insensitive
# ---------------------------------------------------------------------------

async def test_planet_by_name_case_insensitive(async_client, mock_weather):
    # The router lower-cases the path segment before the validity check.
    response = await async_client.get(
        "/api/v1/planets/Jupiter",
        params={"lat": LAT, "lon": LON},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["name"].lower() == "jupiter"


# ---------------------------------------------------------------------------
# 7. GET /{name} — unknown planet name → 404
# ---------------------------------------------------------------------------

async def test_unknown_planet_returns_404(async_client, mock_weather):
    response = await async_client.get(
        "/api/v1/planets/pluto",
        params={"lat": LAT, "lon": LON},
    )
    assert response.status_code == 404


# ---------------------------------------------------------------------------
# 8. GET /visible — missing lat → 422
# ---------------------------------------------------------------------------

async def test_missing_lat_returns_422(async_client, mock_weather, mock_forecast):
    # lat is declared Query(...) — required; FastAPI returns 422 when absent.
    response = await async_client.get(
        "/api/v1/planets/visible",
        params={"lon": LON},
    )
    assert response.status_code == 422


# ---------------------------------------------------------------------------
# 9. GET /visible — lat=999 out of range → 422
# ---------------------------------------------------------------------------

async def test_invalid_lat_returns_422(async_client, mock_weather, mock_forecast):
    # lat is declared Query(..., ge=-90, le=90), so 999 fails FastAPI's built-in
    # range validation and returns 422 Unprocessable Entity.
    response = await async_client.get(
        "/api/v1/planets/visible",
        params={"lat": 999, "lon": LON},
    )
    assert response.status_code == 422


# ---------------------------------------------------------------------------
# 10. GET /visible — missing lon → 422
# ---------------------------------------------------------------------------

async def test_missing_lon_returns_422(async_client, mock_weather, mock_forecast):
    # lon is declared Query(...) — required; FastAPI returns 422 when absent.
    response = await async_client.get(
        "/api/v1/planets/visible",
        params={"lat": LAT},
    )
    assert response.status_code == 422


# ---------------------------------------------------------------------------
# Phase B1 — best_time / dark_rise_time / dark_set_time fields
# ---------------------------------------------------------------------------

# Stockholm coordinates used for Phase B1 tests.  These are far enough south
# that a nautical dark window exists year-round (no midnight-sun issue).
_STOCKHOLM_LAT = 59.33
_STOCKHOLM_LON = 18.07

# Keys that every PlanetPosition must carry after Phase B1.
_DARK_WINDOW_KEYS = {"best_time", "dark_rise_time", "dark_set_time"}


# ---------------------------------------------------------------------------
# 11. GET /visible — Phase B1 fields present on every planet
# ---------------------------------------------------------------------------

async def test_visible_includes_phase_b1_fields(async_client, mock_weather, mock_forecast):
    # Every planet dict in the /visible response must contain the three new
    # dark-window fields.  Values may be null (None) — that is expected when a
    # planet stays below _MIN_ALTITUDE_DEG all night — but the keys must exist.
    response = await async_client.get(
        "/api/v1/planets/visible",
        params={"lat": _STOCKHOLM_LAT, "lon": _STOCKHOLM_LON},
    )
    assert response.status_code == 200
    body = response.json()
    for planet in body["planets"]:
        missing = _DARK_WINDOW_KEYS - planet.keys()
        assert not missing, (
            f"Planet '{planet.get('name')}' is missing Phase B1 keys: {missing}"
        )


# ---------------------------------------------------------------------------
# 12. GET /tonight — Phase B1 fields present on every planet
# ---------------------------------------------------------------------------

async def test_tonight_includes_phase_b1_fields(async_client, mock_weather):
    # Same expectation as /visible — all three dark-window keys must be present
    # on every planet object in the /tonight response, even if null.
    response = await async_client.get(
        "/api/v1/planets/tonight",
        params={"lat": _STOCKHOLM_LAT, "lon": _STOCKHOLM_LON},
    )
    assert response.status_code == 200
    body = response.json()
    for planet in body["planets"]:
        missing = _DARK_WINDOW_KEYS - planet.keys()
        assert not missing, (
            f"Planet '{planet.get('name')}' is missing Phase B1 keys: {missing}"
        )


# ---------------------------------------------------------------------------
# 13. GET /{name} — Phase B1 fields present and null
# ---------------------------------------------------------------------------

async def test_planet_by_name_includes_phase_b1_fields_as_null(async_client, mock_weather):
    # The /{name} endpoint returns a bare PlanetPosition and never invokes
    # _compute_best_viewing_times, so the three dark-window fields must exist
    # on the model but must be null (None → JSON null).
    response = await async_client.get(
        "/api/v1/planets/jupiter",
        params={"lat": _STOCKHOLM_LAT, "lon": _STOCKHOLM_LON},
    )
    assert response.status_code == 200
    body = response.json()
    missing = _DARK_WINDOW_KEYS - body.keys()
    assert not missing, f"Missing Phase B1 keys: {missing}"
    for key in _DARK_WINDOW_KEYS:
        assert body[key] is None, (
            f"Expected '{key}' to be null from /{'{name}'} endpoint, got {body[key]!r}"
        )


# ---------------------------------------------------------------------------
# 14. Unit test — _compute_nautical_dark_window returns (None, None) during
#     midnight sun (sun never drops below -12° at lat=70, lon=25 in June)
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# 15. GET /visible — next_good_observation key present on every planet (B9)
# ---------------------------------------------------------------------------

async def test_visible_includes_next_good_observation(async_client, mock_weather, mock_forecast):
    # Every planet dict in the /visible response must carry the
    # next_good_observation key introduced in Phase B9.  When the forecast
    # mock returns None the value will be null, but the key must exist.
    response = await async_client.get(
        "/api/v1/planets/visible",
        params={"lat": _STOCKHOLM_LAT, "lon": _STOCKHOLM_LON},
    )
    assert response.status_code == 200
    body = response.json()
    for planet in body["planets"]:
        assert "next_good_observation" in planet, (
            f"Planet '{planet.get('name')}' is missing 'next_good_observation' key"
        )


# ---------------------------------------------------------------------------
# 14. Unit test — _compute_nautical_dark_window returns (None, None) during
#     midnight sun (sun never drops below -12° at lat=70, lon=25 in June)
# ---------------------------------------------------------------------------

def test_compute_nautical_dark_window_midnight_sun():
    # Import the private helper directly so we can test it without HTTP.
    from app.api.routes.planets import _compute_nautical_dark_window

    # Midsummer date at which the sun never dips below -12° near Tromsø.
    midsummer = datetime(2025, 6, 21, 12, 0, 0, tzinfo=timezone.utc)

    # Patch datetime.now inside the route module so that the helper treats the
    # current time as midsummer 2025 rather than the real wall-clock time.
    mock_dt = MagicMock(wraps=datetime)
    mock_dt.now = MagicMock(return_value=midsummer)

    with patch("app.api.routes.planets.datetime", mock_dt):
        dark_start, dark_end = _compute_nautical_dark_window(lat=70.0, lon=25.0)

    assert dark_start is None, (
        f"Expected dark_start=None for midnight sun, got {dark_start!r}"
    )
    assert dark_end is None, (
        f"Expected dark_end=None for midnight sun, got {dark_end!r}"
    )
