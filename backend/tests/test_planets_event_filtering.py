"""
Tests for location-based event altitude filtering on planet endpoints.

The /api/v1/planets/visible and /api/v1/planets/tonight routes include an
``events`` list in PlanetsResponse.  Events where altitude_deg is a non-null
negative number must be excluded.  Events where altitude_deg is None, 0.0, or
positive must be retained.

All tests mock detect_events so that:
  - No real ephem computation takes place.
  - The response events list contains exactly the events returned by the mock.

Patch target: app.api.routes.planets.detect_events
  (detect_events is imported directly into the planets route module, so it must
   be patched at the location where it is looked up, not at its definition site)

The mock_weather fixture from conftest is required because both planet
endpoints call get_weather; without it the live HTTP call would fail.

asyncio_mode = auto is set in pytest.ini so no @pytest.mark.asyncio decorator
is needed on async test functions — pytest-asyncio collects them automatically.
"""

from unittest.mock import patch

from app.models.planet import AstronomicalEvent


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

_DEFAULT_PARAMS = {"lat": 59.3, "lon": 18.1}

# Minimal required fields for AstronomicalEvent.
# NOTE: altitude_deg is intentionally absent here — it defaults to None via the
# model.  Callers must always supply altitude_deg explicitly for filtering tests
# so the assertion reflects the intended filtering behaviour, not the default.
_EVENT_DEFAULTS = dict(
    event_type="conjunction",
    bodies=["Venus", "Jupiter"],
    date="2026-04-01T20:00:00Z",
    description_sv="Venus och Jupiter i konjunktion",
    event_icon="conjunction",
)


def _make_event(**overrides) -> AstronomicalEvent:
    """Return an AstronomicalEvent with sensible defaults and any overrides applied."""
    fields = {**_EVENT_DEFAULTS, **overrides}
    return AstronomicalEvent(**fields)


# ---------------------------------------------------------------------------
# /api/v1/planets/visible — altitude filtering
# ---------------------------------------------------------------------------

async def test_visible_negative_altitude_event_is_excluded(async_client, mock_weather):
    """An event with altitude_deg = -5.0 must not appear in /visible response["events"]."""
    event = _make_event(altitude_deg=-5.0)

    with patch("app.api.routes.planets.detect_events", return_value=[event]):
        response = await async_client.get("/api/v1/planets/visible", params=_DEFAULT_PARAMS)

    assert response.status_code == 200
    data = response.json()
    assert data["events"] == [], (
        f"Expected empty events list but got: {data['events']}"
    )


async def test_visible_positive_altitude_event_is_retained(async_client, mock_weather):
    """An event with altitude_deg = 15.0 must be kept in /visible response["events"]."""
    event = _make_event(altitude_deg=15.0)

    with patch("app.api.routes.planets.detect_events", return_value=[event]):
        response = await async_client.get("/api/v1/planets/visible", params=_DEFAULT_PARAMS)

    assert response.status_code == 200
    data = response.json()
    assert len(data["events"]) == 1, (
        f"Expected 1 event but got {len(data['events'])}"
    )
    assert data["events"][0]["altitude_deg"] == 15.0


async def test_visible_null_altitude_event_is_retained(async_client, mock_weather):
    """An event with altitude_deg = None must be kept in /visible response["events"]."""
    event = _make_event(altitude_deg=None)

    with patch("app.api.routes.planets.detect_events", return_value=[event]):
        response = await async_client.get("/api/v1/planets/visible", params=_DEFAULT_PARAMS)

    assert response.status_code == 200
    data = response.json()
    assert len(data["events"]) == 1, (
        f"Expected 1 event but got {len(data['events'])}"
    )
    assert data["events"][0]["altitude_deg"] is None


async def test_visible_zero_altitude_event_is_retained(async_client, mock_weather):
    """An event with altitude_deg = 0.0 (exactly on horizon) must be kept in /visible response["events"]."""
    event = _make_event(altitude_deg=0.0)

    with patch("app.api.routes.planets.detect_events", return_value=[event]):
        response = await async_client.get("/api/v1/planets/visible", params=_DEFAULT_PARAMS)

    assert response.status_code == 200
    data = response.json()
    assert len(data["events"]) == 1, (
        f"Expected 1 event but got {len(data['events'])}"
    )
    assert data["events"][0]["altitude_deg"] == 0.0


# ---------------------------------------------------------------------------
# /api/v1/planets/tonight — altitude filtering
# ---------------------------------------------------------------------------

async def test_tonight_negative_altitude_event_is_excluded(async_client, mock_weather):
    """An event with altitude_deg = -5.0 must not appear in /tonight response["events"]."""
    event = _make_event(altitude_deg=-5.0)

    with patch("app.api.routes.planets.detect_events", return_value=[event]):
        response = await async_client.get("/api/v1/planets/tonight", params=_DEFAULT_PARAMS)

    assert response.status_code == 200
    data = response.json()
    assert data["events"] == [], (
        f"Expected empty events list but got: {data['events']}"
    )


async def test_tonight_positive_altitude_event_is_retained(async_client, mock_weather):
    """An event with altitude_deg = 15.0 must be kept in /tonight response["events"]."""
    event = _make_event(altitude_deg=15.0)

    with patch("app.api.routes.planets.detect_events", return_value=[event]):
        response = await async_client.get("/api/v1/planets/tonight", params=_DEFAULT_PARAMS)

    assert response.status_code == 200
    data = response.json()
    assert len(data["events"]) == 1, (
        f"Expected 1 event but got {len(data['events'])}"
    )
    assert data["events"][0]["altitude_deg"] == 15.0


async def test_tonight_null_altitude_event_is_retained(async_client, mock_weather):
    """An event with altitude_deg = None must be kept in /tonight response["events"]."""
    event = _make_event(altitude_deg=None)

    with patch("app.api.routes.planets.detect_events", return_value=[event]):
        response = await async_client.get("/api/v1/planets/tonight", params=_DEFAULT_PARAMS)

    assert response.status_code == 200
    data = response.json()
    assert len(data["events"]) == 1, (
        f"Expected 1 event but got {len(data['events'])}"
    )
    assert data["events"][0]["altitude_deg"] is None


async def test_tonight_zero_altitude_event_is_retained(async_client, mock_weather):
    """An event with altitude_deg = 0.0 (exactly on horizon) must be kept in /tonight response["events"]."""
    event = _make_event(altitude_deg=0.0)

    with patch("app.api.routes.planets.detect_events", return_value=[event]):
        response = await async_client.get("/api/v1/planets/tonight", params=_DEFAULT_PARAMS)

    assert response.status_code == 200
    data = response.json()
    assert len(data["events"]) == 1, (
        f"Expected 1 event but got {len(data['events'])}"
    )
    assert data["events"][0]["altitude_deg"] == 0.0


# ---------------------------------------------------------------------------
# NaN altitude — both endpoints must treat NaN as below-horizon and exclude it
# ---------------------------------------------------------------------------

async def test_visible_nan_altitude_event_is_excluded(async_client, mock_weather):
    """An event with altitude_deg = float('nan') must not appear in /visible response["events"]."""
    event = _make_event(altitude_deg=float("nan"))

    with patch("app.api.routes.planets.detect_events", return_value=[event]):
        response = await async_client.get("/api/v1/planets/visible", params=_DEFAULT_PARAMS)

    assert response.status_code == 200
    data = response.json()
    assert data["events"] == [], (
        f"Expected empty events list but got: {data['events']}"
    )


async def test_tonight_nan_altitude_event_is_excluded(async_client, mock_weather):
    """An event with altitude_deg = float('nan') must not appear in /tonight response["events"]."""
    event = _make_event(altitude_deg=float("nan"))

    with patch("app.api.routes.planets.detect_events", return_value=[event]):
        response = await async_client.get("/api/v1/planets/tonight", params=_DEFAULT_PARAMS)

    assert response.status_code == 200
    data = response.json()
    assert data["events"] == [], (
        f"Expected empty events list but got: {data['events']}"
    )
