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
from app.models.planet import azimuth_to_compass

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
    colour="#ffffff",
    label_sv="ISS",
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


# ---------------------------------------------------------------------------
# 8-10. Partial-failure and multi-source tests (tests 11-13 of overall suite)
#
# These tests patch get_iss_position and get_horizons_objects at their
# use locations inside tracker.py so that get_all_artificial_objects calls
# the real aggregation logic while each source is independently controlled.
# ---------------------------------------------------------------------------

# Patch targets inside the tracker module (where the names are bound).
_ISS_TARGET = "app.services.artificial_objects.tracker.get_iss_position"
_HORIZONS_TARGET = "app.services.artificial_objects.tracker.get_horizons_objects"

# A minimal Artemis II ArtificialObject for use in multi-source tests.
_ARTEMIS_OBJECT = ArtificialObject(
    name="Artemis II",
    category="spacecraft",
    altitude_deg=23.5,
    azimuth_deg=142.1,
    direction=azimuth_to_compass(142.1),
    is_above_horizon=True,
    data_source="jpl_horizons",
    colour="#00bfff",
    label_sv="Artemis II",
)


async def test_both_sources_succeed_returns_both_objects(async_client):
    """Test 11: ISS and Artemis II both present when both sources succeed."""
    with (
        patch(_ISS_TARGET, new=AsyncMock(return_value=_ISS_OBJECT)),
        patch(_HORIZONS_TARGET, new=AsyncMock(return_value=[_ARTEMIS_OBJECT])),
    ):
        response = await async_client.get(
            "/api/v1/artificial-objects",
            params={"lat": 55.7, "lon": 13.4},
        )
    assert response.status_code == 200
    body = response.json()
    names = {obj["name"] for obj in body["objects"]}
    assert "ISS" in names, f"ISS missing from objects: {names}"
    assert "Artemis II" in names, f"Artemis II missing from objects: {names}"


async def test_horizons_fails_iss_still_returned(async_client):
    """Test 12: Horizons raises → endpoint returns HTTP 200 with ISS only."""
    with (
        patch(_ISS_TARGET, new=AsyncMock(return_value=_ISS_OBJECT)),
        patch(_HORIZONS_TARGET, new=AsyncMock(side_effect=RuntimeError("horizons down"))),
    ):
        response = await async_client.get(
            "/api/v1/artificial-objects",
            params={"lat": 55.7, "lon": 13.4},
        )
    assert response.status_code == 200
    body = response.json()
    assert len(body["objects"]) == 1, (
        f"Expected 1 object (ISS), got {len(body['objects'])}"
    )
    assert body["objects"][0]["name"] == "ISS"


async def test_iss_fails_horizons_still_returned(async_client):
    """Test 13: ISS raises → endpoint returns HTTP 200 with Artemis II only."""
    with (
        patch(_ISS_TARGET, new=AsyncMock(side_effect=RuntimeError("iss down"))),
        patch(_HORIZONS_TARGET, new=AsyncMock(return_value=[_ARTEMIS_OBJECT])),
    ):
        response = await async_client.get(
            "/api/v1/artificial-objects",
            params={"lat": 55.7, "lon": 13.4},
        )
    assert response.status_code == 200
    body = response.json()
    assert len(body["objects"]) == 1, (
        f"Expected 1 object (Artemis II), got {len(body['objects'])}"
    )
    assert body["objects"][0]["name"] == "Artemis II"


# ---------------------------------------------------------------------------
# 14–15. earth_detail_position field serialisation
# ---------------------------------------------------------------------------

# An ArtificialObject with a fully-populated EarthDetailPosition — the four
# sub-fields that the VECTORS call produces for Artemis II.
from app.models.artificial_object import EarthDetailPosition  # noqa: E402

_ARTEMIS_WITH_EARTH_DETAIL = ArtificialObject(
    name="Artemis II",
    category="spacecraft",
    altitude_deg=18.7,
    azimuth_deg=213.5,
    direction=azimuth_to_compass(213.5),
    is_above_horizon=True,
    data_source="jpl_horizons",
    colour="#00bfff",
    label_sv="Artemis II",
    earth_detail_position=EarthDetailPosition(
        x_offset_earth_radii=12.345,
        y_offset_earth_radii=-6.789,
        distance_km=423_456.0,
        label_sv="Artemis II",
    ),
)


async def test_earth_detail_position_present_in_response(async_client):
    """Test 14: ArtificialObject with EarthDetailPosition → field serialised correctly."""
    with patch(_MOCK_TARGET, new=AsyncMock(return_value=[_ARTEMIS_WITH_EARTH_DETAIL])):
        response = await async_client.get(
            "/api/v1/artificial-objects",
            params={"lat": LAT, "lon": LON},
        )
    assert response.status_code == 200
    body = response.json()
    assert len(body["objects"]) == 1
    edp = body["objects"][0].get("earth_detail_position")
    assert edp is not None, "earth_detail_position must not be null for this object"
    assert edp["x_offset_earth_radii"] == 12.345, (
        f"Unexpected x_offset_earth_radii: {edp['x_offset_earth_radii']!r}"
    )
    assert edp["y_offset_earth_radii"] == -6.789, (
        f"Unexpected y_offset_earth_radii: {edp['y_offset_earth_radii']!r}"
    )
    assert edp["distance_km"] == 423_456.0, (
        f"Unexpected distance_km: {edp['distance_km']!r}"
    )
    assert edp["label_sv"] == "Artemis II", (
        f"Unexpected label_sv: {edp['label_sv']!r}"
    )


async def test_earth_detail_position_null_for_iss(async_client):
    """Test 15: ArtificialObject with earth_detail_position=None → field is null in JSON."""
    # _ISS_OBJECT does not set earth_detail_position; it defaults to None.
    with patch(_MOCK_TARGET, new=AsyncMock(return_value=[_ISS_OBJECT])):
        response = await async_client.get(
            "/api/v1/artificial-objects",
            params={"lat": LAT, "lon": LON},
        )
    assert response.status_code == 200
    body = response.json()
    assert len(body["objects"]) == 1
    obj = body["objects"][0]
    assert "earth_detail_position" in obj, (
        "earth_detail_position key must be present in the serialised object"
    )
    assert obj["earth_detail_position"] is None, (
        f"Expected null earth_detail_position for ISS, got {obj['earth_detail_position']!r}"
    )
