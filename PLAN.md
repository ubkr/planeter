# Planetvis (Planeter) — Implementation Plan

## Overview

A web application that calculates which planets are visible from a specific location (primarily Sweden) at a given time. Reuses architecture, patterns, and components from the sibling `norrsken` (aurora visibility) project. Backend: Python FastAPI with the `ephem` library for astronomical calculations. Frontend: Vanilla HTML/CSS/JavaScript with Leaflet map picker.

## MVP Scope

The MVP answers one question: **"Which planets can I see from my location right now, and where do I look?"**

### MVP Features

1. Calculate positions (altitude, azimuth) of all naked-eye planets (Mercury, Venus, Mars, Jupiter, Saturn) for a given location and time
2. Determine rise/set times for each planet
3. Assess actual visibility considering: altitude above horizon, sun position (daylight penalty), cloud cover, planet apparent magnitude
4. Display results in a dark-themed UI showing each planet's status, direction, and visibility score
5. Location picker with map (reused from norrsken)
6. Weather/cloud cover integration (reused from norrsken)

## What to Reuse from norrsken

### Direct Copy and Adapt

| norrsken File | planeter Equivalent | Changes Needed | Status |
|---|---|---|---|
| `backend/app/config.py` | `backend/app/config.py` | Rename settings, change API title/description | ✅ Copied & adapted |
| `backend/app/utils/logger.py` | `backend/app/utils/logger.py` | None (copy as-is) | ✅ Copied |
| `backend/app/utils/sun.py` | `backend/app/utils/sun.py` | Copy as-is; used for daylight penalty | ✅ Copied |
| `backend/app/utils/moon.py` | `backend/app/utils/moon.py` | Adapt to compute moon brightness interference | ✅ Copied & adapted |
| `backend/app/services/cache_service.py` | `backend/app/services/cache_service.py` | None (copy as-is) | ✅ Copied |
| `backend/app/services/weather/base.py` | `backend/app/services/weather/base.py` | None (copy as-is) | ✅ Copied |
| `backend/app/services/weather/metno_client.py` | `backend/app/services/weather/metno_client.py` | Copy as-is | ✅ Copied |
| `backend/app/services/weather/openmeteo_client.py` | `backend/app/services/weather/openmeteo_client.py` | Copy as-is | ✅ Copied |
| `backend/app/models/weather.py` | `backend/app/models/weather.py` | Copy as-is | ✅ Copied |
| `backend/app/main.py` | `backend/app/main.py` | Change router registrations | ✅ Copied & adapted |
| `backend/app/api/routes/health.py` | `backend/app/api/routes/health.py` | Copy as-is | ✅ Copied & adapted |
| `frontend/js/location-manager.js` | `frontend/js/location-manager.js` | Change storage key from `aurora_location` to `planet_location` | ✅ Copied & adapted |
| `frontend/js/components/map-selector.js` | `frontend/js/components/map-selector.js` | Copy as-is | ✅ Copied |
| `frontend/js/components/settings-modal.js` | `frontend/js/components/settings-modal.js` | Copy as-is | ✅ Copied & adapted |
| `frontend/js/components/tooltip.js` | `frontend/js/components/tooltip.js` | Copy as-is | ✅ Copied |
| `frontend/css/tokens.css` | `frontend/css/tokens.css` | Adjust accent colors to a planetary theme | ✅ Copied & adapted |
| `frontend/css/base.css` | `frontend/css/base.css` | Minor adjustments | ✅ Copied |
| `frontend/css/layout.css` | `frontend/css/layout.css` | Copy as-is | ✅ Copied |
| `frontend/css/components/modal.css` | `frontend/css/components/modal.css` | Copy as-is | ✅ Copied |
| `start-backend.sh` | `start-backend.sh` | Change paths | ✅ Copied & adapted |
| `start-frontend.sh` | `start-frontend.sh` | Change paths | — Not present in norrsken; create in Phase 6 |

### Build from Scratch

| Component | Description |
|---|---|
| `backend/app/services/planets/calculator.py` | Core planet position engine using `ephem` |
| `backend/app/services/scoring.py` | Planet visibility scoring algorithm |
| `backend/app/models/planet.py` | Pydantic models for planet data |
| `backend/app/api/routes/planets.py` | API endpoints for planet visibility |
| `frontend/js/components/planet-cards.js` | UI cards showing each planet's status |
| `frontend/js/components/sky-summary.js` | Overview showing tonight's visible planets |
| `frontend/js/api.js` | API client adapted for planet endpoints |
| `frontend/index.html` | New page layout for planet display |
| `frontend/css/components/planet-cards.css` | Styling for planet cards |

---

## Phase-by-Phase Execution

## Phase 1: Project Setup — [ ]

**Depends on**: none
**Parallelisable with**: none

### Tasks
- ✅ Already in place — directory structure created: `backend/app/`, `backend/app/api/routes/`, `backend/app/models/`, `backend/app/services/planets/`, `backend/app/utils/`, `frontend/js/components/`, `frontend/css/components/`
- ✅ Already in place — all `__init__.py` files created in every Python package directory
- ✅ Already in place — `backend/requirements.txt` copied from norrsken; removed `apscheduler` and `aiofiles`
- ✅ Already in place — `backend/app/config.py` adapted: title "Planeter API", description "Planet visibility calculations for Sweden", removed aurora-specific fields, added `openmeteo_base_url`
- ✅ Already in place — `backend/app/main.py` adapted: aurora/prediction/weather routers removed, health and geocode registered, TODO stub for planets router
- ✅ Already in place — `start-backend.sh` copied and paths updated to planeter
- Copy `start-frontend.sh` from norrsken — update paths to planeter frontend directory (norrsken has no `start-frontend.sh`; create in Phase 6 alongside `index.html`)
- ✅ Already in place — `.env` and `.env.example` created with placeholder values

### Intended Outcome
The project directory exists in its final shape. The backend starts (uvicorn) and responds to requests; the health endpoint returns 200. No planet logic is wired yet.

### Definition of Done
- [ ] All package directories exist and contain `__init__.py`
- [ ] `pip install -r backend/requirements.txt` completes without errors
- [ ] `start-backend.sh` starts uvicorn without import errors
- [ ] `GET /api/v1/health` returns HTTP 200 with a valid JSON body
- [ ] `backend/app/config.py` loads from `.env` without validation errors

---

## Phase 2: Planet Calculation Engine — [ ]

**Depends on**: Phase 1
**Parallelisable with**: Phase 3

### Tasks
- Build `backend/app/models/planet.py` — Pydantic models `PlanetPosition` and `PlanetData` covering altitude, azimuth, magnitude, constellation, rise/transit/set times
- Build `backend/app/services/planets/calculator.py` — implement `calculate_planet_positions(lat, lon, dt) -> list[PlanetPosition]` using `ephem`
- Compute per-planet fields for Mercury, Venus, Mars, Jupiter, Saturn: altitude (degrees), azimuth (degrees), apparent magnitude, constellation name, rise time, transit time, set time
- Handle circumpolar and never-rises edge cases (rise/set can be None)

### Intended Outcome
A single function call with a latitude, longitude, and datetime returns a fully populated list of `PlanetPosition` objects for all five naked-eye planets, computed via `ephem`.

### Definition of Done
- [ ] `ephem` returns a non-zero altitude for Jupiter on 2025-06-15 00:00 UTC at lat=55.7, lon=13.4
- [ ] All five planets (Mercury, Venus, Mars, Jupiter, Saturn) appear in the returned list
- [ ] Each `PlanetPosition` object passes Pydantic validation (no missing required fields)
- [ ] Rise, transit, and set times are ISO 8601 strings or `null` when not applicable
- [ ] Altitude and azimuth values are within physically valid ranges (−90 to 90 and 0 to 360 respectively)

---

## Phase 3: Weather and Utility Integration — [ ]

**Depends on**: Phase 1
**Parallelisable with**: Phase 2

### Tasks
- ✅ Already in place — `backend/app/utils/logger.py` copied from norrsken; no changes needed
- ✅ Already in place — `backend/app/utils/sun.py` copied from norrsken; used as-is for daylight penalty
- ✅ Already in place — `backend/app/utils/moon.py` copied and extended: added `get_moon_angular_separation()` function for planet proximity scoring
- ✅ Already in place — `backend/app/services/cache_service.py` copied from norrsken; no changes needed
- ✅ Already in place — `backend/app/services/weather/base.py` copied from norrsken; no changes needed
- ✅ Already in place — `backend/app/services/weather/metno_client.py` copied from norrsken; no changes needed
- ✅ Already in place — `backend/app/services/weather/openmeteo_client.py` copied from norrsken; no changes needed
- ✅ Already in place — `backend/app/models/weather.py` copied from norrsken; no changes needed

### Intended Outcome
All weather service files, utility modules, and the cache service are present and importable. Weather data can be fetched for a lat/lon coordinate and cloud cover retrieved as a numeric value.

### Definition of Done
- [ ] `from backend.app.utils.logger import get_logger` imports without error
- [ ] `from backend.app.utils.sun import get_sun_altitude` imports without error
- [ ] `from backend.app.services.weather.metno_client import MetNoClient` imports without error
- [ ] Weather client returns a cloud cover value (0–100) for lat=55.7, lon=13.4 when called against live API (or a mocked response in tests)
- [ ] Cache service stores and retrieves a value within the same process

---

## Phase 4: Visibility Scoring — [ ]

**Depends on**: Phase 2, Phase 3
**Parallelisable with**: Phase 6 (frontend scaffolding can begin)

### Tasks
- Build `backend/app/services/scoring.py` — implement `score_planet(planet: PlanetPosition, sun_altitude: float, cloud_cover: float, moon_phase: float, moon_separation: float) -> int`
- Altitude penalty — zero score below 0°, linearly scaling up to full weight at 30°+
- Apparent magnitude factor — brighter planets (lower magnitude) score higher
- Sun elevation penalty — full penalty when sun is above −6° (civil twilight), partial at −6° to −18°
- Cloud cover penalty — linear reduction; 100% cloud cover zeroes the score
- Atmospheric extinction penalty — increases rapidly below 10° altitude
- Moon proximity penalty — reduce score when moon is within 15° of the planet and phase is above 0.5
- Implement `score_tonight(planets: list[PlanetPosition], ...) -> int` — overall sky summary score (0–100)

### Intended Outcome
Given a list of planet positions plus weather and solar data, the scoring module returns a 0–100 integer score for each planet and an aggregate tonight score. Scores behave sensibly at boundary conditions (planet below horizon = 0, fully overcast = 0, excellent conditions = high score).

### Definition of Done
- [ ] A planet at −1° altitude returns a score of 0
- [ ] A planet at 45° altitude with 0% cloud cover and sun at −20° returns a score above 70
- [ ] 100% cloud cover causes every planet's score to be 0
- [ ] Sun above 0° (daytime) causes every planet's score to be 0
- [ ] Moon penalty reduces score by a detectable amount when moon is within 10° and phase > 0.8
- [ ] `score_tonight` returns a value in the range 0–100

---

## Phase 5: API Layer — [ ]

**Depends on**: Phase 4
**Parallelisable with**: none

### Tasks
- ✅ Already in place — `backend/app/api/routes/health.py` copied from norrsken; service name changed to `planeter-api`
- Build `backend/app/api/routes/planets.py` — implement three endpoints:
  - `GET /api/v1/planets/visible?lat=&lon=` — returns currently visible planets with positions and scores
  - `GET /api/v1/planets/tonight?lat=&lon=` — returns all planets with tonight's visibility windows
  - `GET /api/v1/planets/{name}?lat=&lon=` — returns detailed info for a single named planet
- Register the planets router in `backend/app/main.py`
- Add input validation — lat must be −90 to 90, lon must be −180 to 180, planet name must be one of the five valid names
- Return structured error responses (422 for invalid input, 404 for unknown planet name)

### Intended Outcome
All three planet endpoints are reachable and return valid JSON. The `/visible` endpoint integrates planet calculation, weather fetch, and scoring into a single response. Health endpoint still works.

### Definition of Done
- [ ] `GET /api/v1/planets/visible?lat=55.7&lon=13.4` returns HTTP 200 with a JSON array of planet objects
- [ ] Each planet object in the response contains `name`, `altitude`, `azimuth`, `score`, and `rise_time`
- [ ] `GET /api/v1/planets/tonight?lat=55.7&lon=13.4` returns HTTP 200
- [ ] `GET /api/v1/planets/jupiter?lat=55.7&lon=13.4` returns HTTP 200 with a single planet object
- [ ] `GET /api/v1/planets/pluto?lat=55.7&lon=13.4` returns HTTP 404
- [ ] Invalid lat/lon values return HTTP 422 with a descriptive error message
- [ ] `GET /api/v1/health` still returns HTTP 200

---

## Phase 6: Frontend — [ ]

**Depends on**: Phase 5
**Parallelisable with**: Phase 4 (scaffolding and static layout can begin before Phase 5 is done)

### Tasks
- ✅ Already in place — `frontend/js/location-manager.js` adapted: storage key changed from `aurora_location` to `planet_location`
- ✅ Already in place — `frontend/js/components/map-selector.js` copied from norrsken; no changes needed
- ✅ Already in place — `frontend/js/components/settings-modal.js` adapted: title changed to "Inställningar", button text in Swedish, aurora-specific fields removed
- ✅ Already in place — `frontend/js/components/tooltip.js` copied from norrsken; no changes needed
- ✅ Already in place — `frontend/css/tokens.css` adapted: primary accent changed to warm gold `#f5c842`, secondary to deep blue `#3b82f6`, aurora-specific metric color renamed
- ✅ Already in place — `frontend/css/base.css` copied from norrsken; no changes needed
- ✅ Already in place — `frontend/css/layout.css` copied from norrsken; no changes needed
- ✅ Already in place — `frontend/css/components/modal.css` copied from norrsken; no changes needed
- Build `frontend/index.html` — dark-themed page layout with planet card grid, sky summary banner, location picker trigger, and settings icon
- Build `frontend/js/api.js` — functions `fetchVisiblePlanets(lat, lon)`, `fetchTonightPlanets(lat, lon)`, `fetchPlanet(name, lat, lon)` calling the planeter API
- Build `frontend/js/components/planet-cards.js` — renders one card per planet showing name (Swedish), altitude, azimuth compass direction, score bar, rise/set times
- Build `frontend/js/components/sky-summary.js` — renders the top-level "tonight's sky" banner with overall score and count of visible planets
- Build `frontend/css/components/planet-cards.css` — dark card style with score colour gradient (red → amber → green)
- Create `start-frontend.sh` — simple static file server for the frontend directory

### Intended Outcome
Opening `index.html` in a browser shows the full planet visibility UI. All five planet cards render with live data from the API. The location map picker works. Labels and planet names are in Swedish.

### Definition of Done
- [ ] All five planet cards (Merkurius, Venus, Mars, Jupiter, Saturnus) render in the browser without console errors
- [ ] Each card displays altitude, azimuth direction, and a numeric score
- [ ] Score bar changes colour based on score value (red for low, green for high)
- [ ] Clicking the location button opens the Leaflet map picker
- [ ] Selecting a new location on the map triggers a fresh API fetch and re-renders the cards
- [ ] Sky summary banner shows correct count of planets with score above 50
- [ ] Page is usable on a 375 px wide mobile viewport (no horizontal overflow)
- [ ] No JavaScript errors in the browser console on initial load

---

## Phase 7: Testing — [ ]

**Depends on**: Phase 1, Phase 2, Phase 3, Phase 4, Phase 5, Phase 6
**Parallelisable with**: none

### Tasks
- Read existing norrsken test files to understand patterns before writing any tests
- Write unit tests for `calculator.py` — known planet positions at fixed dates and locations
- Write unit tests for `scoring.py` — boundary conditions (below horizon, full cloud, full sun, moon penalty)
- Write integration tests for `GET /api/v1/planets/visible` — valid input, invalid lat/lon, unknown planet name
- Write integration tests for `GET /api/v1/planets/tonight` and `GET /api/v1/planets/{name}`
- Write integration test for `GET /api/v1/health`
- Configure `pytest.ini` or `pyproject.toml` with asyncio mode and test paths

### Intended Outcome
Running `pytest` from the backend directory executes all tests and they pass. Test output is readable and failures identify the specific assertion that broke.

### Definition of Done
- [ ] `pytest` exits with code 0 (all tests pass)
- [ ] Calculator test asserts Jupiter's altitude at a known date/location matches `ephem` reference output within 0.1°
- [ ] Scoring tests cover: altitude below horizon returns 0, cloud 100% returns 0, sun above 0° returns 0
- [ ] API integration test for `/visible` with invalid lat (e.g. lat=999) asserts HTTP 422
- [ ] API integration test for `/planets/pluto` asserts HTTP 404
- [ ] Test suite runs in under 30 seconds (weather calls are mocked)
- [ ] No test imports production secrets or makes real external HTTP calls

---

## Confirmed Decisions

| Question | Decision |
|---|---|
| Planet scope | **Naked-eye only**: Mercury, Venus, Mars, Jupiter, Saturn |
| Time selection | **Right now + tonight**: current positions, plus tonight's visibility windows (sunset → sunrise) |
| UI language | **Swedish**: all labels, planet names, and UI text in Swedish |
| Cloud cover | **Affects visibility score**: overcast sky reduces or zeroes a planet's score |
| Default location | Södra Sandby (55.7°N, 13.4°E) — same as norrsken |
| Uranus/Neptune | Not in scope for MVP; can be added in a future phase |

## Future Roadmap

### Phase A: Sky Map
- Interactive sky map showing planet positions on a hemispherical projection
- Use HTML5 Canvas or SVG to render the sky dome
- Show cardinal directions, horizon line, zenith
- Plot planets with size proportional to brightness

### Phase B: Observation Tips
- Best viewing times for each planet (when highest above horizon in darkness)
- "What to look for" descriptions (colour, brightness, nearby stars)
- Telescope vs. binocular vs. naked-eye guidance
- Conjunction and opposition alerts

### Phase C: Extended Bodies
- Add Uranus and Neptune (telescope targets)
- Add bright asteroids (Vesta, Ceres)
- Add comets (when notable ones are active)
- International Space Station pass predictions

### Phase D: Notifications
- Push notifications for rare events (conjunctions, oppositions, Mercury visibility windows)
- "Tonight's highlights" daily summary
