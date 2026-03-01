"""
Integration tests for the /api/v1/health endpoint.

All tests use:
  - async_client  — httpx AsyncClient wired to the FastAPI ASGI app.

asyncio_mode = auto is set in pytest.ini so no @pytest.mark.asyncio is needed.

The health endpoint has no external dependencies (no weather or astronomy
calls), so mock_weather is not needed here.

Endpoint: GET /api/v1/health
Expected response shape:
  {
    "status":    "healthy",
    "service":   "planeter-api",
    "timestamp": "<ISO-8601 string ending in Z>"
  }
"""


# ---------------------------------------------------------------------------
# 1. Status code
# ---------------------------------------------------------------------------

async def test_health_returns_200(async_client):
    response = await async_client.get("/api/v1/health")
    assert response.status_code == 200


# ---------------------------------------------------------------------------
# 2. Response shape
# ---------------------------------------------------------------------------

async def test_health_response_shape(async_client):
    response = await async_client.get("/api/v1/health")
    body = response.json()

    # "status" must be the literal string "healthy".
    assert body.get("status") == "healthy", (
        f"Expected status='healthy', got {body.get('status')!r}"
    )

    # "service" must match the value declared in the health route handler.
    assert body.get("service") == "planeter-api", (
        f"Expected service='planeter-api', got {body.get('service')!r}"
    )

    # "timestamp" must be present and non-empty (exact value varies by run time).
    timestamp = body.get("timestamp")
    assert isinstance(timestamp, str) and len(timestamp) > 0, (
        f"Expected a non-empty string for 'timestamp', got {timestamp!r}"
    )
