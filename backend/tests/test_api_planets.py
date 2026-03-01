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

# Coordinates for Malmö, Sweden — well within the valid lat/lon ranges.
LAT = 55.6
LON = 13.0


# ---------------------------------------------------------------------------
# 1. GET /visible — happy-path status
# ---------------------------------------------------------------------------

async def test_visible_returns_200(async_client, mock_weather):
    response = await async_client.get(
        "/api/v1/planets/visible",
        params={"lat": LAT, "lon": LON},
    )
    assert response.status_code == 200


# ---------------------------------------------------------------------------
# 2. GET /visible — response shape
# ---------------------------------------------------------------------------

async def test_visible_response_keys(async_client, mock_weather):
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

async def test_visible_returns_five_planets(async_client, mock_weather):
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

async def test_missing_lat_returns_422(async_client, mock_weather):
    # lat is declared Query(...) — required; FastAPI returns 422 when absent.
    response = await async_client.get(
        "/api/v1/planets/visible",
        params={"lon": LON},
    )
    assert response.status_code == 422


# ---------------------------------------------------------------------------
# 9. GET /visible — lat=999 out of range → 422
# ---------------------------------------------------------------------------

async def test_invalid_lat_returns_422(async_client, mock_weather):
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

async def test_missing_lon_returns_422(async_client, mock_weather):
    # lon is declared Query(...) — required; FastAPI returns 422 when absent.
    response = await async_client.get(
        "/api/v1/planets/visible",
        params={"lat": LAT},
    )
    assert response.status_code == 422
