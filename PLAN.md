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

## Phase 1: Project Setup — ✅

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

## Phase 2: Planet Calculation Engine — ✅

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

## Phase 3: Weather and Utility Integration — ✅

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

## Phase 4: Visibility Scoring — ✅

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

## Phase 5: API Layer — ✅

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

## Phase 6: Frontend — ✅

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

## Phase 7: Testing — ✅

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

## Phase 8: Visibility Reason Tooltips — ✅

**Depends on**: Phase 4, Phase 5, Phase 6
**Parallelisable with**: Phase 7

### Tasks
- Extend `backend/app/models/planet.py` — add a `visibility_reasons: list[str]` field to `PlanetData`; reasons are short machine-readable keys, e.g. `"below_horizon"`, `"dagsljus"`, `"molnighet"`, `"månljus"`, `"atmosfärisk_dämpning"`
- Extend `backend/app/services/scoring.py` — collect the active penalty factors during scoring and populate `visibility_reasons` on the returned object; a planet with a zero score should carry at least one reason
- Update `backend/app/api/routes/planets.py` — confirm that `visibility_reasons` is included in all three endpoint responses (`/visible`, `/tonight`, `/{name}`)
- Extend `frontend/js/components/planet-cards.js` — attach a tooltip (via the existing `tooltip.js` component) to the visibility-status text on each planet card; the tooltip content is built from `visibility_reasons` and rendered in Swedish
- Add Swedish reason-label lookup in `frontend/js/utils.js` — map each reason key to a human-readable Swedish string, e.g. `"below_horizon"` → `"Planeten är under horisonten"`, `"dagsljus"` → `"För ljust – solen är uppe"`, `"molnighet"` → `"Molnen blockerar sikten"`, `"månljus"` → `"Månens sken stör observationen"`, `"atmosfärisk_dämpning"` → `"Atmosfärisk dämpning vid låg höjd"`
- Update `frontend/css/components/planet-cards.css` — style the visibility-status text with a dashed underline to signal that it is hoverable

### Intended Outcome
Hovering over the visibility text on any planet card (e.g. "Ej synlig" or "Synlig") opens a small tooltip listing in plain Swedish why the planet is or is not observable. All relevant factors — cloud cover, daylight, moon interference, horizon obstruction, and atmospheric extinction — can appear independently or in combination.

### Definition of Done
- [ ] `PlanetData` includes a non-empty `visibility_reasons` list for every planet whose score is below 100
- [ ] A planet below the horizon always carries the reason `"below_horizon"` and never a positive score
- [ ] A planet hidden by cloud cover carries `"molnighet"` regardless of its altitude or score
- [ ] Hovering the visibility text in the browser shows a tooltip with at least one Swedish-language reason string
- [ ] Multiple simultaneous factors (e.g. low altitude + partial cloud cover) each appear as separate lines in the tooltip
- [ ] Planets with a high score and no active penalties show no tooltip, or the tooltip states "Goda observationsförhållanden"
- [ ] Tooltip is keyboard-accessible (visible on focus) and dismissed on blur or mouse-leave
- [ ] No JavaScript errors are thrown when `visibility_reasons` is an empty array

---

## Phase 9: Scoring Accuracy and Scale Calibration — ✅

**Depends on**: Phase 4, Phase 6
**Parallelisable with**: Phase 10, Phase 11

### Tasks

- **Fix the `is_visible` twilight threshold** in `backend/app/services/scoring.py` `apply_scores()`. Change `sun_altitude < -6` to `sun_altitude < -12` so that `is_visible` requires nautical twilight or darker, matching the specification in ARCHITECTURE.md ("twilight phase is nautical twilight or darker"). The existing inline comment on the `is_visible` condition already labels the threshold "nautical twilight or darker", which is correct for −12°; once the threshold value is fixed to −12, no other comment change is needed.
- **Recalibrate scoring component weights** so the full 0–100 range is reachable. The current components (altitude 0–30, magnitude 0–20, cloud cover 0–30) sum to at most 80. Adjust the positive components to: altitude 0–40, magnitude 0–25, cloud cover 0–35, totalling 100. Update `score_planet()` in `backend/app/services/scoring.py` accordingly. Update the scoring table in `ARCHITECTURE.md` to match.
- **Fix visible-planet count in sky summary** in `frontend/js/components/sky-summary.js`. Change `planets.filter(p => p.is_visible)` to `planets.filter(p => p.visibility_score > 50)` so the count matches the Phase 6 Definition of Done ("planets with score above 50").
- **Update `scoreToLevel` tier boundaries** in `frontend/js/utils.js` if the recalibrated scale shifts where "good" and "excellent" begin. Ensure "excellent" is reachable under realistic best-case conditions (clear sky, planet at 45+ degrees altitude, full darkness).

### Intended Outcome
The visibility score accurately reflects real-world observing conditions for every planet. The full 0–100 scale is reachable: a planet under ideal conditions (clear sky, high altitude, full darkness) scores at least 90. The `is_visible` flag only flips true when it is genuinely dark enough to observe, and the sky summary correctly counts planets with a score above 50. The score is the single most important number the app produces — it drives the `is_visible` flag, the sky summary, the card colours, and the tooltip reasons. The three problems addressed here (twilight threshold, unreachable scale ceiling, wrong visible-count criterion) are corrections to existing modules, not new features; fixing them together ensures the number a user sees genuinely reflects what they would experience outside.

### Definition of Done

- [ ] `apply_scores()` sets `is_visible = False` for a planet when the sun altitude is -8 degrees (between civil and nautical twilight), even if the planet is above the horizon with a positive score
- [ ] `apply_scores()` sets `is_visible = True` for a planet when the sun altitude is -14 degrees (nautical twilight), the planet is at 30 degrees altitude, cloud cover is 0%, and the score exceeds 15
- [ ] A planet at 45 degrees altitude with magnitude −4.0, 0% cloud cover, sun at −20 degrees, and no moon proximity penalty produces a score of 100 (all positive components are at maximum and all penalties are zero)
- [ ] The `scoreToLevel` function returns `"excellent"` for a score of 95
- [ ] The sky summary visible count shows 0 when all five planets have scores between 16 and 50 (previously would have shown them as visible via the `is_visible` flag)
- [ ] The ARCHITECTURE.md scoring table matches the new component weights in `score_planet()`
- [ ] No existing Phase 8 tooltip behaviour is broken — `visibility_reasons` still populates correctly

---

## Phase 10: Backend Cleanup — Dead Code and Redundant Computation — ✅

**Depends on**: Phase 5, Phase 6
**Parallelisable with**: Phase 9, Phase 11

### Tasks

- **Remove the unused `penalty_pts` return value from `calculate_moon_penalty()`** in `backend/app/utils/moon.py`. The scorer computes its own moon proximity penalty via `get_moon_angular_separation()` and never reads `penalty_pts`. Remove the `penalty_pts` computation and drop it from the returned dict. Audit all callers (`scoring.py` `apply_scores()`, `planets.py` `_build_moon_info()`) to confirm none read the field.
- **Eliminate the double sun/moon computation in the `/visible` endpoint** in `backend/app/api/routes/planets.py`. Currently `apply_scores()` calls `calculate_sun_penalty()` and `calculate_moon_penalty()` internally, and then the route handler calls `_build_sun_info()` and `_build_moon_info()` which call the same two functions again. Refactor so the sun and moon data are computed once and passed through. Preferred approach: compute sun/moon data in the route handler first, then pass it into `apply_scores()`, keeping `apply_scores()` a pure scoring function. Apply the same fix to the `/tonight` and `/{name}` endpoints.
- **Mark `fetchTonightPlanets()` as reserved for a future phase** in `frontend/js/api.js`. Add a clear comment on the function explaining that it is not called by the current UI and why — the backend `/tonight` endpoint has sophisticated night-window sampling that the current UI does not yet consume.

### Intended Outcome
The backend has no dead code or duplicate computation. Each request triggers exactly one sun calculation and one moon calculation regardless of which endpoint is called. `frontend/js/api.js` no longer contains a live function that silently calls an endpoint whose results are never used. This phase addresses two kinds of waste inherited from the rapid copy-and-build process: dead code that misleads anyone reading the module, and redundant computation that calls the same `ephem` functions twice per request. Cleaning these up now — before Phase 7 (Testing) writes assertions against the current interfaces — prevents dead code from being enshrined in tests. Note: Phase 10 must be completed before Phase 7 writes its `scoring.py` unit tests, because Phase 10 changes the internal signature of `apply_scores()` and tests written against the old signature would require immediate rework. This phase is refactoring only: no new features, no API changes, no frontend changes.

### Definition of Done

- [ ] `calculate_moon_penalty()` no longer contains a `penalty_pts` key in its returned dict
- [ ] `_build_moon_info()` still constructs a valid `MoonInfo` object after the `penalty_pts` key is removed
- [ ] The `/visible` endpoint makes exactly one call to `calculate_sun_penalty()` and one call to `calculate_moon_penalty()` per request
- [ ] The `/tonight` and `/{name}` endpoints also avoid double computation
- [ ] `fetchTonightPlanets()` in `frontend/js/api.js` carries a clear comment marking it as reserved for a future phase and explaining why it is not called by the current UI
- [ ] All three API endpoints (`/visible`, `/tonight`, `/{name}`) return identical response shapes as before — no fields added, removed, or renamed
- [ ] `GET /api/v1/health` still returns HTTP 200

---

## Phase 11: Frontend Cleanup — Dead CSS and Coordinate Formatting — ✅

**Depends on**: Phase 6
**Parallelisable with**: Phase 9, Phase 10

### Tasks

- **Remove dead norrsken grid selectors from `frontend/css/layout.css`**. Delete the `.score-section`, `.data-grid-section`, and `.chart-section` rules. These selectors targeted norrsken's dashboard layout and have no corresponding elements in planeter's `index.html`. After removing those three rules, audit every remaining rule in the `@media (min-width: 900px)` block by cross-referencing each selector against `frontend/index.html`. Remove any additional rules whose selectors have no corresponding element in the planeter DOM. Leave the `@media` block intact if other rules inside it are still needed; remove the entire block if it becomes empty.
- **Fix `formatLocation()` hemisphere labels** in `frontend/js/utils.js`. Currently the fallback format always appends "N" and "O" regardless of the sign of lat/lon. Change it to append "N"/"S" based on the sign of latitude and "Ö"/"V" (Öst/Väst in Swedish) based on the sign of longitude. Use the absolute value of the coordinate for display so that negative signs do not appear alongside the hemisphere letter.

### Intended Outcome
`frontend/css/layout.css` contains only rules that apply to elements present in planeter's DOM. `formatLocation()` in `frontend/js/utils.js` produces correct hemisphere labels for any coordinate on Earth, not just the positive-lat/positive-lon case that covers Sweden. Two issues carried over from the norrsken copy are resolved: layout CSS targeting selectors that do not exist in planeter's DOM (which adds noise to the stylesheet and would confuse anyone reading the grid layout), and a coordinate formatter that hardcodes Northern and Eastern hemisphere labels (a bug invisible for Sweden but wrong for any location outside the positive-lat/positive-lon quadrant). This phase is cleanup only: no new features, no backend changes.

### Definition of Done

- [ ] Confirm that `index.html` contains no elements with class `score-section`, `data-grid-section`, or `chart-section` before removing the CSS rules (search `frontend/index.html` for these class names)
- [ ] `layout.css` contains no rules targeting `.score-section`, `.data-grid-section`, or `.chart-section`
- [ ] The `@media (min-width: 900px)` block in `layout.css` either contains only planeter-relevant rules or is removed entirely
- [ ] `formatLocation({ lat: 55.7, lon: 13.4 })` returns `"55.70°N, 13.40°Ö"` (unchanged for Swedish positive-coordinate case)
- [ ] `formatLocation({ lat: -33.9, lon: 18.4 })` returns `"33.90°S, 18.40°Ö"` (southern hemisphere)
- [ ] `formatLocation({ lat: 40.7, lon: -74.0 })` returns `"40.70°N, 74.00°V"` (western hemisphere)
- [ ] `formatLocation({ lat: -34.6, lon: -58.4 })` returns `"34.60°S, 58.40°V"` (southern and western)
- [ ] `formatLocation({ lat: 55.7, lon: 13.4, name: "Södra Sandby" })` returns `"Södra Sandby"` (name takes precedence, unchanged)
- [ ] Page renders correctly at 375px and 1200px viewport widths with no layout regressions from the CSS removal
- [ ] No JavaScript console errors on initial page load

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

#### Phase A1: Sky Map Tab Shell and Navigation — ⬜

**Depends on:** Phase 6 (Frontend)

**Intended Outcome**

The app gains a tab bar below the header with two tabs: "Planeter" (the existing default view) and "Stjärnkarta" (sky map). Clicking "Stjärnkarta" hides the planet cards and sky summary and shows an empty sky map container with a placeholder message. Clicking "Planeter" restores the original view with the active tab visually indicated. The entire existing UI continues to work exactly as before when the "Planeter" tab is active.

**Definition of Done**
- [ ] A tab bar renders below the header with exactly two tabs labelled "Planeter" and "Stjärnkarta"
- [ ] On initial page load the "Planeter" tab is active and the planet cards and sky summary are visible
- [ ] Clicking "Stjärnkarta" hides `#skySummary` and `#planetCards` and shows `#skyMapContainer`
- [ ] Clicking "Planeter" hides `#skyMapContainer` and shows `#skySummary` and `#planetCards`
- [ ] The active tab uses `--color-accent-primary` as its visual indicator
- [ ] Tab bar is usable on a 375 px mobile viewport with no horizontal overflow
- [ ] Switching tabs does not trigger an API re-fetch; both views share the same data
- [ ] No JavaScript console errors when switching tabs rapidly
- [ ] `aria-selected` and `role="tab"` / `role="tabpanel"` attributes are set correctly for accessibility
- [ ] Tab bar and container use existing design tokens for colours, spacing, borders, and typography

**Key files**
- Modify `frontend/index.html` — add tab bar markup and `#skyMapContainer` section
- Create `frontend/js/components/tab-nav.js` — tab switching logic and event dispatch
- Create `frontend/css/components/tab-nav.css` — tab bar styling
- Modify `frontend/css/main.css` — import `components/tab-nav.css`
- Modify `frontend/js/main.js` — initialise `TabNav`, wire tab switching to show/hide content panels

---

#### Phase A2: SVG Polar Projection Grid — ⬜

**Depends on:** Phase A1

**Intended Outcome**

The sky map tab shows a circular SVG chart where the zenith is at the centre and the horizon is the outer edge. Concentric altitude rings at 0°, 30°, and 60° are drawn and labelled. Swedish cardinal direction labels (N, O, S, V) and intermediate tick marks (NO, SO, SV, NV) are placed around the horizon ring. The chart background matches the app's deep-space theme and scales responsively from 375 px to 1200 px, always maintaining a square aspect ratio. No astronomical data is plotted yet — this phase establishes the reusable coordinate system.

**Definition of Done**
- [ ] An SVG element renders inside `#skyMapContainer` when the sky map tab is active
- [ ] The SVG uses a `viewBox` attribute and scales responsively with no fixed pixel width or height
- [ ] Three concentric circles are drawn at altitudes 0° (horizon), 30°, and 60°
- [ ] Each altitude ring is labelled with its degree value using `--color-text-muted`
- [ ] Cardinal labels N, O, S, V are placed at the four cardinal positions around the horizon
- [ ] Intermediate tick marks (NO, SO, SV, NV) are drawn at 45° intervals
- [ ] North (azimuth 0°) is at the top of the chart; East (90°) is to the right
- [ ] `altAzToXY(altitude_deg, azimuth_deg)` is exported as a pure function testable in isolation
- [ ] Grid lines use `--border-color`; labels use `--color-text-secondary`; background uses `--color-bg-surface`
- [ ] The SVG maintains a 1:1 aspect ratio on both 375 px and 1200 px viewports
- [ ] No JavaScript console errors when switching to the sky map tab

**Key files**
- Create `frontend/js/components/sky-map.js` — `SkyMap` class with `altAzToXY()` projection and grid rendering
- Create `frontend/css/components/sky-map.css` — container sizing, aspect-ratio constraint, SVG defaults
- Modify `frontend/css/main.css` — import `components/sky-map.css`
- Modify `frontend/js/main.js` — instantiate `SkyMap` and render it when the sky map tab is activated

---

#### Phase A3: Planet, Sun, and Moon Plotting — ⬜

**Depends on:** Phase A2

**Intended Outcome**

All five naked-eye planets, the Sun, and the Moon are plotted on the sky map at their correct altitude/azimuth positions using data already returned by the `/api/v1/planets/visible` endpoint. Planet dot size scales with apparent brightness; each planet uses its per-planet colour token. Bodies below the horizon are rendered at reduced opacity outside the horizon ring. Hovering or tapping any body shows a tooltip (via the existing `tooltip.js`) with the body's Swedish name, altitude, azimuth direction, and magnitude. The sky map re-renders automatically whenever new API data arrives.

**Definition of Done**
- [ ] All five planets appear on the sky map at positions matching their `altitude_deg` and `azimuth_deg` from the API response
- [ ] Planet dot radius varies with apparent magnitude: Venus (mag ≈ −4) is visibly larger than Saturn (mag ≈ +1)
- [ ] Each planet dot uses its per-planet colour from `tokens.css` (e.g. Mars uses `--color-planet-mars`)
- [ ] Planets with `altitude_deg < 0` are rendered at 0.3 opacity outside the horizon ring
- [ ] Planet labels (Swedish name) are rendered next to each dot
- [ ] The Sun is plotted as a golden circle using `--color-sun-penalty` at its correct altitude/azimuth position
- [ ] The Moon is plotted using `moon.elevation_deg` and `moon.azimuth_deg` from the API response
- [ ] Hovering a planet dot shows a tooltip with: Swedish name, altitude (e.g. "Höjd: 25.3°"), direction (e.g. "Riktning: VSV"), and magnitude
- [ ] Sun tooltip shows "Solen" and its elevation; Moon tooltip shows "Månen" and its illumination percentage
- [ ] The tooltip reuses the existing `tooltip.js` component
- [ ] The sky map re-renders when `loadData()` completes without requiring a tab switch
- [ ] No JavaScript console errors when the map contains planets both above and below the horizon
- [ ] Backend: `SunInfo` model includes `azimuth_deg` field populated from `calculate_sun_penalty()` or equivalent

**Key files**
- Modify `frontend/js/components/sky-map.js` — add `plotBodies(planets, sun, moon)` method
- Modify `frontend/js/main.js` — pass API response data to `SkyMap.plotBodies()` after each render
- Modify `backend/app/models/planet.py` — add `azimuth_deg: float` field to `SunInfo`
- Modify `backend/app/utils/sun.py` — return sun azimuth alongside elevation
- Modify `backend/app/api/routes/planets.py` — populate `SunInfo.azimuth_deg` in the response builder

---

#### Phase A4: Constellation Lines — ⬜

**Depends on:** Phase A3

**Intended Outcome**

The sky map displays constellation stick-figure lines for all constellations with stars above the horizon. Constellation data is embedded as a static JSON file (< 150 KB, sourced from Stellarium under GPL-2.0-or-later) — no external CDN or runtime download. A client-side JavaScript module converts star RA/Dec coordinates to alt/az using sidereal time, keeping all astronomical projection math consistent without adding a new backend endpoint. Lines are drawn in a subtle muted colour behind planet dots; each visible constellation is labelled with its IAU three-letter abbreviation. The map degrades gracefully if the data file fails to load.

**Definition of Done**
- [ ] `frontend/data/constellations.json` exists, is < 150 KB uncompressed, and contains at least the 30 most prominent constellations visible from Sweden's latitude range (55°–70° N)
- [ ] `THIRD_PARTY_LICENSES.md` (or equivalent) documents the Stellarium data source, its GPL-2.0-or-later licence, and the URL of the original file
- [ ] `frontend/js/astro-projection.js` exports `raDecToAltAz(ra_deg, dec_deg, lat, lon, utc_timestamp)` as a pure function
- [ ] Constellation lines render as SVG elements with stroke colour `--color-text-muted` at 0.25 opacity
- [ ] Constellation lines are drawn in an SVG `<g>` group layered behind the planet/sun/moon group
- [ ] Each visible constellation has its IAU three-letter label rendered near its geometric centre using `--font-size-xs` and `--color-text-muted`
- [ ] Constellations entirely below the horizon (all stars at altitude < 0°) are not rendered
- [ ] The constellation layer updates when data refreshes (location change or auto-refresh)
- [ ] If `constellations.json` fails to load, the sky map renders planets and grid without constellation lines and logs a warning — no JavaScript errors thrown
- [ ] `raDecToAltAz()` is unit-tested for at least two known star positions (e.g. Polaris at lat 59° N should appear near azimuth 0°, altitude ≈ 59°)

**Key files**
- Create `frontend/data/constellations.json` — embedded Stellarium constellation line data (RA/Dec pairs + IAU abbreviation per constellation)
- Create `frontend/js/astro-projection.js` — pure `raDecToAltAz()` function with sidereal time calculation
- Modify `frontend/js/components/sky-map.js` — add `plotConstellations(data, lat, lon, timestamp)` method; load JSON; create SVG line groups
- Modify `frontend/js/main.js` — load constellation data once on startup; pass to `SkyMap` on each render
- Create `THIRD_PARTY_LICENSES.md` (project root) — document Stellarium GPL-2.0-or-later licence

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
