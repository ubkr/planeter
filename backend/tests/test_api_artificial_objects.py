"""
Integration tests for the /api/v1/artificial-objects endpoint.

All tests use the async_client fixture from conftest.py (AsyncClient wired to
the FastAPI ASGI app).  Most tests mock get_all_artificial_objects at its
import location inside the route module so no live TLE fetches occur.

asyncio_mode = auto is set in pytest.ini so no @pytest.mark.asyncio decorator
is needed.

Endpoint: GET /api/v1/artificial-objects

ArtificialObjectsResponse top-level keys: timestamp, location, objects.

lat/lon are declared with ge/le constraints in Query(), so FastAPI returns 422
for values outside [-90, 90] and [-180, 180] respectively.
"""

from unittest.mock import AsyncMock, patch

from app.models.artificial_object import ArtificialObject

# Coordinates for Malmö, Sweden — well within the valid lat/lon ranges.
LAT = 55.6
LON = 13.0

# The import path of get_all_artificial_objects as it is bound inside the route
# module.  Mocking here overrides the name used by the route handler.
_MOCK_TARGET = "app.api.routes.artificial_objects.get_all_artificial_objects"

# A minimal, valid ArtificialObject representing the ISS.
_ISS_OBJECT = ArtificialObject(
    name="ISS",
    category="satellite",
    altitude_deg=25.3,
    azimuth_deg=180.0,
    direction="S",
    is_above_horizon=True,
    data_source="celestrak_tle",
)


# ---------------------------------------------------------------------------
# 1. Happy path — HTTP 200
# ---------------------------------------------------------------------------

async def test_happy_path_returns_200(async_client):
    with patch(_MOCK_TARGET, new=AsyncMock(return_value=[_ISS_OBJECT])):
        response = await async_client.get(
            "/api/v1/artificial-objects",
            params={"lat": LAT, "lon": LON},
        )
    assert response.status_code == 200


# ---------------------------------------------------------------------------
# 2. Response schema — top-level keys
# ---------------------------------------------------------------------------

async def test_response_has_top_level_keys(async_client):
    with patch(_MOCK_TARGET, new=AsyncMock(return_value=[_ISS_OBJECT])):
        response = await async_client.get(
            "/api/v1/artificial-objects",
            params={"lat": LAT, "lon": LON},
        )
    body = response.json()
    expected_keys = {"timestamp", "location", "objects"}
    assert expected_keys.issubset(body.keys()), (
        f"Missing top-level keys: {expected_keys - body.keys()}"
    )


# ---------------------------------------------------------------------------
# 3. ISS object fields present and name correct
# ---------------------------------------------------------------------------

async def test_iss_in_objects_with_required_fields(async_client):
    with patch(_MOCK_TARGET, new=AsyncMock(return_value=[_ISS_OBJECT])):
        response = await async_client.get(
            "/api/v1/artificial-objects",
            params={"lat": LAT, "lon": LON},
        )
    body = response.json()
    assert len(body["objects"]) == 1
    obj = body["objects"][0]

    assert obj["name"] == "ISS", f"Expected name 'ISS', got {obj['name']!r}"

    required_fields = {
        "name",
        "category",
        "altitude_deg",
        "azimuth_deg",
        "direction",
        "is_above_horizon",
        "data_source",
    }
    missing = required_fields - obj.keys()
    assert not missing, f"objects[0] is missing required fields: {missing}"


# ---------------------------------------------------------------------------
# 4. Schema isolation — no PlanetPosition-specific fields
# ---------------------------------------------------------------------------

async def test_response_does_not_contain_planet_fields(async_client):
    with patch(_MOCK_TARGET, new=AsyncMock(return_value=[_ISS_OBJECT])):
        response = await async_client.get(
            "/api/v1/artificial-objects",
            params={"lat": LAT, "lon": LON},
        )
    body = response.json()
    obj = body["objects"][0]

    planet_only_fields = {"magnitude", "constellation", "visibility_score"}
    present = planet_only_fields & obj.keys()
    assert not present, (
        f"objects[0] must not contain PlanetPosition fields, but found: {present}"
    )


# ---------------------------------------------------------------------------
# 5. Missing lat → 422
# ---------------------------------------------------------------------------

async def test_missing_lat_returns_422(async_client):
    # lat is a required Query parameter; omitting it must produce 422.
    response = await async_client.get(
        "/api/v1/artificial-objects",
        params={"lon": LON},
    )
    assert response.status_code == 422


# ---------------------------------------------------------------------------
# 6. Invalid lon (out of range) → 422
# ---------------------------------------------------------------------------

async def test_invalid_lon_returns_422(async_client):
    # lon is constrained to [-180, 180]; 999 exceeds the upper bound.
    response = await async_client.get(
        "/api/v1/artificial-objects",
        params={"lat": LAT, "lon": 999},
    )
    assert response.status_code == 422


# ---------------------------------------------------------------------------
# 7. Empty objects list when tracker returns no data
# ---------------------------------------------------------------------------

async def test_empty_objects_list_on_no_data(async_client):
    with patch(_MOCK_TARGET, new=AsyncMock(return_value=[])):
        response = await async_client.get(
            "/api/v1/artificial-objects",
            params={"lat": LAT, "lon": LON},
        )
    assert response.status_code == 200
    body = response.json()
    assert body["objects"] == [], (
        f"Expected empty objects list, got {body['objects']!r}"
    )
