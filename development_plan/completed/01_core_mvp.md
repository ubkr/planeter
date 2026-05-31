# Core MVP (Phases 1–7)

**Status:** Completed

**Phases included:** Phase 1 (Project Setup), Phase 2 (Planet Calculation Engine), Phase 3 (Weather & Utility Integration), Phase 4 (Visibility Scoring), Phase 5 (API Layer), Phase 6 (Frontend), Phase 7 (Testing)

---

## Intended Outcome (User Perspective)

The user opens the app and immediately sees which of the five naked-eye planets — Mercury, Venus, Mars, Jupiter, and Saturn — are visible from their location right now. Each planet has its own card showing its name in Swedish, its altitude and compass direction, a colour-coded score bar, and when it rises and sets. A sky summary banner at the top shows how many planets are worth looking for tonight. The user can tap a map button to pick any location in Sweden and the cards update instantly. All text is in Swedish. The app works on both mobile and desktop.

---

## Definition of Done

### Phase 1 — Project Setup
- All package directories exist and contain `__init__.py`
- `pip install -r backend/requirements.txt` completes without errors
- `start-backend.sh` starts uvicorn without import errors
- `GET /api/v1/health` returns HTTP 200 with a valid JSON body
- `backend/app/config.py` loads from `.env` without validation errors

### Phase 2 — Planet Calculation Engine
- `ephem` returns a non-zero altitude for Jupiter on 2025-06-15 00:00 UTC at lat=55.7, lon=13.4
- All five planets (Mercury, Venus, Mars, Jupiter, Saturn) appear in the returned list
- Each `PlanetPosition` object passes Pydantic validation (no missing required fields)
- Rise, transit, and set times are ISO 8601 strings or `null` when not applicable
- Altitude and azimuth values are within physically valid ranges (−90 to 90 and 0 to 360)

### Phase 3 — Weather & Utility Integration
- `from backend.app.utils.logger import get_logger` imports without error
- `from backend.app.utils.sun import get_sun_altitude` imports without error
- `from backend.app.services.weather.metno_client import MetNoClient` imports without error
- Weather client returns a cloud cover value (0–100) for lat=55.7, lon=13.4 against live API
- Cache service stores and retrieves a value within the same process

### Phase 4 — Visibility Scoring
- A planet at −1° altitude returns a score of 0
- A planet at 45° altitude with 0% cloud cover and sun at −20° returns a score above 70
- 100% cloud cover causes every planet's score to be 0
- Sun above 0° (daytime) causes every planet's score to be 0
- Moon penalty reduces score by a detectable amount when moon is within 10° and phase > 0.8
- `score_tonight` returns a value in the range 0–100

### Phase 5 — API Layer
- `GET /api/v1/planets/visible?lat=55.7&lon=13.4` returns HTTP 200 with a JSON array of planet objects
- Each planet object contains `name`, `altitude`, `azimuth`, `score`, and `rise_time`
- `GET /api/v1/planets/tonight?lat=55.7&lon=13.4` returns HTTP 200
- `GET /api/v1/planets/jupiter?lat=55.7&lon=13.4` returns HTTP 200 with a single planet object
- `GET /api/v1/planets/pluto?lat=55.7&lon=13.4` returns HTTP 404
- Invalid lat/lon values return HTTP 422 with a descriptive error message
- `GET /api/v1/health` returns HTTP 200

### Phase 6 — Frontend
- All five planet cards (Merkurius, Venus, Mars, Jupiter, Saturnus) render without console errors
- Each card displays altitude, azimuth direction, and a numeric score
- Score bar changes colour based on score value (red for low, green for high)
- Clicking the location button opens the Leaflet map picker
- Selecting a new location triggers a fresh API fetch and re-renders the cards
- Sky summary banner shows correct count of planets with score above 50
- Page is usable on a 375 px wide mobile viewport (no horizontal overflow)
- No JavaScript errors on initial load

### Phase 7 — Testing
- `pytest` exits with code 0 (all tests pass)
- Calculator test asserts Jupiter's altitude at a known date/location matches `ephem` reference output within 0.1°
- Scoring tests cover: altitude below horizon returns 0, cloud 100% returns 0, sun above 0° returns 0
- API integration test for `/visible` with invalid lat (lat=999) asserts HTTP 422
- API integration test for `/planets/pluto` asserts HTTP 404
- Test suite runs in under 30 seconds (weather calls are mocked)
- No test imports production secrets or makes real external HTTP calls
