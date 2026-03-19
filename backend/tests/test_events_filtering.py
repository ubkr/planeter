"""
Tests for location-based event altitude filtering (Phase B7).

The /api/v1/events route removes events where altitude_deg is a non-null
negative number.  Events where altitude_deg is None or >= 0 are kept.

All tests mock detect_events and the cache so that:
  - No real ephem computation takes place.
  - The cache never returns a stale hit from a prior test.

Patch targets (pythonpath = backend/, so the package root is 'app'):
  - app.api.routes.events.detect_events  — controls returned events.
  - app.api.routes.events.cache          — prevents cache read/write side-effects.

asyncio_mode = auto is set in pytest.ini so no @pytest.mark.asyncio is needed
on async test functions — pytest-asyncio collects them automatically.
"""

from typing import List
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.models.planet import AstronomicalEvent


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_ENDPOINT = "/api/v1/events"
_DEFAULT_PARAMS = {"lat": 59.3, "lon": 18.1}

# Minimal set of required fields for AstronomicalEvent.
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


def _make_cache_mock() -> MagicMock:
    """Return a mock that behaves like CacheService with a cold cache."""
    mock = MagicMock()
    mock.get = AsyncMock(return_value=None)
    mock.set = AsyncMock(return_value=None)
    return mock


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

async def test_negative_altitude_event_is_excluded(async_client):
    """An event with altitude_deg = -5.0 must be removed from the response."""
    event = _make_event(altitude_deg=-5.0)

    with patch("app.api.routes.events.detect_events", return_value=[event]), \
         patch("app.api.routes.events.cache", _make_cache_mock()):
        response = await async_client.get(_ENDPOINT, params=_DEFAULT_PARAMS)

    assert response.status_code == 200
    data = response.json()
    assert data["events"] == [], (
        f"Expected empty events list but got: {data['events']}"
    )


async def test_positive_altitude_event_is_retained(async_client):
    """An event with altitude_deg = 15.0 must be kept in the response."""
    event = _make_event(altitude_deg=15.0)

    with patch("app.api.routes.events.detect_events", return_value=[event]), \
         patch("app.api.routes.events.cache", _make_cache_mock()):
        response = await async_client.get(_ENDPOINT, params=_DEFAULT_PARAMS)

    assert response.status_code == 200
    data = response.json()
    assert len(data["events"]) == 1, (
        f"Expected 1 event but got {len(data['events'])}"
    )
    assert data["events"][0]["altitude_deg"] == 15.0


async def test_null_altitude_event_is_retained(async_client):
    """An event with altitude_deg = None must be kept (conservative pass-through)."""
    event = _make_event(altitude_deg=None)

    with patch("app.api.routes.events.detect_events", return_value=[event]), \
         patch("app.api.routes.events.cache", _make_cache_mock()):
        response = await async_client.get(_ENDPOINT, params=_DEFAULT_PARAMS)

    assert response.status_code == 200
    data = response.json()
    assert len(data["events"]) == 1, (
        f"Expected 1 event but got {len(data['events'])}"
    )
    assert data["events"][0]["altitude_deg"] is None


async def test_zero_altitude_event_is_retained(async_client):
    """An event with altitude_deg = 0.0 (exactly on horizon) must be kept."""
    event = _make_event(altitude_deg=0.0)

    with patch("app.api.routes.events.detect_events", return_value=[event]), \
         patch("app.api.routes.events.cache", _make_cache_mock()):
        response = await async_client.get(_ENDPOINT, params=_DEFAULT_PARAMS)

    assert response.status_code == 200
    data = response.json()
    assert len(data["events"]) == 1, (
        f"Expected 1 event but got {len(data['events'])}"
    )
    assert data["events"][0]["altitude_deg"] == 0.0


async def test_all_events_filtered_returns_empty_list_with_200(async_client):
    """When all events are below the horizon, the response is HTTP 200 with an empty events list."""
    events: List[AstronomicalEvent] = [
        _make_event(altitude_deg=-10.0),
        _make_event(altitude_deg=-1.5),
        _make_event(altitude_deg=-45.0),
    ]

    with patch("app.api.routes.events.detect_events", return_value=events), \
         patch("app.api.routes.events.cache", _make_cache_mock()):
        response = await async_client.get(_ENDPOINT, params=_DEFAULT_PARAMS)

    assert response.status_code == 200
    data = response.json()
    assert data["events"] == [], (
        f"Expected empty events list but got: {data['events']}"
    )


async def test_just_below_horizon_event_is_excluded(async_client):
    """An event with altitude_deg = -0.001 (just below horizon) must be excluded."""
    event = _make_event(altitude_deg=-0.001)

    with patch("app.api.routes.events.detect_events", return_value=[event]), \
         patch("app.api.routes.events.cache", _make_cache_mock()):
        response = await async_client.get(_ENDPOINT, params=_DEFAULT_PARAMS)

    assert response.status_code == 200
    data = response.json()
    assert data["events"] == [], (
        f"Expected empty events list but got: {data['events']}"
    )


async def test_filtering_depends_on_location_altitude(async_client):
    """
    The filter must use the altitude_deg value that detect_events computes for
    each specific location — not a static rule.

    Location A (59.3, 18.1): detect_events returns altitude_deg = -5.0
      → event is below the horizon → 0 events in response.

    Location B (57.7, 11.9): detect_events returns altitude_deg = 15.0
      → event is above the horizon → 1 event in response.

    This proves that the same event type can appear or be filtered depending on
    the actual altitude value supplied per location.
    """
    params_a = {"lat": 59.3, "lon": 18.1}
    params_b = {"lat": 57.7, "lon": 11.9}

    event_below = _make_event(altitude_deg=-5.0)
    event_above = _make_event(altitude_deg=15.0)

    # Location A — event is below the horizon.
    with patch("app.api.routes.events.detect_events", return_value=[event_below]), \
         patch("app.api.routes.events.cache", _make_cache_mock()):
        response_a = await async_client.get(_ENDPOINT, params=params_a)

    # Location B — same event type but above the horizon.
    with patch("app.api.routes.events.detect_events", return_value=[event_above]), \
         patch("app.api.routes.events.cache", _make_cache_mock()):
        response_b = await async_client.get(_ENDPOINT, params=params_b)

    assert response_a.status_code == 200
    assert response_b.status_code == 200

    data_a = response_a.json()
    data_b = response_b.json()

    assert len(data_a["events"]) == 0, (
        f"Location A: expected 0 events (below horizon) but got {len(data_a['events'])}"
    )
    assert len(data_b["events"]) == 1, (
        f"Location B: expected 1 event (above horizon) but got {len(data_b['events'])}"
    )
