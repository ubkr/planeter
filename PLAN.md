# Planetvis (Planeter) — Implementation Plan

## Overview

A web application that calculates which planets are visible from a specific location (primarily Sweden) at a given time. Backend: Python FastAPI with the `ephem` library for astronomical calculations. Frontend: Vanilla HTML/CSS/JavaScript with Leaflet map picker.

## MVP Scope

The MVP answers one question: **"Which planets can I see from my location right now, and where do I look?"**

### MVP Features

1. Calculate positions (altitude, azimuth) of all naked-eye planets (Mercury, Venus, Mars, Jupiter, Saturn) for a given location and time
2. Determine rise/set times for each planet
3. Assess actual visibility considering: altitude above horizon, sun position (daylight penalty), cloud cover, planet apparent magnitude
4. Display results in a dark-themed UI showing each planet's status, direction, and visibility score
5. Location picker with map
6. Weather/cloud cover integration

## Phase-by-Phase Execution

## Phase 1: Project Setup — ✅

**Depends on**: none
**Parallelisable with**: none

### Tasks
- ✅ Already in place — directory structure created: `backend/app/`, `backend/app/api/routes/`, `backend/app/models/`, `backend/app/services/planets/`, `backend/app/utils/`, `frontend/js/components/`, `frontend/css/components/`
- ✅ Already in place — all `__init__.py` files created in every Python package directory
- ✅ Already in place — `backend/requirements.txt` created; `apscheduler` and `aiofiles` excluded
- ✅ Already in place — `backend/app/config.py` adapted: title "Planeter API", description "Planet visibility calculations for Sweden", removed aurora-specific fields, added `openmeteo_base_url`
- ✅ Already in place — `backend/app/main.py` adapted: aurora/prediction/weather routers removed, health and geocode registered, TODO stub for planets router
- ✅ Already in place — `start-backend.sh` copied and paths updated to planeter
- ✅ Already in place — `start-frontend.sh` created for the frontend directory
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
- ✅ Already in place — `backend/app/utils/logger.py`
- ✅ Already in place — `backend/app/utils/sun.py`; used for daylight penalty
- ✅ Already in place — `backend/app/utils/moon.py`; extended with `get_moon_angular_separation()` for planet proximity scoring
- ✅ Already in place — `backend/app/services/cache_service.py`
- ✅ Already in place — `backend/app/services/weather/base.py`
- ✅ Already in place — `backend/app/services/weather/metno_client.py`
- ✅ Already in place — `backend/app/services/weather/openmeteo_client.py`
- ✅ Already in place — `backend/app/models/weather.py`

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
- ✅ Already in place — `backend/app/api/routes/health.py`; service name changed to `planeter-api`
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
- ✅ Already in place — `frontend/js/components/map-selector.js`
- ✅ Already in place — `frontend/js/components/settings-modal.js` adapted: title changed to "Inställningar", button text in Swedish, aurora-specific fields removed
- ✅ Already in place — `frontend/js/components/tooltip.js`
- ✅ Already in place — `frontend/css/tokens.css` adapted: primary accent changed to warm gold `#f5c842`, secondary to deep blue `#3b82f6`, aurora-specific metric color renamed
- ✅ Already in place — `frontend/css/base.css`
- ✅ Already in place — `frontend/css/layout.css`
- ✅ Already in place — `frontend/css/components/modal.css`
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

- **Remove dead grid selectors from `frontend/css/layout.css`**. Delete the `.score-section`, `.data-grid-section`, and `.chart-section` rules. These selectors have no corresponding elements in planeter's `index.html`. After removing those three rules, audit every remaining rule in the `@media (min-width: 900px)` block by cross-referencing each selector against `frontend/index.html`. Remove any additional rules whose selectors have no corresponding element in the planeter DOM. Leave the `@media` block intact if other rules inside it are still needed; remove the entire block if it becomes empty.
- **Fix `formatLocation()` hemisphere labels** in `frontend/js/utils.js`. Currently the fallback format always appends "N" and "O" regardless of the sign of lat/lon. Change it to append "N"/"S" based on the sign of latitude and "Ö"/"V" (Öst/Väst in Swedish) based on the sign of longitude. Use the absolute value of the coordinate for display so that negative signs do not appear alongside the hemisphere letter.

### Intended Outcome
`frontend/css/layout.css` contains only rules that apply to elements present in planeter's DOM. `formatLocation()` in `frontend/js/utils.js` produces correct hemisphere labels for any coordinate on Earth, not just the positive-lat/positive-lon case that covers Sweden. Two issues are resolved: layout CSS targeting selectors that do not exist in planeter's DOM (which adds noise to the stylesheet and would confuse anyone reading the grid layout), and a coordinate formatter that hardcodes Northern and Eastern hemisphere labels (a bug invisible for Sweden but wrong for any location outside the positive-lat/positive-lon quadrant). This phase is cleanup only: no new features, no backend changes.

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

## Phase 12: Magnitude-Aware Twilight Visibility — ✅

**Depends on:** Phase 9
**Parallelisable with:** Phase B1, Phase B2

### Tasks
- Research and implement a continuous twilight limiting-magnitude model in `backend/app/utils/sun.py` — replace the current step-function penalty (50/40/20/8/0 pts at discrete twilight band boundaries) with a continuous function that returns both a penalty value and a twilight limiting magnitude as a function of sun altitude; reference Schaefer (1993) "Astronomy and the Limits of Vision" (Vistas in Astronomy, Vol. 36, pp. 311-361) and Stellarium's SkyBright implementation for the empirical relationship between sun depression angle and sky brightness
- Modify `backend/app/services/scoring.py` `score_planet()` — make the sun penalty magnitude-aware so that bright planets (low apparent magnitude) receive a smaller penalty during twilight than faint planets; Venus at mag -3.8 should receive near-zero sun penalty during nautical twilight while Saturn at mag +0.5 should still receive a substantial penalty
- Modify `backend/app/services/scoring.py` `apply_scores()` — replace the hard `sun_altitude < -12` gate on `is_visible` with a magnitude-dependent threshold: a planet is potentially visible when its apparent magnitude is brighter than the limiting magnitude for the current sun altitude
- Add unit tests in `backend/tests/` — test the new twilight limiting-magnitude function against known empirical data points (Venus visible at sun altitude -4°, Jupiter at -7°, first-magnitude stars at -6°, sixth-magnitude stars at -18°); test that `apply_scores()` marks Venus and Jupiter visible when sun altitude is -8°
- Update `ARCHITECTURE.md` — revise the "Visibility Scoring Algorithm" table and the `is_visible` description to document the magnitude-aware twilight model and cite the Schaefer reference

> **Note:** `ARCHITECTURE.md` is at project root, not under `backend/` or `frontend/`. Documentation file — path exception is intentional.

### Intended Outcome
The visibility scorer accounts for planet brightness when evaluating twilight conditions. Bright planets like Venus and Jupiter are correctly reported as visible during early twilight (sun at −5 to −8° below horizon), while faint planets still require deeper darkness. The sun penalty is a continuous function of sun altitude rather than a coarse step function, and the `is_visible` gate uses a magnitude-dependent threshold derived from the empirical relationship between sky brightness and sun depression angle documented in Schaefer (1993). The net effect is that the app no longer produces false negatives for the two brightest planets during the most common evening observation window.

### Definition of Done
- [ ] `calculate_sun_penalty()` in `backend/app/utils/sun.py` returns a `limiting_magnitude` float field alongside existing fields
- [ ] Limiting magnitude at sun altitude −6° (end of civil twilight) ≈ magnitude −1 to 0 (first-magnitude stars become visible empirically)
- [ ] Limiting magnitude at sun altitude −12° (end of nautical twilight) ≈ magnitude +3 to +4
- [ ] Limiting magnitude at sun altitude −18° (end of astronomical twilight) ≈ magnitude +5.5 to +6.5
- [ ] `apply_scores()` sets `is_visible = True` for Venus (mag −3.8) at sun altitude −8° when planet is above the horizon with clear skies
- [ ] `apply_scores()` sets `is_visible = True` for Jupiter (mag −2.2) at sun altitude −8° when planet is above the horizon with clear skies
- [ ] `apply_scores()` sets `is_visible = False` for Saturn (mag +0.5) at sun altitude −8°, sky still too bright
- [ ] `score_planet()` produces a higher score for Venus than for Saturn at identical sun altitude −8°, all other factors equal
- [ ] Sun penalty in `score_planet()` is a continuous function — no abrupt score jumps when sun altitude crosses −6°, −12°, or −18° boundaries
- [ ] All existing unit tests in `backend/tests/` continue to pass
- [ ] `ARCHITECTURE.md` scoring table documents the magnitude-aware twilight model and references Schaefer (1993)

---

## Phase 13: Solsystemsvy — Statisk Ögonblicksbild — ✅

**Status:** Complete
**Depends on:** Phase 6, Phase 2
**Parallelisable with:** Phase B series, Phase E series

### Tasks
- Build `backend/app/services/planets/heliocentric.py` — compute heliocentric (Sun-relative) XYZ positions in astronomical units for all five naked-eye planets using ephem orbital elements; calculate semi-major axes for orbit scaling
- Modify `backend/app/models/planet.py` — add optional `heliocentric_x_au`, `heliocentric_y_au`, `heliocentric_z_au` float fields to `PlanetPosition` model
- Modify `backend/app/api/routes/planets.py` — call heliocentric calculator in `/visible` endpoint; populate the three new fields on each `PlanetPosition` before returning (additive change, no breaking modifications)
- Create `frontend/js/components/solar-system-view.js` — SVG renderer for top-down solar system diagram: Sun at centre, planet orbits as concentric circles scaled by semi-major axis, planet positions as coloured dots at current heliocentric coordinates, Swedish planet labels, hover/tap triggers tooltip via existing `tooltip.js`
- Create `frontend/css/components/solar-system-view.css` — container sizing, SVG aspect ratio, planet dot colours matching existing per-planet tokens, orbit stroke styling
- Modify `frontend/index.html` — add "Solsystemet" tab button as the fourth tab (after "Kommande") and `#panelSolarSystem` container with `#solarSystemContainer`
- Modify `frontend/js/components/tab-nav.js` — extend tab loop to support four tabs; add "Solsystemet" to tab array
- Modify `frontend/js/main.js` — instantiate `SolarSystemView`; pass heliocentric data from API response when "Solsystemet" tab is active; wire location change to trigger re-render (positions change slightly with observer location due to parallax)
- Modify `frontend/css/main.css` — import `components/solar-system-view.css`

### Intended Outcome
The app gains a fourth tab, "Solsystemet", showing a static top-down view of the inner solar system. The Sun sits at the centre; the five naked-eye planets are plotted at their current heliocentric positions as coloured dots on correctly scaled orbital rings. The view is geocentric-independent (all users see the same planetary configuration at a given moment) but updates when new API data arrives. Hovering or tapping any planet dot shows a Swedish tooltip with the planet's name and its current distance from the Sun in astronomical units. Orbits are drawn to scale relative to each other (Mercury's orbit is visibly smaller than Saturn's), but planet dots are enlarged for visibility. This first version is a static snapshot — no animation or time-travel controls.

### Definition of Done
- [ ] `PlanetPosition` includes three new optional float fields: `heliocentric_x_au`, `heliocentric_y_au`, `heliocentric_z_au`; Venus on 2026-03-29 has non-null values for all three
- [ ] `GET /api/v1/planets/visible?lat=55.7&lon=13.4` returns heliocentric coordinates for all five planets; each planet's distance from origin (sqrt(x² + y² + z²)) is within 0.1 AU of its known semi-major axis
- [ ] A "Solsystemet" tab button renders as the fourth tab in the tab bar, after "Kommande"
- [ ] Clicking "Solsystemet" hides the other three panels and shows an SVG diagram with the Sun at the centre and five planetary orbit circles
- [ ] All five planets (Merkurius, Venus, Mars, Jupiter, Saturnus) render as coloured dots on or near their respective orbit rings at positions matching their heliocentric coordinates
- [ ] Hovering a planet dot on desktop or tapping it on mobile shows a tooltip with the Swedish planet name and its distance from the Sun formatted as "X.XX AU"
- [ ] Mercury's orbit circle is visibly smaller than Earth's implied orbit (1 AU reference), and Saturn's orbit is the outermost ring
- [ ] Planet dot colours match the existing per-planet CSS tokens: Mercury grey, Venus yellow, Mars red, Jupiter amber, Saturn gold
- [ ] The Sun is rendered as a larger golden circle at the origin with the label "Solen"
- [ ] Switching to a different location (via the map picker) triggers a re-render of planet positions (parallax effect, though minimal at planetary distances)
- [ ] No JavaScript console errors when switching to the "Solsystemet" tab before API data has loaded (graceful empty state or skeleton)
- [ ] The SVG maintains correct aspect ratio and is centred in its container on both 375 px and 1200 px viewports

---

## Confirmed Decisions

| Question | Decision |
|---|---|
| Planet scope | **Naked-eye only**: Mercury, Venus, Mars, Jupiter, Saturn |
| Time selection | **Right now + tonight**: current positions, plus tonight's visibility windows (sunset → sunrise) |
| UI language | **Swedish**: all labels, planet names, and UI text in Swedish |
| Cloud cover | **Affects visibility score**: overcast sky reduces or zeroes a planet's score |
| Default location | Södra Sandby (55.7°N, 13.4°E) |
| Uranus/Neptune | Not in scope for MVP; can be added in a future phase |

## Future Roadmap

### Phase A: Sky Map

#### Phase A1: Sky Map Tab Shell and Navigation — ✅

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

#### Phase A2: SVG Polar Projection Grid — ✅

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

#### Phase A3: Planet, Sun, and Moon Plotting — ✅

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

#### Phase A4: Constellation Lines — ✅

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

#### Phase B1: Best Viewing Times — ✅

**Depends on:** Phase 5 (API Layer), Phase 6 (Frontend)
**Parallelisable with:** Phase B2, Phase B3

**Intended Outcome**

Each planet card gains a "Bästa observationstid" section showing the optimal viewing window during tonight's darkness. The backend computes, for each planet, the time interval when the planet is above 10° altitude while the sun is below −12° (nautical twilight or darker), and identifies the moment of peak altitude within that window. The `/visible` and `/tonight` endpoints both include this data so the UI always shows it. Planets that never enter the dark window display "Ej synlig ikväll" instead of a time range.

**Definition of Done**
- [x] `PlanetPosition` model includes `best_time: Optional[str]` (UTC ISO 8601 timestamp of the planet's **peak altitude** within the dark window), `dark_rise_time: Optional[str]`, and `dark_set_time: Optional[str]`
- [x] The `/visible` endpoint response includes non-null `best_time` for a planet that is above 10° altitude during tonight's dark window
- [x] A planet that sets before nautical twilight begins has `best_time: null`, `dark_rise_time: null`, `dark_set_time: null`
- [x] During midnight sun conditions (no dark window), all planets have null best-time fields
- [x] The planet card shows "Bästa tid: HH:MM–HH:MM" (in Europe/Stockholm time) beneath the existing rise/transit/set row when `dark_rise_time` and `dark_set_time` are non-null
- [x] The peak time within the window is visually emphasised (bold or accent colour)
- [x] When all three best-time fields are null, the card shows "Ej synlig ikväll" in `--color-text-muted`
- [x] The `/tonight` endpoint also populates the best-time fields using its existing night-window sampling logic
- [x] No regressions in existing planet card layout on 375 px and 1200 px viewports
- [x] No new API endpoints are introduced; the fields are added to the existing response schema
- [x] `dark_rise_time`, `dark_set_time`, and `best_time` are stored as UTC ISO 8601 strings, consistent with all other time fields; the existing `formatTime()` helper in `planet-cards.js` handles conversion to Europe/Stockholm for display — no backend timezone conversion is added

**Key files**
- Modify `backend/app/models/planet.py` — add `best_time`, `dark_rise_time`, `dark_set_time` optional string fields to `PlanetPosition`
- Modify `backend/app/api/routes/planets.py` — compute per-planet dark window using existing `_compute_tonight_window()` and `_sample_times()`; find peak altitude time within the window; populate the three new fields on each `PlanetPosition` before returning. For the `/visible` endpoint specifically (which currently computes only an instantaneous snapshot), B1 adds a single call to `_compute_tonight_window()` once per request (not per planet), then for each planet samples its altitude at 15-minute intervals within that window to find the dark rise/set/peak — estimated latency impact is approximately 7 samples × 5 planets ≈ 35 additional `ephem` calls, well under 50 ms
- Modify `frontend/js/components/planet-cards.js` — add "Bästa observationstid" row to `buildCard()` showing the dark window and peak time, or "Ej synlig ikväll" when fields are null
- Modify `frontend/css/components/planet-cards.css` — style the new best-time row, including accent treatment for the peak time

---

#### Phase B2: Observation Descriptions ("What to Look For") — ✅

**Depends on:** Phase 6 (Frontend)
**Parallelisable with:** Phase B1, Phase B3

**Intended Outcome**

Each planet card gains a collapsible "Vad ska man leta efter?" section containing a short Swedish-language description of the planet's visual appearance: characteristic colour, typical brightness compared to nearby stars, and how to distinguish it from stars (steady light vs. twinkling). The descriptions are static factual content stored in a frontend data file — no backend changes are needed. The section is collapsed by default to keep cards compact and can be expanded by clicking a toggle.

**Definition of Done**
- [x] `frontend/js/data/planet-descriptions.js` exists and exports an object keyed by English planet name (Mercury, Venus, Mars, Jupiter, Saturn)
- [x] Each entry contains at minimum: `color_sv` (string, e.g. "Gulvit"), `appearance_sv` (1–2 sentence description), `identification_tip_sv` (1–2 sentences on how to spot the planet)
- [x] Each planet card renders a "Vad ska man leta efter?" toggle below the visibility pill
- [x] Clicking the toggle expands a section showing the planet's colour, appearance, and identification tip
- [x] Clicking again collapses the section
- [x] The toggle uses a chevron icon (▸ collapsed, ▾ expanded) and the expanded state is visually distinct
- [x] The section is collapsed by default on page load
- [x] Descriptions use correct Swedish astronomical terminology (e.g. "magnitud", "stjärnbild", "fast sken")
- [x] Descriptions are factually accurate for the current epoch (2020s)
- [x] Cards for planets below the horizon still show the description toggle (the information is useful regardless of current visibility)
- [x] No backend changes are required
- [x] No JavaScript console errors when toggling descriptions rapidly

**Key files**
- Create `frontend/js/data/planet-descriptions.js` — static object with Swedish descriptions for each planet
- Modify `frontend/js/components/planet-cards.js` — import descriptions; add collapsible section to `buildCard()`; wire toggle click handler
- Modify `frontend/css/components/planet-cards.css` — style the collapsible description section, toggle button, and transition animation

---

#### Phase B3: Equipment Guidance — ✅

**Depends on:** Phase 6 (Frontend)
**Parallelisable with:** Phase B1, Phase B2

**Intended Outcome**

Each visible planet card displays a small equipment badge indicating whether the planet is best observed with the naked eye, binoculars, or a small telescope under current conditions. The recommendation is computed entirely in the frontend from the planet's current magnitude and altitude — no backend changes. Mercury at faint magnitudes or any planet at very low altitude (5°–10°) gets a "Kikare rekommenderas" badge. All other visible planets get "Blotta ögat". Planets below the horizon or with score 0 do not show an equipment badge.

**Definition of Done**
- [x] `frontend/js/utils.js` exports a `getEquipmentRecommendation(planet)` function returning `null`, `"naked_eye"`, `"binoculars"`, or `"telescope"`
- [x] The function returns `null` when `planet.is_above_horizon` is false or `planet.visibility_score` is 0
- [x] The function returns `"binoculars"` when `planet.altitude_deg` is between 5 and 10 (atmospheric extinction zone)
- [x] The function returns `"binoculars"` when `planet.name === "Mercury"` and `planet.magnitude > 1.5`
- [x] The function returns `"naked_eye"` for all other visible planets
- [x] Each planet card renders a badge with the Swedish label: "Blotta ögat" (naked_eye), "Kikare rekommenderas" (binoculars), or "Teleskop" (telescope)
- [x] The badge uses an appropriate icon or emoji (👁 for naked eye, 🔭 for binoculars/telescope) or a simple text pill
- [x] The badge is not rendered for planets where the function returns `null`
- [x] Badge styling uses `--color-text-secondary` background with `--color-text-primary` text, consistent with existing card design tokens
- [x] No backend changes are required
- [x] No JavaScript console errors on page load or data refresh

**Key files**
- Modify `frontend/js/utils.js` — add `getEquipmentRecommendation(planet)` function
- Modify `frontend/js/components/planet-cards.js` — import and call `getEquipmentRecommendation()`; render equipment badge in `buildCard()` when result is non-null
- Modify `frontend/css/components/planet-cards.css` — style the equipment badge pill

---

#### Phase B4: Astronomical Event Alerts — ✅

**Depends on:** Phase 5 (API Layer) and Phase 6 (Frontend) for backend event detection and the frontend alert banner; Phase A3 (Sky Map plotting) additionally required for sky-map conjunction line and opposition glow rendering only — backend and banner work can proceed without A3
**Parallelisable with:** Phase B2, Phase B3

**Intended Outcome**

The app detects and displays six types of notable astronomical events within a 48-hour window and renders them as real-time alert banners on the planet cards tab. A new `events` array in the API response carries all active or imminent events. Each banner includes a Swedish description and the involved bodies. On the sky map, conjunction and occultation bodies are connected with a dashed line; opposition planets receive a subtle glow.

The six event types detected:

| event_type | Condition | Swedish description example |
|---|---|---|
| `conjunction` | Any two planets/Moon within 5° | "Venus och Jupiter i konjunktion (2,3° separation)" |
| `opposition` | Mars/Jupiter/Saturn elongation > 170° | "Mars i opposition – bästa tillfället att observera planeten" |
| `mercury_elongation` | Mercury elongation > 15° AND within 1° of local maximum | "Bästa tillfället att se Merkurius – titta lågt i väster strax efter solnedgång" |
| `alignment` | 3+ naked-eye planets within 30° ecliptic arc | "4 planeter syns på rad i kvällshimlen!" |
| `venus_brilliancy` | Venus magnitude < −4.5 | "Venus är nu på sin ljusaste – den syns till och med i dagsljus!" |
| `moon_occultation` | Moon within 0.5° of a planet (6-hour sampling) | "Månen täcker Mars – ett sällsynt skådespel" |

Events spanning multiple sample days are deduplicated into one, keeping the most extreme value.

**Definition of Done**
- [x] `backend/app/models/planet.py` includes a new `AstronomicalEvent` Pydantic model with fields: `event_type`, `bodies`, `date` (ISO 8601), `separation_deg`, `elongation_deg`, `description_sv`
- [x] `PlanetsResponse` includes `events: List[AstronomicalEvent]` (default empty list)
- [x] `backend/app/services/planets/events.py` exports `detect_events(lat, lon, start_dt, end_dt)` with six detector sub-functions
- [x] `detect_events` scans a 48-hour window using `ephem.separation()`, `.elong`, and ecliptic coordinates
- [x] The `/visible` and `/tonight` endpoints call `detect_events()` inside a try/except fallback and include results in the response
- [x] `frontend/js/components/event-alerts.js` (`EventAlerts` class) renders a banner for each event; banner is hidden when the array is empty
- [x] Active events use `--color-status-excellent` styling; upcoming events use `--color-status-fair`
- [x] `frontend/js/components/sky-map.js` `plotBodies()` accepts an `events` param; draws dashed lines for conjunctions/occultations and adds `.sky-map-body--opposition` glow class for oppositions
- [x] No regressions in existing endpoint response schemas — `events` is an additive field with a default empty list

**Key files**
- Create `backend/app/services/planets/events.py` — `detect_events()` with six detector sub-functions
- Modify `backend/app/models/planet.py` — add `AstronomicalEvent` and `EventsResponse` models; add `events` field to `PlanetsResponse`
- Modify `backend/app/api/routes/planets.py` — call `detect_events()` in `/visible` and `/tonight` handlers with try/except fallback
- Create `frontend/js/components/event-alerts.js` — `EventAlerts` class rendering alert banners
- Create `frontend/css/components/event-alerts.css` — banner styles
- Modify `frontend/css/main.css` — import `components/event-alerts.css`
- Modify `frontend/index.html` — add `<div id="eventAlerts">` between sky summary and planet cards
- Modify `frontend/js/main.js` — instantiate `EventAlerts`; call `eventAlerts.render(data.events)` after each data fetch
- Modify `frontend/js/components/sky-map.js` — conjunction/occultation dashed lines and opposition glow in `plotBodies()`
- Modify `frontend/css/components/sky-map.css` — add `.sky-map-conjunction-line` and `.sky-map-body--opposition` styles

---

#### Phase B5: Kommande Events Timeline — ✅

**Depends on:** Phase B4 (event detection in `events.py`), Phase A1 (tab navigation shell)
**Parallelisable with:** Phase E1

**Intended Outcome**

A third "Kommande" tab shows all six event types across the next 60 days as a scrollable timeline. Events are grouped by Swedish month name. Each row displays the weekday and date, an event icon, a Swedish description, and a days-away badge ("idag" / "imorgon" / "om X dagar"). The tab lazy-loads its data on first switch and re-fetches whenever the location changes. An empty state message is shown when no notable events are found in the window.

**Definition of Done**
- [x] `backend/app/api/routes/events.py` provides a `GET /api/v1/events?lat=&lon=` endpoint with a 1-hour cache that calls `detect_events()` over a 60-day window and returns `EventsResponse`
- [x] `backend/app/main.py` registers `events.router`
- [x] `frontend/js/components/events-timeline.js` (`EventsTimeline` class) renders month-grouped rows with days-away badges, skeleton loading state, and an empty state message
- [x] `frontend/css/components/events-timeline.css` styles the timeline, month headings, and days-away badges
- [x] `frontend/js/api.js` exports `fetchEvents(lat, lon)` calling `/api/v1/events`
- [x] `frontend/index.html` includes a "Kommande" tab button (`#tabEvents`) and a `#panelEvents` tab panel containing `#eventsTimelineContainer`
- [x] `frontend/js/components/tab-nav.js` is refactored from hardcoded 2-tab logic to a generic 3-tab loop; dispatches a `tabChanged` custom event for all tabs
- [x] `frontend/js/main.js` instantiates `EventsTimeline`, adds `loadEvents()`, and listens for `tabChanged`; events are lazy-loaded on first switch and the `eventsLoaded` flag resets on location change
- [x] Empty state renders "Inga speciella händelser de närmaste 60 dagarna 🌙" when the response is empty
- [x] No regressions in existing planet cards or sky map tabs

**Key files**
- Create `backend/app/api/routes/events.py` — `GET /api/v1/events` endpoint with 60-day window and 1-hour cache
- Modify `backend/app/main.py` — register `events.router`
- Create `frontend/js/components/events-timeline.js` — `EventsTimeline` class with month grouping, skeleton, and empty state
- Create `frontend/css/components/events-timeline.css` — timeline and days-away badge styles
- Modify `frontend/js/api.js` — add `fetchEvents(lat, lon)`
- Modify `frontend/index.html` — add `#tabEvents` button and `#panelEvents` / `#eventsTimelineContainer`
- Modify `frontend/css/main.css` — import `components/events-timeline.css`
- Modify `frontend/js/components/tab-nav.js` — refactor to generic 3-tab loop with `tabChanged` event dispatch
- Modify `frontend/js/main.js` — instantiate `EventsTimeline`; add `loadEvents()`; wire `tabChanged` listener with lazy-load and location-reset logic

---

#### Phase B6: Event Detail — Observation Guidance — ✅

**Depends on:** Phase B4, Phase B5
**Parallelisable with:** Phase B1, Phase B2, Phase E7

**Intended Outcome**

Clicking or tapping an event row (in either the Kommande timeline or the alert cards) reveals detailed observation guidance for that event. The detail view shows the best viewing time window (start and end as `HH:MM`), the sky position at event peak (altitude in degrees, compass direction in Swedish such as "sydväst"), and a short Swedish prose tip explaining where and when to look. The exact interaction pattern — inline expand, modal, bottom sheet, or other — is left to the designer; the backend supplies all necessary data and the frontend components expose a stable hook point for whichever pattern is chosen. Events whose peak occurs during daytime or below the horizon receive a Swedish note explaining reduced visibility. All new UI strings are in Swedish.

**Definition of Done**
- [x] `AstronomicalEvent` model includes optional observation guidance fields: `best_time_start`, `best_time_end`, `altitude_deg`, `azimuth_deg`, `compass_direction_sv`, and `observation_tip_sv`
- [x] The event detection pipeline computes sky position and optimal viewing window for each event type, populating the new fields on every returned event
- [x] Events whose peak is below the horizon or during daylight carry a Swedish explanatory note in `observation_tip_sv`
- [x] Clicking/tapping an event in the Kommande timeline reveals the detail content with no full-page navigation
- [x] Clicking/tapping an event alert card reveals the same detail content
- [x] Detail content is accessible via keyboard (Enter/Space to toggle) and includes appropriate ARIA attributes
- [x] No regressions in existing event rendering, planet cards, or sky map tabs

**Key files**
- Modify `backend/app/models/planet.py` — add optional fields to `AstronomicalEvent`: `best_time_start`, `best_time_end` (ISO time strings), `altitude_deg`, `azimuth_deg` (floats), `compass_direction_sv` (str), `observation_tip_sv` (str)
- Modify `backend/app/services/planets/events.py` — for each detected event, compute the observer-local optimal viewing window and sky coordinates at peak; generate a Swedish observation tip; handle below-horizon and daytime edge cases
- Modify `frontend/js/components/events-timeline.js` — add click/tap handler on event rows; render a detail section showing time window, compass direction, and observation tip (exact interaction pattern determined by designer)
- Modify `frontend/js/components/event-alerts.js` — add click/tap handler on alert cards; render the same detail content
- Modify `frontend/css/components/events-timeline.css` — style the detail/expanded state for timeline rows
- Modify `frontend/css/components/event-alerts.css` — style the detail/expanded state for alert cards

---

#### Phase B7: Platsanpassad Händelsefiltrering — ✅

**Depends on:** Phase B6
**Parallelisable with:** Phase E8

**Intended Outcome**
The `/api/v1/events` endpoint filters out astronomical events that are geometrically unobservable from the queried location before returning the response. Events where the primary body has a negative `altitude_deg` at event peak (i.e. below the horizon for that observer) are excluded from `EventsResponse.events`. Events where `altitude_deg` is `null` (not computed for that event type) are retained. The frontend already handles an empty event list via the "Inga speciella händelser de närmaste 60 dagarna 🌙" empty state, so no frontend changes are required.

**Definition of Done**
- ✅ `GET /api/v1/events?lat=55.7&lon=13.4` returns no event objects where `altitude_deg` is a negative number; verified by inspecting the JSON response body.
- ✅ Events where `altitude_deg` is `null` in the JSON response are still present in the returned `events` array (conservative pass-through for event types where altitude is not computed).
- ✅ Switching to a location in the southern hemisphere (e.g. `lat=-33.9&lon=18.4`) produces a different (non-identical) events list than `lat=55.7&lon=13.4` for the same date, confirming the filter is location-dependent.
- ✅ When all detected events are filtered out, `GET /api/v1/events` returns `{"events": [], ...}` with HTTP 200, and the frontend renders the "Inga speciella händelser de närmaste 60 dagarna 🌙" empty-state message.
- ✅ The 1-hour cache in `routes/events.py` stores the already-filtered list (no behaviour change to cache key or TTL required).

**Key files**
- Modify `backend/app/api/routes/events.py` — after calling `detect_events()`, filter the resulting list to exclude events where `altitude_deg is not None and altitude_deg < 0`, then pass the filtered list to `EventsResponse`

---

#### Phase B8: Nästa Synlighetstid för Dolda Planeter — ✅

**Depends on:** Phase B1, Phase 6
**Parallelisable with:** Phase E series

**Intended Outcome**

Planets that are currently not visible (either below the horizon or hidden by daylight/cloud cover) display a "next visible time" in their compact card tooltip, showing when the planet will next be observable above 10° altitude during nautical darkness within the next 24 hours. The backend computes the earliest qualifying moment by scanning the next 24-hour window at 15-minute intervals, using the same dark-window and altitude-threshold logic as Phase B1's best-viewing-time calculator. Planets that remain unobservable throughout the entire 24-hour window show "Ej synlig nästa 24h" instead. This gives users actionable guidance on when to return to check for a planet that is currently hidden.

**Definition of Done**

- [x] `PlanetPosition` includes a new optional field `next_visible_time: Optional[str]` (UTC ISO 8601 string or null)
- [x] The `/visible` endpoint computes `next_visible_time` for every planet where `is_visible == False` by sampling the next 24 hours at 15-minute intervals; the first sample where both `altitude_deg > 10` and `sun_altitude < -12` (nautical darkness) is captured as the next visible time
- [x] A planet that never meets both conditions within 24 hours has `next_visible_time: null` in the JSON response
- [x] A planet currently visible (`is_visible == True`) has `next_visible_time: null` (no need to show future time when already observable)
- [x] Compact planet cards (`.planet-card--compact`) show the visibility pill with a tooltip; hovering or tapping the pill reveals either "Nästa synlig: HH:MM" (in Europe/Stockholm time, formatted via the existing `formatTime()` helper) or "Ej synlig nästa 24h" when `next_visible_time` is null
- [x] Full (non-compact) planet cards do not show the next-visible-time information (it's only relevant when the planet is currently hidden and the card is in compact mode)
- [x] The tooltip reuses the existing `tooltip.js` component for consistent interaction and accessibility
- [x] No regressions in existing planet card layout on 375 px and 1200 px viewports
- [x] Sampling the next 24 hours adds no more than 100 ms to the `/visible` endpoint median latency (profiled on a mid-range CPU with live ephem calls)

**Key files**
- Modify `backend/app/models/planet.py` — add `next_visible_time: Optional[str]` field to `PlanetPosition` model
- Modify `backend/app/api/routes/planets.py` — add `_compute_next_visible_time(planet_name, lat, lon, current_dt, sun_data) -> Optional[str]` helper that samples the next 24 hours at 15-minute intervals, checking both altitude > 10° and sun altitude < -12° at each sample; call this helper for every planet where `is_visible == False` before returning the response; populate the new field on each `PlanetPosition`
- Modify `frontend/js/components/planet-cards.js` — in compact card rendering, attach a tooltip to the visibility pill; tooltip content shows "Nästa synlig: {formatTime(next_visible_time)}" when `next_visible_time` is non-null, or "Ej synlig nästa 24h" when null
- Modify `frontend/css/components/planet-cards.css` — style the visibility pill in compact mode to indicate it is hoverable (e.g. subtle underline or help cursor) and ensure the tooltip appears correctly positioned

---

#### Phase B9: Nästa Bra Observationstillfälle (6-månadersprognos) — ✅

**Depends on:** Phase B1
**Parallelisable with:** Phase E series

**Intended Outcome**

Each planet card displays a "Nästa bra tillfälle" section showing when the next geometrically favourable observation opportunity occurs within the coming six months. The backend scans forward ~180 nights, sampling each planet's peak altitude during each night's nautical-darkness window and evaluating a lightweight geometric quality score based on altitude, apparent magnitude, and moon angular separation. Weather is deliberately excluded — it cannot be forecast months ahead, and the intent is to answer "when will the sky geometry next be good for watching this planet?", not "will the sky be clear?". The first night that exceeds a quality threshold is returned as the recommendation. If no qualifying night is found, the card shows "Inga bra tillfällen de närmaste 6 månaderna". Results are cached per location with a 6-hour TTL, since planetary geometry changes slowly and the computation spans ~900 ephem calls per request.

**Definition of Done**
- [x] `backend/app/services/planets/forecast.py` exports `compute_next_good_observation(planet_name, lat, lon, start_dt) -> Optional[NextGoodObservation]` scanning up to 180 nights ahead
- [x] The scanner evaluates one sample per night at the planet's peak-altitude moment within nautical darkness (sun < −12°); nights where the dark window is `None` (midnight sun) are skipped
- [x] The geometric quality score considers altitude (higher is better, minimum 15°), apparent magnitude (brighter is better), and moon angular separation (farther is better, penalty when < 20° and moon illumination > 0.4); the first night exceeding a configurable quality threshold is returned
- [x] `PlanetPosition` model includes a new optional field `next_good_observation: Optional[NextGoodObservation]` where `NextGoodObservation` is a nested Pydantic model with fields: `date` (ISO 8601 date string, e.g. `"2026-05-14"`), `start_time` (ISO 8601 UTC), `end_time` (ISO 8601 UTC), `peak_time` (ISO 8601 UTC), `peak_altitude_deg` (float), `magnitude` (float), `quality_score` (int, 0–100)
- [x] The `/visible` endpoint calls the forecast function for each planet and populates `next_good_observation` on each `PlanetPosition` in the response
- [x] Forecast results are cached per `(lat_rounded, lon_rounded)` key (rounded to 1 decimal place, ~11 km granularity) with a 6-hour TTL using the existing `CacheService`; a cache hit skips all ephem computation
- [x] A planet that is currently in an excellent observation period (e.g. opposition or high altitude during darkness) returns a `next_good_observation` with today's date, not the next future night
- [x] Mercury and Venus (inferior planets with short visibility windows) have a lower quality threshold than Mars, Jupiter, and Saturn to avoid never recommending them
- [x] Each planet card (both full and compact) renders a "Nästa bra tillfälle" row showing the date formatted as `"DD månad"` in Swedish (e.g. "14 maj") and the time window as `HH:MM–HH:MM` in Europe/Stockholm time
- [x] When `next_good_observation` is `null`, the card shows "Inga bra tillfällen kommande 6 mån" in `--color-text-muted`
- [x] The date display uses Swedish month names (januari, februari, …, december)
- [x] No regressions in existing planet card layout on 375 px and 1200 px viewports
- [x] No new API endpoints are introduced; the field is added to the existing `/visible` response schema
- [x] Forecast computation completes within 500 ms for all five planets combined (profiled with live ephem calls)

**Key files**
- Create `backend/app/services/planets/forecast.py` — `compute_next_good_observation()` with per-night dark-window sampling, geometric quality scoring, and per-planet threshold tuning
- Modify `backend/app/models/planet.py` — add `NextGoodObservation` Pydantic model and `next_good_observation: Optional[NextGoodObservation]` field on `PlanetPosition`
- Modify `backend/app/api/routes/planets.py` — call the forecast for each planet; integrate with `CacheService` using `(lat_rounded, lon_rounded)` cache key and 6-hour TTL; populate `next_good_observation` before returning
- Modify `frontend/js/components/planet-cards.js` — render "Nästa bra tillfälle" row on both full and compact cards; format date in Swedish and time window in Europe/Stockholm timezone
- Modify `frontend/css/components/planet-cards.css` — style the new forecast row, consistent with the existing "Bästa tid" styling

---

#### Phase B10: Twilight-Window Forecast för Merkurius och Venus — ✅

**Depends on:** Phase B9
**Parallelisable with:** None

**Intended Outcome**

The 6-month forecast feature adapts to the observational reality of inferior planets (Mercury and Venus), which are best viewed during twilight near maximum elongation rather than during nautical darkness when they're typically too close to the sun. The forecast scanner now uses twilight windows (sun between 0° and −12°) for Mercury and Venus, sampling both evening twilight (after sunset) and morning twilight (before sunrise) and selecting whichever offers better geometry. Outer planets (Mars, Jupiter, Saturn) continue using the existing nautical-darkness logic. The frontend requires no changes — the existing "Nästa bra tillfälle" display already shows any time window regardless of whether it's twilight or darkness.

**Definition of Done**
- [x] `backend/app/services/planets/forecast.py` exports a new helper `_compute_twilight_window_for_night(lat, lon, night_dt, is_evening: bool) -> Tuple[Optional[datetime], Optional[datetime]]` that returns the evening twilight window (sunset to sun at −12°) when `is_evening=True`, or the morning twilight window (sun at −12° to sunrise) when `is_evening=False`
- [x] `compute_next_good_observation()` branches on planet type: when `planet_name in {"Mercury", "Venus"}`, it calls `_compute_twilight_window_for_night()` for both evening and morning, samples each window via `_find_peak_in_window()`, and returns the window with the higher quality score; when `planet_name in {"Mars", "Jupiter", "Saturn"}`, the existing nautical-darkness logic (sun < −12°) is used unchanged
- [x] Mercury at 20° altitude during evening civil twilight (sun at −4°) with elongation 25° returns a forecast recommendation with `start_time` immediately after sunset and `end_time` at nautical twilight onset (sun −12°), not `None` as it would under the old nautical-darkness-only logic
- [x] Venus at 15° altitude during morning nautical twilight (sun at −10°) returns a forecast recommendation with a morning time window, demonstrating the dawn-side sampling
- [x] Mars at 30° altitude during nautical darkness (sun at −15°) continues to return the existing nautical-darkness window unchanged — outer-planet logic is unaffected
- [x] When both evening and morning twilight windows qualify for Mercury or Venus on the same night, the window with the higher `quality_score` is returned, breaking ties in favor of evening
- [x] Forecast cache keys remain unchanged (`(lat_rounded, lon_rounded)` with 6-hour TTL) — the cache logic does not distinguish between twilight and darkness windows
- [x] No regression in forecast performance: all five planets' forecasts still complete within 500 ms combined

**Key files**
- Modify `backend/app/services/planets/forecast.py` — add `_compute_twilight_window_for_night()` helper using `observer.horizon = "0"` (sunset/sunrise) and `observer.horizon = "-12"` (nautical boundaries) via `ephem.Observer.next_setting()` and `next_rising()`; modify `compute_next_good_observation()` to branch on planet type, sample both twilight windows for inferior planets, and select the window with better quality score

---

#### Phase B11: Sun and Moon Rise/Set Times in the Sky Summary — ✅

**Depends on:** Phase 5, Phase 6
**Parallelisable with:** None

**Intended Outcome**

The sky summary box above the planet cards shows two compact info blocks on the right: one for the Sun and one for the Moon. Each block shows rise and set times in Europe/Stockholm time. The frontend prefers today's rise and set when those events are still ahead of the current time, but falls back to the next upcoming event when today's time has already passed. The backend therefore returns both today's and next rise/set timestamps as raw ISO 8601 values so the UI can make the display decision without duplicating astronomical calculation logic in the browser.

**Definition of Done**
- [x] `SunInfo` in the JSON response from `GET /api/v1/planets/visible?lat=55.7&lon=13.4` includes `today_rise_time`, `today_set_time`, `next_rise_time`, and `next_set_time`, where each value is a UTC ISO 8601 string or `null`
- [x] `MoonInfo` in the same response includes `today_rise_time`, `today_set_time`, `next_rise_time`, and `next_set_time`, where each value is a UTC ISO 8601 string or `null`
- [x] When `/api/v1/planets/visible` is requested after today's sunrise but before today's sunset, the sky summary renders `Solen` with `Upp: nästa HH:MM` and `Ned: HH:MM`, formatted in Europe/Stockholm time
- [x] When today's moonrise and moonset are both still in the future, the sky summary renders `Månen` using only today's times and does not add the `nästa` label
- [x] `#skySummary` renders two clearly labelled blocks with the headings `Solen` and `Månen` to the right of the existing summary content on a 1200 px viewport without pushing the score block underneath
- [x] `#skySummary` stacks the sun and moon time blocks below the existing summary content on a 375 px viewport without horizontal overflow
- [x] `backend/tests/test_api_planets.py` verifies that the new `SunInfo` and `MoonInfo` time fields are present in the `/visible` response

**Key files**
- Modify `backend/app/models/planet.py` — add `today_rise_time`, `today_set_time`, `next_rise_time`, and `next_set_time` to `SunInfo` and `MoonInfo`
- Modify `backend/app/utils/sun.py` — compute today's and next upcoming sunrise/sunset timestamps for the observer date
- Modify `backend/app/utils/moon.py` — compute today's and next upcoming moonrise/moonset timestamps for the observer date
- Modify `backend/app/api/routes/planets.py` — populate the new sun and moon time fields in the `/visible` and `/tonight` responses
- Modify `backend/tests/test_api_planets.py` — add API assertions for the new time fields
- Modify `frontend/js/components/sky-summary.js` — choose between today's and next time using the response `timestamp` and render the `Solen` and `Månen` blocks on the right side of the summary box
- Modify `frontend/css/main.css` — extend the `sky-summary` layout so the sun/moon time block works on desktop and mobile

---

#### Phase B12: 24-Hour Altitude Timeline for Planets, Sun, and Moon — ✅

**Depends on:** Phase A1, Phase B1
**Parallelisable with:** None

**Intended Outcome**

The app gains a new top-level `Höjdkurva` view that shows a 24-hour chart from now into the future. The backend returns altitude-above-horizon time series for Mercury, Venus, Mars, Jupiter, Saturn, the Sun, and the Moon, and the frontend renders them as a responsive SVG chart using the same colours already used elsewhere in the app. The view makes it easy to see when each body is above or below the horizon, how its altitude changes over the next day, and when the Sun or Moon is likely to affect observing conditions.

**Definition of Done**
- [x] `GET /api/v1/planets/timeline?lat=55.7&lon=13.4` returns HTTP 200 and includes the top-level fields `timestamp`, `location`, `sample_interval_minutes`, and `series`, where `series` contains exactly seven objects with `name` values `Mercury`, `Venus`, `Mars`, `Jupiter`, `Saturn`, `Sun`, and `Moon`
- [x] Each `series[*].samples` collection contains UTC timestamps and `altitude_deg` values covering the next 24 hours from the response `timestamp` in 15-minute intervals; the first sample is within 15 minutes of `timestamp` and the last sample is between 23 hours 45 minutes and 24 hours 15 minutes later
- [x] A new main-navigation tab labelled `Höjdkurva` is visible; when the user activates it, `#panelAltitudeTimeline` is shown and the other tab panels are hidden using the same ARIA tab pattern as the existing tabs
- [x] The chart renders a clearly marked horizon line at `0°`, a y-axis in degrees for altitude above the horizon, and an x-axis spanning from `Nu` to `+24 h`
- [x] The lines for `Merkurius`, `Venus`, `Mars`, `Jupiter`, `Saturnus`, `Solen`, and `Månen` use the existing colour tokens `--color-planet-mercury`, `--color-planet-venus`, `--color-planet-mars`, `--color-planet-jupiter`, `--color-planet-saturn`, `--color-sun-penalty`, and `--color-moon-penalty`
- [x] On a 375 px viewport the chart remains readable without horizontal page scroll; on a 1200 px viewport the axes, labels, and legend remain readable and no plotted line is clipped outside the chart area
- [x] `backend/tests/test_api_planets.py` includes assertions that verify the response schema, the seven series names, and that `/api/v1/planets/timeline` covers a full 24-hour interval

**Key files**
- Create `backend/app/services/planets/timeline.py` — compute 24-hour altitude-above-horizon series for Mercury, Venus, Mars, Jupiter, Saturn, the Sun, and the Moon in fixed 15-minute steps from the request time
- Modify `backend/app/models/planet.py` — add Pydantic models for timeline sample points and the altitude-timeline endpoint response
- Modify `backend/app/api/routes/planets.py` — add `GET /api/v1/planets/timeline`, build the response from the new timeline service, and register the route before the `/{name}` wildcard route
- Modify `backend/tests/test_api_planets.py` — add endpoint assertions for status code, series names, and sample interval coverage
- Modify `frontend/index.html` — add the `Höjdkurva` tab button and the `#panelAltitudeTimeline` container
- Modify `frontend/js/components/tab-nav.js` — extend tab navigation and panel mapping so the new view follows the existing ARIA behaviour
- Modify `frontend/js/api.js` — add `fetchPlanetTimeline(lat, lon)` with Swedish error handling
- Modify `frontend/js/main.js` — fetch and cache altitude-timeline data when the tab is activated, refresh it on location change, and reuse cached data when the location is unchanged
- Create `frontend/js/components/altitude-timeline.js` — render the SVG chart, axes, legend, loading state, and empty state
- Modify `frontend/css/main.css` — add responsive layout and chart styles for the altitude-timeline panel, SVG, legend, axes, and horizon line

---

### Phase C: Extended Bodies

**Status: Deferred** — These phases are planned for a future iteration and are not yet scheduled for implementation. See Phase E for the current development track.

- Add Uranus and Neptune (telescope targets)
- Add bright asteroids (Vesta, Ceres)
- Add comets (when notable ones are active)
- International Space Station pass predictions

### Phase D: Notifications

**Status: Deferred** — These phases are planned for a future iteration and are not yet scheduled for implementation. See Phase E for the current development track.

- Push notifications for rare events (conjunctions, oppositions, Mercury visibility windows)
- "Tonight's highlights" daily summary

### Phase E: UI Refinements

Phase E consists of five sub-phases with distinct dependency profiles. E1 is an independent UI refinement that targets the planet cards layout and can be implemented standalone without touching the sky map or any 3D machinery. E2–E4 form a sequential 3D feature track that introduces Three.js and builds up the immersive sky view in layers: scene scaffold (E2), celestial body plotting (E3), and constellation geometry with environment polish (E4). E5 is a documentation update that closes out Phase E by ensuring ARCHITECTURE.md, TECH_CHOICES.md, and CLAUDE.md accurately reflect everything introduced during E2–E4.

#### Phase E1: Collapse Non-Visible Planets — ✅

**Depends on:** Phase B1, Phase B2, Phase B3
**Parallelisable with:** All other future phases

**Intended Outcome**

Planets that are currently not visible (either below the horizon or blocked by daylight/cloud cover) take up significantly less vertical space to make scanning for actual visible planets much easier. Instead of displaying the full grid of astronomical details (altitude, magnitude, rise/set times, etc.), non-visible planets are rendered as compact "mini-cards". These compact cards show only the planet name, a visibility status pill, and the "Bästa tid" section (if the planet becomes visible later tonight). This progressive disclosure prevents overwhelming the user with irrelevant data. Compact mode is applied only after API data has loaded — skeleton loading cards retain their full height to prevent layout shift.

**Definition of Done**
- [x] In `frontend/js/components/planet-cards.js`, `buildCard()` branches its rendering logic: planets with `is_visible == false` or `is_above_horizon == false` use a simplified compact layout.
- [x] The compact card hides the score bar, the detailed grid (altitude, direction, magnitude, constellation), and the generic rise/transit/set times.
- [x] The compact card displays the planet name, the visibility condition pill, and the "Bästa tid" section.
- [x] `frontend/css/components/planet-cards.css` is updated with styles for the compact layout (e.g., `.planet-card--compact`), reducing padding and adjusting the flex layout to save vertical space.
- [x] Non-visible planets still maintain their greyed-out visual appearance.
- [x] The "Vad ska man leta efter?" description toggle is hidden on compact cards (compact mode prioritises minimal height).
- [x] The equipment badge (added in B3) is hidden on compact cards.
- [x] Event alert badges (added in B4) are hidden on compact cards.
> **Note:** B4's event alerts are rendered in a separate `#eventAlerts` container above the planet grid, not inside individual cards. This DoD bullet is vacuously satisfied.
- [x] The visibility pill on compact cards distinguishes between "Under horisonten" (`is_above_horizon: false`) and "Ej synlig" (above horizon but not visible due to daylight or clouds).
- [x] Skeleton loading cards retain full height; compact mode only applies after API data has loaded.
- [x] No changes to the backend API are required.
- [x] Page renders neatly on both mobile and desktop viewports, seamlessly mixing full-height and compact cards in the grid.

**Key files**
- Modify `frontend/js/components/planet-cards.js` — add compact rendering flow to `buildCard()`
- Modify `frontend/css/components/planet-cards.css` — add layout rules for `.planet-card--compact`

---

#### Phase E2: 3D Sky Setting & Navigation — ✅

**Depends on:** Phase A1, Phase A2
**Parallelisable with:** Phase E1

**Note:** Three.js (~600KB minified, ~150KB gzipped) is loaded lazily — dynamically injected only when the user first activates 3D mode — to avoid impacting initial page load performance. ARCHITECTURE.md and TECH_CHOICES.md must be updated in Phase E5 to document the Three.js dependency.

**Intended Outcome**
The app gains a new immersive 3D viewing mode inside the "Stjärnkarta" tab. A toggle allows the user to switch between the existing "2D Projektion" and a new "3D Vy". **Three.js** is introduced as the 3D library, vendored as local ES module files under `frontend/lib/` (both `three.module.min.js` and `OrbitControls.js`) and resolved via a `<script type="importmap">` block in `index.html` — no CDN dependency, no build step required. A 3D scene is set up where the camera is placed precisely at the origin (0, 0, 0), acting as the user's viewpoint (creating an inside-out sphere view). Orbit controls allow the user to drag the screen to rotate and tilt the camera around the central pivot, simulating looking around the real sky. A visible horizon plane and an alt-azimuth grid are drawn to give the viewer perspective.

**Definition of Done**
- [x] Three.js r0.174.0 and OrbitControls are vendored as local ES module files under `frontend/lib/`, resolved via a `<script type="importmap">` block in `index.html` — no CDN dependency, no build step required.
- [x] A view toggle (e.g. standard buttons or a switch) is added to the "Stjärnkarta" tab allowing switching between 2D and 3D views.
- [x] Selecting "3D Vy" instantiates a full-width immersive 3D canvas instead of the SVG map.
- [x] A camera placed at the center (0,0,0) with drag-to-look controls allows full 360-degree panning and tilting.
- [x] A horizon line/plane is drawn to define where the sky meets the earth.
- [x] A celestial grid (lines marking azimuth every 30° to 45°, and lines for altitude at 30° and 60°) is drawn natively in 3D space.
- [x] Changing screen size / rotating a mobile device resizes the 3D canvas while maintaining a correct aspect ratio.
- [x] The Three.js render loop is started when the 3D view becomes active and cleanly stopped via `renderer.setAnimationLoop(null)` when the user switches to 2D view or navigates away from the Stjärnkarta tab.
- [x] The user's 2D/3D view preference is stored in `localStorage` and restored on page load.
- [x] Mobile touch controls use single-finger drag for rotation only; pinch-zoom is disabled (fixed-radius sphere view).
- [x] The 2D SVG sky map remains the default view and the accessible fallback; the 3D canvas element has `aria-hidden="true"` with a visible or screen-reader-accessible hint pointing users to the 2D view.

**Key files**
- Modify `frontend/index.html` — add the view-toggle UI to the sky map container; Three.js is not loaded here but injected dynamically on first 3D activation.
- Create `frontend/js/components/sky-map-3d.js` — core class for managing the 3D canvas, scene loop, and camera controls.
- Modify `frontend/css/components/sky-map.css` — styling for the 3D canvas container ensuring proper layout.
- Create `frontend/css/components/sky-map-3d.css` — 3D-specific styles (canvas sizing, toggle button positioning, fallback hint).
- Modify `frontend/js/main.js` — wiring 2D/3D toggle state, lazy-loading Three.js, persisting preference to `localStorage`.
- Add `frontend/lib/three.module.min.js` and `frontend/lib/OrbitControls.js` — vendored Three.js ES module dependencies resolved via import map.

---

#### Phase E3: Plotting Celestial Bodies in 3D — ✅

**Depends on:** Phase E2, Phase A3
**Parallelisable with:** None

**Intended Outcome**
The planetary bodies (and the Sun and Moon) currently plotted in 2D are brought into the 3D sphere. The spherical coordinates (altitude, azimuth) are projected into 3D Cartesian coordinates (`x, y, z`), mapping them to a fixed radius on the inner surface of the sphere. All celestial bodies are rendered as **sprites (billboarded quads)**, coloured and sized relative to their properties (e.g. magnitude), consistent with the colour coding used in the 2D view. Body text labels are rendered as **CSS2D HTML overlays** via Three.js `CSS2DRenderer`, matching the labelling style of the 2D sky map. An interactive raycaster lets the user tap or hover on bodies to summon the standard Swedish tooltips.

**Definition of Done**
- [x] Spherical coordinate math correctly converts altitude/azimuth into Cartesian coordinates for sphere plotting.
- [x] Planets, the Sun, and the Moon render as billboarded sprite quads in the celestial sky based on the current location's live API data.
- [x] Bodies with altitude < 0 (below the horizon) are hidden entirely — the ground plane from E2 acts as the occlusion boundary.
- [x] Hovering (desktop) or tapping (mobile) on a 3D celestial object works smoothly using a raycaster.
- [x] Triggering an object displays the existing Swedish tooltip interface (with name, altitude, azimuth direction, and magnitude).
- [x] Each celestial body has a text label rendered as a CSS2D HTML overlay, matching the labelling style of the 2D sky map.
- [x] `SkyMap3D` exposes a `plotBodies(planets, sun, moon, events)` method with the same parameter signature as the 2D `SkyMap.plotBodies()`.
- [x] The Sun is rendered as a larger warm-coloured sprite; the Moon sprite shows its illumination percentage in its tooltip; planets use the same colour coding as the 2D view's CSS classes.
- [x] Updating the geographic location dynamically refreshes object placement in the 3D scene.

**Key files**
- Modify `frontend/js/components/sky-map-3d.js` — implement spherical-to-cartesian projection, sprite rendering, CSS2DRenderer label overlays, and raycasting for interaction.
- Modify `frontend/js/main.js` — ensure API payload data is piped directly into the 3D view when it is active.
- Modify `frontend/js/components/tooltip.js` — may need a small adaptation to work with CSS2D-projected coordinates when called from the 3D view.

---

#### Phase E4: 3D Constellations & Environment Polish — ✅

**Depends on:** Phase E3, Phase A4
**Parallelisable with:** None

**Intended Outcome**
The 3D sky environment is completed by wrapping the viewer in constellation lines, completing the digital planetarium experience. The RA/Dec Stellarium data reused from Phase A4 is projected to the same 3D Cartesian space on the sphere, connecting the stars with `LineBasicMaterial` line segments. Cardinal direction labels (N, O, S, V) and constellation IAU labels are rendered as **CSS2D HTML overlays** via `CSS2DRenderer`, consistent with the body label approach introduced in E3. Constellation geometry is built once per data update and never rebuilt per render frame. ARCHITECTURE.md is updated in Phase E5 (not here) to document the completed 3D component.

**Definition of Done**
- [x] Constellation JSON data points are projected using `altAzToCartesian()` and connected with `LineBasicMaterial` line segments (Three.js `LineSegments`) to draw star lines behind the planets.
- [x] Constellation lines perfectly align with the planets, the Sun, and the Moon.
- [x] CSS2DRenderer renders 'N', 'O', 'S', 'V' cardinal labels smoothly around the 3D horizon ring, consistent with the E3 label approach.
- [x] Constellation labels appear mapped to their celestial geometric centres as CSS2D overlays.
- [x] Constellations below the horizon are not rendered, consistent with the 2D view's behaviour.
- [x] Constellation line geometry (Three.js `LineSegments`) is built once per data update (on location change or time refresh), not rebuilt every render frame — the render loop only handles camera rotation.
- [x] Constellation line geometry is profiled on a mid-range mobile browser; geometry rebuild occurs only on data updates, not per frame.
- [x] ARCHITECTURE.md is updated with a `SkyMap3D` component description, its interface (`plotBodies`, `plotConstellations`), and the Three.js/CSS2DRenderer dependency — this is done in Phase E5.

**Key files**
- Modify `frontend/js/components/sky-map-3d.js` — loop through constellation sets generating `LineSegments` geometry and CSS2D cardinal labels.
- Modify `frontend/js/astro-projection.js` — add an `altAzToCartesian(altitude_deg, azimuth_deg, radius)` export that converts spherical sky coordinates to Three.js `{x, y, z}` scene coordinates.
- Add `frontend/data/constellations.json` — reused from Phase A4; referenced here for completeness.
- Modify `frontend/js/main.js` — pass constellation data and location into `SkyMap3D` on each render.

---

#### Phase E5: Documentation Update — ✅

**Depends on:** Phase E4
**Parallelisable with:** None

**Intended Outcome**
All project documentation is updated to accurately reflect the Three.js dependency and the new 3D component architecture introduced in E2–E4. This is a documentation-only phase: no source code changes, no new features.

**Definition of Done**
- [x] `ARCHITECTURE.md` describes the `SkyMap3D` class, its public interface (`plotBodies`, `plotConstellations`), and how it relates to the 2D `SkyMap` — including the CSS2DRenderer overlay approach and the `altAzToCartesian` utility.
- [x] `ARCHITECTURE.md` includes the 2D/3D component hierarchy in the component diagram.
- [x] `TECH_CHOICES.md` documents the Three.js choice with rationale: WebGL 3D library, actively maintained, well-documented, IIFE/UMD build available for no-bundler projects.
- [x] `TECH_CHOICES.md` documents the vendored-over-CDN decision: no runtime CDN dependency, consistent with the project's offline-capable constraint.
- [x] `TECH_CHOICES.md` documents the lazy-loading strategy: Three.js is loaded dynamically only when the user first activates 3D mode, to avoid impacting initial page load (~150KB gzipped).
- [x] `CLAUDE.md` stack section is updated if Three.js is confirmed as a permanent part of the stack.

**Key files**
- `ARCHITECTURE.md` — add `SkyMap3D` component description, CSS2DRenderer usage, `altAzToCartesian` utility, and the 2D/3D component hierarchy
- `TECH_CHOICES.md` — document the Three.js decision: why Three.js over alternatives, why vendored over CDN, lazy-loading strategy
- `CLAUDE.md` — add Three.js to the stack description if appropriate

---

#### Phase E6: Expanderingsknapp för stjärnkartan — ✅

**Depends on:** Phase E5
**Parallelisable with:** None

**Intended Outcome**
Användaren kan expandera stjärnkartan (2D eller 3D) så att den fyller hela webbläsarfönstret, och sedan minimera den tillbaka till ursprunglig storlek. En knapp placeras i `.sky-map-panel` och togglar klassen `.sky-map-panel--expanded`, som via CSS-regler tar över hela skärmen (`position: fixed; inset: 0`). Three.js-renderaren ritar om canvasen automatiskt via det befintliga `_handleResize()`-anropet, och SVG:en för 2D-vyn skalas korrekt via sin `viewBox`.

**Definition of Done**
- [x] En knapp med texten "Förstora" och "Minimera" (beroende på läge) syns i `.sky-map-panel` för både 2D- och 3D-läget
- [x] Klick på knappen togglar klassen `.sky-map-panel--expanded` på `.sky-map-panel` och panelen täcker hela webbläsarfönstret (`100vw × 100vh`) utan scrollbars
- [x] Klick igen tar bort klassen och återgår kartan till ursprunglig layout (`max-width: 600px; aspect-ratio: 1/1`)
- [x] 3D-canvasen ritar om utan svarta kanter eller felaktiga proportioner i expanderat läge (verifieras via `SkyMap3D._handleResize()`)
- [x] 2D-SVG:en fyller det expanderade utrymmet utan distorsion (aspect ratio bevaras via `viewBox="0 0 500 500"`)

**Key files**
- Modify `frontend/index.html` — lägg till expand/minimera-knapp inuti `.sky-map-panel`
- Modify `frontend/css/components/sky-map.css` — lägg till `.sky-map-panel--expanded`-regler med `position: fixed; inset: 0; z-index` för helskärmsläge
- Modify `frontend/css/components/sky-map-3d.css` — lägg till expanded-state-regler för `#skyMap3dContainer` i helskärmsläge
- Modify `frontend/js/main.js` — koppla knapptryckning till klasstoggle och anrop till `skyMap3d._handleResize()`

---

#### Phase E7: Zoom in the 2D and 3D Sky Map — ✅

**Depends on:** Phase E6
**Parallelisable with:** Phase B1, Phase B2

**Intended Outcome**
The user can zoom in and out in both the 2D and 3D sky map using pinch/scroll gestures and via +/− buttons in the map view. In the 2D view the SVG's `viewBox` is adjusted around the map centre to zoom without changing the projection maths. In the 3D view the camera's `fov` (field of view) is changed instead of moving the camera, because the camera sits at the origin inside the sphere. The zoom level is reset on view switch (2D/3D) and on new data fetch to avoid disorientation.

**Definition of Done**
- [x] Two buttons labelled "+" and "−" are visible in `.sky-map-panel` in both 2D and 3D mode, positioned without overlapping the existing expand/collapse button
- [x] Clicking "+" zooms in (shows a smaller portion of the sky in greater detail); clicking "−" zooms out (shows a larger portion of the sky)
- [x] Pinch-zoom on mobile devices and scroll wheel on desktop zoom in/out in both views
- [x] In the 2D view the SVG's `viewBox` attribute is adjusted dynamically around the centre point `(250, 250)` within the range 200×200 (maximum zoom-in) to 500×500 (default, fully zoomed out)
- [x] In the 3D view `PerspectiveCamera.fov` is adjusted within the range 20° (maximum zoom-in) to 90° (maximum zoom-out), with a default value of 60°
- [x] The camera in the 3D view stays at the origin `(0, 0, 0.001)` regardless of zoom level — dolly-zoom via OrbitControls remains disabled (`enableZoom = false`); FOV zoom is handled manually
- [x] The zoom level is reset to the default on switching between 2D and 3D and on new data fetch (location change)
- [x] The zoom buttons work correctly in both normal mode and expanded fullscreen mode (`.sky-map-panel--expanded`)
- [x] No JavaScript console errors on rapid repeated zoom or on zooming an empty map (before API data has loaded)

**Key files**
- Modify `frontend/index.html` — add +/− zoom buttons inside `.sky-map-panel`
- Modify `frontend/js/components/sky-map.js` — add `zoomIn()`, `zoomOut()`, and `resetZoom()` methods that adjust the SVG's `viewBox`; add wheel event listener on the SVG element
- Modify `frontend/js/components/sky-map-3d.js` — add `zoomIn()`, `zoomOut()`, and `resetZoom()` methods that adjust `camera.fov` and call `camera.updateProjectionMatrix()`; add wheel event listener on the canvas
- Modify `frontend/js/main.js` — wire +/− button presses to the active view's zoom methods; call `resetZoom()` on view switch and on location change
- Modify `frontend/css/components/sky-map.css` — add `.sky-map-zoom-controls` rules for button placement and styling, consistent with the existing `.sky-map-expand-btn`

---

#### Phase E8: Stjärnbilder — Aktivering och Intensitetskontroll — ✅

**Depends on:** Phase E7
**Parallelisable with:** None

**Intended Outcome**
The sky map panel gains two constellation controls visible in both the 2D and 3D views: a toggle that immediately shows or hides all constellation lines and labels without a full re-render, and an intensity slider that adjusts constellation line opacity in real time from nearly invisible to fully opaque. Both settings are persisted in `localStorage` and restored on page load. The hardcoded `opacity: 0.25` literals in `sky-map.css` and `opacity: 0.5` in `sky-map-3d.js` are replaced by the slider-driven value, making the slider the single source of truth for constellation brightness.

**Definition of Done**
- [x] A toggle (`<input type="checkbox">`) labelled "Stjärnbilder" appears in the sky map controls area in `frontend/index.html`; unchecking it immediately hides all constellation SVG elements in the 2D view and sets `_constellationsGroup.visible = false` in the 3D view without requiring a full API re-fetch or re-render.
- [x] A range slider (`<input type="range" min="0" max="1" step="0.05">`) labelled "Intensitet" appears alongside the toggle; dragging it updates the `opacity` attribute on the `<g class="sky-map-constellations">` group (2D) and the `LineBasicMaterial.opacity` on children of `_constellationsGroup` (3D) in real time.
- [x] The enabled state and opacity value are written to `localStorage` under keys `planet_constellation_enabled` and `planet_constellation_opacity` and are read back on page load, restoring the user's last preference.
- [x] The hardcoded `opacity: 0.25` in `frontend/css/components/sky-map.css` on `.sky-map-constellation-line` and `.sky-map-constellation-label` is removed so the slider is the sole opacity source.
- [x] The hardcoded `opacity: 0.5` in the `THREE.LineBasicMaterial` constructor inside `sky-map-3d.js` `plotConstellations()` is replaced by the stored or current slider value.
- [x] The new controls are styled consistently with the existing `.sky-map-zoom-controls` and `.sky-map-expand-btn` in `frontend/css/components/sky-map.css`.

**Key files**
- Modify `frontend/index.html` — add constellation toggle checkbox and intensity slider markup inside `.sky-map-panel`
- Modify `frontend/js/main.js` — add `localStorage` read/write for `planet_constellation_enabled` and `planet_constellation_opacity`; wire slider `input` and checkbox `change` events; pass current values to `skyMap` and `skyMap3d` on each update
- Modify `frontend/js/components/sky-map.js` — accept an `opacity` parameter in `plotConstellations()` and apply it to the `<g class="sky-map-constellations">` group; add `setConstellationsVisible(bool)` to show/hide the group instantly
- Modify `frontend/js/components/sky-map-3d.js` — accept an `opacity` parameter in `plotConstellations()` and apply it to the `LineBasicMaterial`; add `setConstellationsVisible(bool)` toggling `_constellationsGroup.visible`
- Modify `frontend/css/components/sky-map.css` — remove hardcoded `opacity: 0.25` from constellation rules; add styles for the new toggle and slider controls

---

#### Phase E8.1: Constellation Data Rebuild Pipeline — ✅

**Depends on:** Phase A4 (Constellation data), Phase E8 (Constellation rendering)

**Context:** While investigating constellation display issues, found that constellation coordinates needed validation and a reproducible rebuild process. Created automated tooling to regenerate data from authoritative sources (commit 0b3b695).

**Tasks:**
1. Create download script for source data
   - HYG Database v3.8 star catalog (30-35 MB)
   - Stellarium v24.4 constellation topology (8-10 KB)
   - Automated validation and decompression
2. Create build script with validation
   - Parse Stellarium constellation definitions
   - Look up coordinates from HYG catalog
   - Cross-validate against bright-stars.json (0.1° tolerance)
   - Generate frontend/data/constellations.json
3. Document data provenance and rebuild workflow
   - ARCHITECTURE.md: Rebuild workflow section
   - TECH_CHOICES.md: Data source rationale
   - Inline documentation in build scripts
4. Configure git exclusions
   - .gitignore: Exclude large downloaded files (regeneratable)

**Intended Outcome:** Constellation coordinates are reproducible from authoritative sources with automated validation, ensuring astronomical accuracy and enabling future updates when source data is revised.

**Definition of Done:**
- [x] tools/download_sources.sh exists and fetches source data with validation
- [x] tools/build_constellations.py generates constellations.json with coordinate validation
- [x] Downloaded source files excluded from git (tools/data/*.csv, *.fab in .gitignore)
- [x] ARCHITECTURE.md documents two-step rebuild workflow
- [x] TECH_CHOICES.md explains data source selection (Stellarium + HYG)
- [x] THIRD_PARTY_LICENSES.md includes Stellarium GPL-2.0-or-later attribution
- [x] Build script includes comprehensive docstring with usage instructions
- [x] Validation against bright-stars.json passes (< 0.1° tolerance)
- [x] Generated constellations.json matches schema (30 constellations, valid RA/Dec ranges)

---

#### Phase E9: Ljusstarka Stjärnor i Stjärnkartan — ✅

**Depends on:** Phase E8, Phase 12, Phase A3
**Parallelisable with:** None

**Intended Outcome**

The sky map — both the 2D SVG view and the 3D dome — displays the brightest naked-eye stars from a static catalog whenever those stars are actually visible from the observer's sky. Visibility uses the same twilight limiting-magnitude criterion as the planetary scorer (Phase 12): a star is rendered only when its altitude is above 0° and its apparent magnitude is brighter than the sky's current limiting magnitude derived from the sun's elevation angle. Weather is deliberately excluded — a completely overcast sky still shows the theoretically visible stars, exactly as the planetary `is_visible` flag excludes weather. Stars are rendered as small white dots/sprites layered between the constellation lines and the planetary bodies, sized proportionally to brightness. Named stars are labelled with their internationally recognised name (most have no distinct Swedish equivalent, but the label uses the accepted name). The sky's `limiting_magnitude` is added to the `SunInfo` API response so the frontend can apply the same threshold the backend already uses for planets.

**Definition of Done**
- [x] `SunInfo` in the `GET /api/v1/planets/visible` JSON response contains a `limiting_magnitude` float field; its value is approximately 6.5 when `sun.elevation_deg` is −20° and approximately −1 when `sun.elevation_deg` is −6°, matching the Phase 12 Schaefer model
- [x] `frontend/data/bright-stars.json` exists and contains at least 40 stars with visual magnitude ≤ 2.5, each with fields `ra_deg`, `dec_deg`, `magnitude`, and `name` (internationally recognised name string)
- [x] In the 2D sky map, the star Sirius (RA 101.3°, Dec −16.7°, mag −1.46) renders as an SVG dot in the `.sky-map-stars` group at the correct computed altitude/azimuth position when it is above the horizon and the sun is below −18°; no dot appears when the sun is above 0°
- [x] In the 3D sky map, the same visibility filter applies and the same stars visible in the 2D view are visible in the 3D view at matching positions
- [x] Stars with altitude ≤ 0° are not rendered in either view
- [x] Star dots are visually smaller than planet dots; the brightest star (Sirius, mag −1.46) has a smaller dot radius than Venus (mag −4) in the 2D view and a smaller sprite scale in the 3D view
- [x] Both `SkyMap.plotStars()` and `SkyMap3D.plotStars()` accept the identical parameter signature `(stars, limitingMagnitude, lat, lon, utcTimestamp)`, consistent with the `plotBodies`/`plotConstellations` pairing convention
- [x] No JavaScript console errors when `plotStars()` is called with an empty array (e.g. during daytime when no stars clear the limiting-magnitude threshold)
- [x] The star layer renders behind all planetary bodies in both views; planets, Sun, and Moon are never occluded by a star dot

**Key files**
- Modify `backend/app/models/planet.py` — add `limiting_magnitude: float` field to `SunInfo`
- Modify `backend/app/api/routes/planets.py` — pass `sun_data["limiting_magnitude"]` from `calculate_sun_penalty()` into `_build_sun_info()` constructor
- Create `frontend/data/bright-stars.json` — static catalog of ≥ 40 stars with magnitude ≤ 2.5, fields: `ra_deg`, `dec_deg`, `magnitude`, `name`
- Modify `frontend/js/components/sky-map.js` — add `plotStars(stars, limitingMagnitude, lat, lon, utcTimestamp)` method; use `raDecToAltAz()` to compute positions; render visible stars as `<circle>` elements in a new `<g class="sky-map-stars">` group inserted after the constellation group and before the bodies group; dot radius = `3 - magnitude * 0.7` (clamped to 1–4 px equivalent)
- Modify `frontend/js/components/sky-map-3d.js` — add `plotStars(stars, limitingMagnitude, lat, lon, utcTimestamp)` method; use `raDecToAltAz()` and `altAzToCartesian()` to position white sprites on the sphere surface; call before `_bodiesGroup` is added so stars render behind planets
- Modify `frontend/js/main.js` — fetch `bright-stars.json` once on startup; call `skyMap.plotStars()` and `skyMap3d.plotStars()` after each data refresh, passing `data.sun.limiting_magnitude`, `location.lat`, `location.lon`, and the API timestamp

---

#### Phase E10: Tooltips for Visible Stars in the Sky Map — ✅

**Depends on:** Phase E9
**Parallelisable with:** None

**Intended Outcome**

The bright stars already plotted in both the 2D SVG sky map and the 3D dome become interactive in the same way as the planets. When the user hovers a visible star on desktop, or taps it in the 3D view, a tooltip appears via the existing `tooltip.js` mechanism. The tooltip identifies the star by name and shows concrete observation data in Swedish formatting, so the star layer is no longer purely decorative and becomes useful for sky orientation.

**Definition of Done**
- [x] Visible stars in the 2D view render as interactive tooltip targets inside `.sky-map-stars` instead of purely decorative `<circle>` elements; hover or keyboard focus shows a tooltip with the star's name, altitude (`Höjd: X°`), direction (`Riktning: ...`), and magnitude
- [x] Visible stars in the 3D view participate in the same raycaster flow as the planets, so hovering or tapping a star sprite shows the corresponding tooltip without requiring a separate information panel
- [x] Star tooltip content reuses the existing `TooltipManager` convention (`.info-icon` + `title` or `data-tooltip-title`) and introduces no new tooltip component
- [x] Stars filtered out by `limiting_magnitude` or lying below the horizon have no tooltip and leave no invisible interaction targets behind in the DOM or 3D scene
- [x] The star Sirius shows a tooltip with the name `Sirius` and its magnitude when visible in the sky map; the same star shows no tooltip in daylight when it is not rendered
- [x] No regression occurs in existing planet tooltips in 2D or 3D; planets, the Sun, and the Moon continue to show Swedish tooltip text as before
- [x] No JavaScript errors occur when `plotStars()` is called with an empty array or when the user moves the pointer over a map with no visible stars

**Key files**
- Modify `frontend/js/components/sky-map.js` — make star circles in `plotStars()` focusable and tooltip-compatible by adding name and observation data for each visible star
- Modify `frontend/js/components/sky-map-3d.js` — extend `plotStars()` and the raycaster logic so star sprites can trigger the same tooltip flow as the planetary bodies
- Modify `frontend/css/components/sky-map.css` — add subtle hover/focus styling for interactive stars in the 2D map without visually competing with planet markers
- Modify `frontend/css/components/sky-map-3d.css` — add any cursor- or focus-related styling needed for interactive star tooltip targets in the 3D view

---

#### Phase E11: Match Maximum Constellation Intensity Between 2D and 3D — ✅

**Depends on:** Phase E8
**Parallelisable with:** None

**Intended Outcome**

The constellation intensity slider continues to control both sky-map renderers from one shared value, but the maximum setting now produces the same perceived line intensity in both the 2D SVG map and the 3D Three.js dome. The current mismatch, where the 3D view remains noticeably dimmer even at the slider's highest position, is removed so the user can trust that `Intensitet` means the same thing regardless of whether the active view is `2D Projektion` or `3D Vy`.

**Definition of Done**
- [x] With the `Intensitet` slider at its maximum value (`1`), constellation lines in the 3D view are visually as strong as the corresponding lines in the 2D view for the same location and timestamp; the 3D view no longer appears dimmer at the top setting
- [x] `frontend/js/main.js` continues to use a single shared `constellationOpacity` value for both renderers; no second slider state or 3D-only storage key is introduced
- [x] `SkyMap.plotConstellations(..., opacity)` and `SkyMap3D.plotConstellations(..., opacity)` both accept the same slider-domain input, but the 3D renderer maps that input so the effective maximum intensity matches the 2D renderer's maximum appearance
- [x] Moving the `Intensitet` slider away from the maximum still updates both views immediately, and switching between `2D Projektion` and `3D Vy` preserves the same stored slider value from `planet_constellation_opacity`
- [x] Constellation labels in the 3D view remain legible when lines are at maximum intensity and do not become disproportionately faint relative to the 2D IAU labels
- [x] No regressions occur in constellation visibility toggling: unchecking `Stjärnbilder` still hides both lines and labels instantly in 2D and 3D without a data refetch
- [x] No JavaScript errors occur when the slider is dragged repeatedly between minimum and maximum while the user switches between 2D and 3D views

**Key files**
- Modify `frontend/js/main.js` — keep the intensity slider as the single shared control and pass the normalized value consistently to both sky-map renderers on load, slider input, and view switches
- Modify `frontend/js/components/sky-map.js` — confirm and preserve the 2D constellation opacity behavior as the visual reference for the maximum slider setting
- Modify `frontend/js/components/sky-map-3d.js` — adjust line-material and label-intensity handling in `plotConstellations()` so the maximum slider value matches the 2D view's perceived brightness
- Modify `frontend/css/components/sky-map-3d.css` — add or tune any 3D constellation label styling needed so labels remain readable when the line intensity is raised to match 2D

---

#### Phase E12: 3D Stjärnkarta — Intermediärkompassriktningar och Färgkonsistens ✅

**Depends on:** Phase E4, Phase E3
**Parallelisable with:** None

**Intended Outcome**
The 3D sky dome gains the four intermediate compass direction labels already present in the 2D view — NO, SO, SV, NV — rendered as canvas-texture sprites at azimuths 45°, 135°, 225°, and 315°, placed at the horizon ring at a slightly smaller scale and dimmer colour than the main cardinal sprites to match the 2D visual hierarchy (where intermediate labels use `.sky-map-label--muted`). In addition, the Sun and Moon sprite colours in the 3D view are aligned with the CSS design tokens used in the 2D SVG map: the Moon changes from white-grey (`#e2e8f0`) to the purple token (`--color-moon-penalty` = `#c084fc`) and the Sun changes from pale yellow (`#fde68a`) to the amber token (`--color-sun-penalty` = `#f59e0b`). After this phase the two renderers are fully colour-consistent and share the same visual compass vocabulary.

**Definition of Done**
- [x] The 3D sky dome renders NO, SO, SV, NV labels at azimuths 45°, 135°, 225°, and 315° — confirmed by activating 3D-läge and visually inspecting the four intermediate labels around the horizon ring
- [x] The intermediate sprites in 3D are visually subordinate to the main cardinal sprites (N, O, S, V) — smaller scale or noticeably dimmer colour — matching the muted hierarchy in the 2D view
- [x] `BODY_COLORS.moon` in `frontend/js/components/sky-map-3d.js` equals `'#c084fc'`, causing the Moon sprite in the 3D dome to appear purple, consistent with the `.sky-map-body--moon { fill: var(--color-moon-penalty) }` rule that governs the 2D moon dot
- [x] `BODY_COLORS.sun` in `frontend/js/components/sky-map-3d.js` equals `'#f59e0b'`, causing the Sun sprite in the 3D dome to appear amber, consistent with the `.sky-map-body--sun { fill: var(--color-sun-penalty) }` rule in the 2D view
- [x] Existing cardinal labels N, O, S, V in the 3D view are unchanged in position, size, and colour
- [x] No JavaScript console errors appear when switching between 2D- and 3D-läge or when the sky map re-renders after a location change

**Key files**
- Modify `frontend/js/components/sky-map-3d.js` — add an `INTERMEDIATES` constant array (NO at 45°, SO at 135°, SV at 225°, NV at 315°); extend `buildCardinalLabels()` to loop over `INTERMEDIATES` and call a muted variant of `buildCardinalSprite()` (smaller canvas font, reduced sprite scale, dimmer fill colour); change `BODY_COLORS.sun` from `'#fde68a'` to `'#f59e0b'`; change `BODY_COLORS.moon` from `'#e2e8f0'` to `'#c084fc'`

---

#### Phase E13: Helskärmsläge för Solsystemsvy — ✅

**Depends on:** Phase E6, Phase 13
**Parallelisable with:** Phase B6, Phase B7, Phase E9, Phase E10, Phase E11

**Intended Outcome**
The solar system view gains the same fullscreen capability as the 2D and 3D sky maps. A "Förstora" button appears in the solar system panel that, when clicked, expands the view to fill the entire browser window using the same CSS-based approach established in Phase E6. The SVG diagram scales via its viewBox attribute to fill the expanded space without distortion, maintaining correct orbital proportions. Clicking "Minimera" returns the view to its normal embedded size.

**Definition of Done**
- [x] En knapp med texten "Förstora" och "Minimera" (beroende på läge) syns i `#panelSolarSystem` container
- [x] Klick på knappen togglar klassen `.solar-system-panel--expanded` på solsystemspanelen och vyn täcker hela webbläsarfönstret (`100vw × 100vh`) utan scrollbars
- [x] Klick igen tar bort klassen och återgår vyn till ursprunglig layout
- [x] SVG:en för solsystemet fyller det expanderade utrymmet utan distorsion (aspect ratio bevaras via `viewBox` precis som för 2D-stjärnkartan)
- [x] Planettolltips fortsätter fungera korrekt i både normalt och expanderat läge
- [x] Ingen regression i befintlig solsystemsvy-rendering på 375 px och 1200 px viewports

**Key files**
- Modify `frontend/index.html` — lägg till expand/minimera-knapp inuti `#panelSolarSystem` container
- Modify `frontend/css/components/solar-system-view.css` — lägg till `.solar-system-panel--expanded`-regler med `position: fixed; inset: 0; z-index` för helskärmsläge, konsistent med `.sky-map-panel--expanded` från Phase E6
- Modify `frontend/js/main.js` — koppla knapptryckning till klasstoggle på solsystemspanelen

> **Implementation note:** Use the `frontend-enhancement` skill for this phase — frontend-only change reusing an established pattern, no new backend computation.

---

### Phase F: Solsystemsvy — Interaktiv Planetutforskning

The solar system view gains interactive planet exploration. Clicking a planet dot zooms in and presents an encyclopedic information panel, a rendering of the planet's largest moons at their current positions as seen from Earth, and (for Saturn) the ring system tilted to match the current Earth–Saturn geometry. F1 (click, zoom, and info) is the foundation; F2 (moons) and F3 (rings) build on the zoomed-in detail view and can be implemented in parallel with each other.

#### Phase F1: Planetklick & Zoom med Informationsruta — ✅

**Depends on:** Phase 13
**Parallelisable with:** Phase E series

**Intended Outcome**

Clicking or tapping a planet dot in the solar system SVG smoothly zooms the viewBox to centre on that planet, then presents a detail overlay containing a Swedish-language encyclopedic information panel. The panel includes physical characteristics (diameter, orbital period, distance from the Sun), notable features, and number of known moons — static factual content sourced from publicly available encyclopedic knowledge and stored in a frontend data file, analogous to the existing `planet-descriptions.js`. A "Tillbaka" button reverses the zoom and returns to the full solar system overview. The interaction works for all five naked-eye planets and Earth.

**Definition of Done**
- [ ] Clicking a planet dot (Merkurius, Venus, Mars, Jupiter, Saturnus) in the solar system SVG triggers a smooth viewBox transition that centres the clicked planet within 400 ms
- [ ] After the zoom completes, an info overlay or panel is visible containing the planet's Swedish name, diameter (km), orbital period, mean distance from the Sun (AU), number of known moons, and a 2–3 sentence description of notable features — all text in Swedish
- [ ] `frontend/js/data/planet-info.js` exists and exports a keyed object with encyclopedic data for all five planets and Earth; each entry includes at minimum: `diameter_km`, `orbital_period_sv`, `distance_au`, `known_moons`, `description_sv`
- [ ] Clicking the Earth dot in the solar system SVG also triggers the zoom and shows Earth's info panel
- [ ] A "Tillbaka" button or click-outside-to-dismiss gesture reverses the zoom and hides the info overlay, restoring the full solar system viewBox
- [ ] The zoomed-in state and info panel are usable on both 375 px and 1200 px viewports without overflow
- [ ] The info overlay is keyboard-accessible: focusable "Tillbaka" button, Escape key dismisses the overlay
- [ ] No JavaScript console errors when clicking planets before API data has loaded (the view gracefully ignores clicks when no planet positions are available)

**Key files**
- Create `frontend/js/data/planet-info.js` — static Swedish encyclopedic data for Mercury, Venus, Earth, Mars, Jupiter, Saturn (physical facts, orbital data, notable features, known moon count)
- Modify `frontend/js/components/solar-system-view.js` — add click handler on planet dots and Earth dot; implement viewBox zoom animation; render detail overlay with info panel and "Tillbaka" button; manage zoomed/overview state
- Modify `frontend/css/components/solar-system-view.css` — style `.solar-system__detail-overlay` info panel, zoom transition, "Tillbaka" button, responsive layout for zoomed state
- Modify `frontend/js/main.js` — wire Escape key handler to dismiss zoomed state when solar system tab is active

> **Implementation note:** Use the `frontend-enhancement` skill for this phase — frontend-only change using static data, no new backend computation.

---

#### Phase F2: Månpositioner för Jätteplaneter — ✅

**Depends on:** Phase F1
**Parallelisable with:** Phase F3

**Intended Outcome**

When the user zooms into Jupiter or Saturn in the solar system detail view, the planet's largest moons are rendered as small labelled dots at their current positions relative to the planet as seen from Earth. The backend computes moon positions using `ephem`'s built-in satellite calculators (`ephem.Io()`, `ephem.Europa()`, `ephem.Ganymede()`, `ephem.Callisto()` for Jupiter; `ephem.Titan()`, `ephem.Rhea()`, `ephem.Dione()`, `ephem.Tethys()`, `ephem.Enceladus()`, `ephem.Mimas()`, `ephem.Iapetus()` for Saturn), which report X/Y offsets in parent-planet radii as seen from Earth — ideal for this rendering. The frontend renders moons as dots positioned around a larger planet circle in the detail overlay, with Swedish labels. All positions are computed for the current time, matching the solar system view's timestamp.

**Definition of Done**
- [x] `backend/app/services/planets/moons.py` exists and exports `compute_moon_positions(dt: datetime) -> dict` returning X/Y offsets (in parent-planet radii) for Jupiter's 4 Galilean moons and Saturn's 7 major moons
- [x] `PlanetPosition` model includes a new optional field `moons: Optional[List[MoonPosition]]` where `MoonPosition` is a Pydantic model with fields `name` (str), `name_sv` (str), `x_offset` (float, planet radii), `y_offset` (float, planet radii)
- [x] `GET /api/v1/planets/visible?lat=55.7&lon=13.4` returns a non-empty `moons` array for both Jupiter and Saturn; Mercury, Venus, and Mars return `moons: null` or an empty list
- [x] The zoomed-in detail view for Jupiter renders 4 moon dots (Io, Europa, Ganymedes, Callisto) positioned around the planet circle at offsets matching their current `x_offset`/`y_offset` values
- [x] The zoomed-in detail view for Saturn renders at least Titan and the other major moons as labelled dots
- [x] Each moon dot has a Swedish label (e.g. "Io", "Europa", "Ganymedes", "Callisto", "Titan") rendered adjacent to the dot
- [x] Moon dots are visually smaller than the planet circle and use a muted colour distinct from the planet's colour token
- [x] Hovering or tapping a moon dot shows a tooltip with the moon's Swedish name and its current offset distance from the planet
- [x] Planets without moons in the API response (Mercury, Venus, Mars) show no moon rendering in their detail view — no errors or empty-state clutter
- [x] No regression in existing solar system view rendering; the overview mode (unzoomed) is unaffected by the moon data addition

> Note: Minor label-anchor asymmetry for right-side moon labels is cosmetic (not a DoD failure). Can be addressed in a future polish pass.

**Key files**
- Create `backend/app/services/planets/moons.py` — compute moon positions using `ephem.Io()`, `ephem.Europa()`, `ephem.Ganymede()`, `ephem.Callisto()`, `ephem.Titan()`, `ephem.Rhea()`, etc.; return X/Y offsets in planet radii as seen from Earth
- Modify `backend/app/models/planet.py` — add `MoonPosition` Pydantic model and `moons: Optional[List[MoonPosition]]` field on `PlanetPosition`
- Modify `backend/app/api/routes/planets.py` — call `compute_moon_positions()` in the `/visible` handler; populate `moons` field on Jupiter and Saturn `PlanetPosition` objects
- Modify `frontend/js/components/solar-system-view.js` — in the zoomed-in detail overlay, render moon dots around the planet circle for Jupiter and Saturn using their `moons` array data; add tooltip interaction for moon dots
- Modify `frontend/css/components/solar-system-view.css` — style `.solar-system__moon` dots, labels, and hover/focus states

> **Implementation note:** Use the `full-stack-feature` skill for this phase — new backend computation (ephem moon positions) and frontend rendering.

---

#### Phase F3: Saturnusringar — Visuell Rendering — ✅

**Depends on:** Phase F1
**Parallelisable with:** Phase F2

**Intended Outcome**

When the user zooms into Saturn in the solar system detail view, the planet's ring system is rendered as a tilted ellipse matching the ring opening angle as seen from Earth at the current time. The backend computes the ring tilt using `ephem.Saturn()`'s `earth_tilt` attribute, which gives the inclination of Saturn's rings toward the Earth observer in radians. The frontend renders the rings as an SVG ellipse where the semi-major axis represents the ring's physical extent and the semi-minor axis is scaled by `sin(earth_tilt)`, producing the correct apparent foreshortening. When the rings are nearly edge-on (`earth_tilt` close to 0°), the ellipse collapses to a thin line, faithfully representing the real-world view.

**Definition of Done**
- [x] `PlanetPosition` model includes a new optional field `ring_tilt_deg: Optional[float]` populated only for Saturn, representing the ring tilt toward Earth in degrees (positive = southern face visible (pyephem convention), negative = northern face visible)
- [x] `GET /api/v1/planets/visible?lat=55.7&lon=13.4` returns a non-null `ring_tilt_deg` value for Saturn; all other planets return `ring_tilt_deg: null`
- [x] The zoomed-in detail view for Saturn renders an SVG ellipse around the planet circle; the ellipse's semi-minor axis is proportional to `|sin(ring_tilt_deg)|`, correctly representing the apparent ring opening
- [x] At the current epoch (2025–2026, ring tilt near 0°), Saturn's rings render as a very thin ellipse nearly edge-on — matching the real-world near-edge-on passage expected in 2025
- [x] The ring ellipse uses Saturn's gold colour token (`--color-planet-saturn`) at reduced opacity (e.g. 0.4) so moons from Phase F2 remain visible through the ring
- [x] The ring rendering does not obscure the Saturn planet circle or its label
- [x] Planets other than Saturn show no ring rendering in their zoomed-in detail view
- [x] No regression in existing solar system overview rendering; ring data is only visible in the zoomed-in state

**Key files**
- Modify `backend/app/services/planets/moons.py` — add `compute_ring_tilt(dt: datetime) -> Optional[float]` that reads `ephem.Saturn().earth_tilt` and converts to degrees
- Modify `backend/app/models/planet.py` — add `ring_tilt_deg: Optional[float]` field on `PlanetPosition`
- Modify `backend/app/api/routes/planets.py` — call `compute_ring_tilt()` and populate `ring_tilt_deg` on Saturn's `PlanetPosition`
- Modify `frontend/js/components/solar-system-view.js` — in the zoomed-in detail overlay for Saturn, render an SVG `<ellipse>` with semi-minor axis derived from `ring_tilt_deg`; layer the ring behind moon dots but in front of the planet background
- Modify `frontend/css/components/solar-system-view.css` — style `.solar-system__ring` ellipse with Saturn gold colour at reduced opacity

> **Implementation note:** Use the `full-stack-feature` skill for this phase — new backend computation (ring tilt) and frontend rendering.

---

#### Phase F4: Integrated Zoom View with Side Info Panel — ✅

**Depends on:** Phase F2, Phase F3
**Parallelisable with:** None

**Intended Outcome**

When the user zooms into a planet in the solar system view, the enlarged planet rendering remains inside the same solar system panel instead of moving into a separate small info window. The information panel is shown to the left of the selected planet on larger viewports, while the zoomed planet rendering with moons and Saturn's rings remains visible in the same composed view. This lets the user read the facts while still seeing the full selected planet and all currently rendered moons at the same time.

**Definition of Done**
- [x] Clicking Jupiter or Saturn keeps the zoomed rendering inside the existing solar system panel; no dark fullscreen or modal overlay hides the actual planet view
- [x] On wider viewports, the information panel renders to the left of the zoomed planet, and the selected planet remains fully visible to the right in the same layout
- [x] For Jupiter, all moons present in `planet.moons` render simultaneously in the zoomed view without any moon dots being clipped by the panel edge
- [x] For Saturn, the zoomed view renders the planet, the ring ellipse from `ring_tilt_deg`, and all moons in `planet.moons` together in the same composed view
- [x] The previous small rendering inside the information box is replaced by a larger zoom area where the planet body and its surrounding moons are visually readable without leaving the solar system view
- [x] On a 375 px viewport, the layout stacks responsively without horizontal overflow, and the zoomed planet rendering remains visible together with the information content
- [x] `Tillbaka` and Escape restore the normal overview without leaving any stale zoom or layout classes behind
- [x] No JavaScript errors occur when switching between overview mode, zoomed mode, and fullscreen solar system mode

**Key files**
- Modify `frontend/js/components/solar-system-view.js` — replace the current overlay-based detail view with an integrated zoom layout in the same solar system panel; keep the selected planet, moons, and Saturn rings visible while placing the fact panel to the left
- Modify `frontend/css/components/solar-system-view.css` — build the split layout for the zoomed state with a left-aligned information panel on wider viewports, responsive stacking on small screens, and rules that prevent the planet, ring, or moon rendering from being clipped

---

#### Phase F5: Earth-Moon System Detail View — ✅

**Depends on:** Phase F4
**Parallelisable with:** None

**Intended Outcome**

Clicking `Jorden` in the solar system view opens the same integrated detail layout already used for Jupiter and Saturn, but the right-hand visualization now shows the current Earth-Moon system instead of a generic planet-only detail state. The backend provides a dedicated `earth_system` payload with the Moon's current position relative to Earth, and the frontend renders a scaled Earth/Moon diagram with Swedish labels inside the existing two-column Solsystemet detail view.

**Definition of Done**
- [x] `GET /api/v1/planets/visible?lat=55.7&lon=13.4` returns a top-level `earth_system` object containing a nested `moon` object with at least `name_sv`, `x_offset_earth_radii`, `y_offset_earth_radii`, `distance_km`, and `illumination`
- [x] Clicking the Earth dot in the Solsystemet SVG opens the existing detail layout with the title `Jorden` and a right-column Earth/Moon diagram that contains one moon marker labelled `Månen`
- [x] The Moon marker position in the Earth detail diagram is derived from `earth_system.moon.x_offset_earth_radii` and `earth_system.moon.y_offset_earth_radii`, not from a hardcoded fixed orbit angle
- [x] The Earth detail view remains usable on both 375 px and 1200 px viewports, with the information panel and Earth/Moon diagram visible at the same time and no horizontal overflow
- [x] If `earth_system` is missing or null, clicking `Jorden` still opens the detail panel and shows a Swedish fallback message such as `Månens position kunde inte laddas just nu`
- [x] `backend/tests/test_api_planets.py` verifies the `earth_system` response shape and that the Moon offset fields are present in `/api/v1/planets/visible`

**Key files**
- Modify `backend/app/models/planet.py` — add `EarthSystemInfo` / `EarthSystemMoon` models and a top-level `earth_system` field on `PlanetsResponse`
- Create `backend/app/services/planets/earth_system.py` — compute the Moon's current position relative to Earth for the Solsystemet detail view
- Modify `backend/app/api/routes/planets.py` — populate `earth_system` in the `/visible` response
- Modify `backend/tests/test_api_planets.py` — add assertions for the new `earth_system` payload
- Modify `frontend/js/components/solar-system-view.js` — render the Earth/Moon diagram and Swedish fallback state when `Jorden` is clicked
- Modify `frontend/css/components/solar-system-view.css` — style the Earth/Moon detail diagram inside the existing two-column detail layout

---

#### Phase F6: Generic Tracked Spacecraft in Earth Detail View — ✅ 2026-04-06

**Depends on:** Phase F5, Phase G2
**Parallelisable with:** None

**Intended Outcome**

The Earth detail view becomes a reusable host for tracked spacecraft and future Earth-system satellites, using the existing artificial-objects backend as its data source. The first object rendered in this view is `Artemis II`, but the payload and rendering flow are made generic so additional spacecraft or satellites can be added later without redesigning the Earth detail UI. Only objects explicitly marked for the Earth-system detail view are rendered there, so unrelated tracked objects such as ISS remain excluded for now.

**Definition of Done**
- [x] `GET /api/v1/artificial-objects?lat=55.7&lon=13.4` returns a schema where an object can optionally include an `earth_detail_position` payload for Earth-system rendering; in mocked tests, `Artemis II` includes this payload
- [x] Clicking `Jorden` in the Solsystemet view renders `Artemis II` in the Earth detail diagram using the current artificial-objects response, with a Swedish visible label `Artemis II`
- [x] Objects without `earth_detail_position` or without an explicit Earth-detail flag are not rendered in the Earth/Moon diagram, so `ISS` is excluded from this view at this stage
- [x] Hovering or tapping the `Artemis II` marker in the Earth detail view shows a Swedish tooltip with concrete fields such as `Avstånd från jorden` and `Datakälla`
- [x] The Earth detail renderer can display more than one tracked object without layout breakage; in a mocked frontend test with multiple eligible objects, each object produces its own marker and label
- [x] If no object is eligible for the Earth detail view, the Earth/Moon detail still renders and shows a Swedish empty state such as `Inga aktuella rymdfarkoster i jordsystemet`
- [x] `backend/tests/test_api_artificial_objects.py` verifies the new Earth-detail payload for `Artemis II` and confirms that the schema supports additional future spacecraft without breaking existing object fields

**Key files**
- Modify `backend/app/models/artificial_object.py` — add a generic `EarthDetailPosition` model and an optional `earth_detail_position` field on `ArtificialObject`
- Modify `backend/app/services/artificial_objects/horizons_provider.py` — compute Earth-system-relative detail coordinates for eligible spacecraft, currently `Artemis II`
- Modify `backend/app/api/routes/artificial_objects.py` — return the enriched artificial-object schema from the existing endpoint
- Modify `backend/tests/test_api_artificial_objects.py` — add assertions for `earth_detail_position` and future-multi-object compatibility
- Modify `frontend/js/main.js` — pass the latest artificial-object list into `SolarSystemView`
- Modify `frontend/js/components/solar-system-view.js` — render Earth-detail spacecraft markers generically from the artificial-object array and filter to eligible objects only
- Modify `frontend/css/components/solar-system-view.css` — add styling for spacecraft markers, labels, and Earth-detail empty state

---

#### Phase F7: Tidsglidare för Jord-Månvyn

**Depends on:** Phase F5, Phase F6, Phase G2
**Parallelisable with:** None

**Intended Outcome**
The Earth/Moon detail view in the Solsystemet tab gains a time slider that lets the user scrub ±7 days (168 hours) relative to the current moment. Moving the slider updates the Moon's position in the diagram using the same geocentric `compute_earth_system()` pipeline already used for the live view, and refreshes any tracked spacecraft markers (e.g. Artemis II) using a parameterised Horizons geocentric VECTORS call at the selected time. A dedicated backend endpoint `GET /api/v1/earth-detail?lat=&lon=&offset_hours=` serves these time-offset queries, keeping the existing `/visible` and `/artificial-objects` endpoints unchanged. The backend service functions (`compute_earth_system`, `compute_horizons_earth_detail`, and the existing `compute_moon_positions`) are all parameterised on a target `datetime`, so a future phase can reuse them for a similar slider on Jupiter or Saturn without redesigning the service layer. The slider UI itself is limited to the Earth detail view in this phase. The current offset is shown as a Swedish label — "Nu" at the centre position, "X dagar sedan" to the left, and "om X dagar" to the right.

> **Note:** Spacecraft marker positions depend on the published JPL Horizons trajectory window. For Artemis II, positions outside the published trajectory window cause the spacecraft marker to disappear silently; the provider already handles empty Horizons responses with the existing Swedish empty-state message.

**Definition of Done**
- [ ] `GET /api/v1/earth-detail?lat=55.7&lon=13.4&offset_hours=0` returns HTTP 200 with `timestamp`, `earth_system`, and `objects`; `earth_system.moon.x_offset_earth_radii` and `earth_system.moon.y_offset_earth_radii` are non-null floats matching the values from `/api/v1/planets/visible` at the same instant
- [ ] `GET /api/v1/earth-detail?lat=55.7&lon=13.4&offset_hours=-48` returns a `earth_system.moon` with different x/y offsets than the `offset_hours=0` call, confirming the Moon is computed at 2 days in the past
- [ ] `GET /api/v1/earth-detail?lat=55.7&lon=13.4&offset_hours=999` returns HTTP 422 (offset_hours is outside the allowed range of −168 to 168)
- [ ] The Earth detail panel shows a `<input type="range">` slider with endpoint labels "−7 dagar" and "+7 dagar" and a centre tick "Nu"; the slider default position is 0
- [ ] A Swedish label adjacent to the slider reflects the selected offset: "Nu" at 0, "3 dagar sedan" for −72 h, "om 2 dagar" for +48 h (rounding to the nearest day)
- [ ] Moving the slider updates the Moon marker position within 500 ms after debounce (250 ms debounce), without requiring a tab switch or page reload
- [ ] If the Artemis II `earth_detail_position` is present in the response, the spacecraft marker moves to its position at the selected time; if absent (outside trajectory window), the Swedish empty-state "Inga aktuella rymdfarkoster i jordsystemet" is shown without throwing a JavaScript error
- [ ] The slider and labels are visible and usable on both 375 px and 1200 px viewports without horizontal overflow
- [ ] Clicking "Tillbaka" resets the slider state so the next entry into the Earth detail view starts at "Nu"
- [ ] The service functions `compute_earth_system(dt)` and `compute_horizons_earth_detail(dt)` each accept an explicit `datetime` parameter with no hardcoded "now" reference, confirmed by unit-test-style inspection of the function signatures in their respective files

**Key files**
- Create `backend/app/api/routes/earth_detail.py` — `GET /api/v1/earth-detail`; validates `offset_hours` via `Query(ge=-168, le=168, default=0)`; computes `target_dt = datetime.now(UTC) + timedelta(hours=offset_hours)`; calls `compute_earth_system(target_dt)` and a new `compute_horizons_earth_detail(target_dt)` helper; returns `EarthDetailResponse` Pydantic model with `timestamp`, `location`, `earth_system`, and `objects` fields
- Modify `backend/app/services/artificial_objects/horizons_provider.py` — add `compute_horizons_earth_detail(target_dt: datetime) -> List[dict]` that executes a geocentric VECTORS call (`CENTER='500@399'`) at `target_dt` for each `earth_detail: True` registry entry; cache key includes `command_id` and `target_dt` rounded to the nearest 5 minutes; individual object failures are caught and skipped rather than raised; this function is intentionally kept generic so any `earth_detail: True` Horizons object (current or future) is included automatically
- Modify `backend/app/main.py` — import and register `earth_detail.router`
- Modify `frontend/js/api.js` — add `fetchEarthDetail(lat, lon, offsetHours)` calling `GET /api/v1/earth-detail`
- Modify `frontend/js/components/solar-system-view.js` — in `_showDetailOverlay('earth')`, inject a `.solar-system__time-slider-section` block into the left info panel (between the facts grid and the "Tillbaka" button) containing a `<input type="range" min="-168" max="168" step="1" value="0">`, endpoint labels, a "Nu" centre tick, and a dynamic offset label; wire the `input` event (debounced 250 ms) to call an injected callback supplied via `setEarthDetailCallback(fn)` and re-render only the Earth/Moon diagram portion of `svgArea` with the returned data; expose `setEarthDetailCallback(fn)` so `main.js` can wire `fetchEarthDetail()` without coupling the component to the API module
- Modify `frontend/css/components/solar-system-view.css` — add styles for `.solar-system__time-slider-section`, `.solar-system__time-slider-labels` (space-between flex for endpoint labels), `.solar-system__time-slider-current` (centred offset label), and the range input itself; use existing CSS design tokens; ensure the block does not overflow on 375 px viewports

---

### Phase G: Artificial Objects in the Sky Map

This group introduces human-made sky objects as a separate data track in the app, independent from the planets API. G1 establishes a dedicated endpoint, models, and rendering flow for ISS as the first tracked object. G2 extends the same endpoint and sky-map pipeline with Artemis II using a separate mission ephemeris source. This keeps the planets domain clean while allowing future sub-phases to add more satellites, spacecraft, pass forecasts, filtering, and source-specific handling.

#### Phase G1: ISS via Separate Artificial Objects Endpoint

**Depends on:** Phase 5, Phase A3, Phase E3
**Parallelisable with:** None

**Intended Outcome**

The app gains a separate endpoint for artificial sky objects that returns a current sky position for the selected location and time without mixing these objects into the planets API. The first version supports ISS only. The frontend fetches ISS data separately from the planets response and plots it in both the 2D sky map and the 3D dome using the existing refresh and tooltip patterns. The solution keeps models, routes, and tracking logic for artificial objects isolated from the planet stack.

**Definition of Done**
- [x] `GET /api/v1/artificial-objects?lat=55.7&lon=13.4` returns HTTP 200 with top-level fields `timestamp`, `location`, and `objects`
- [x] In mocked backend tests, the `objects` array contains an entry with `name` = `ISS`
- [x] Each object in `objects` contains at minimum `name`, `category`, `altitude_deg`, `azimuth_deg`, `direction`, `is_above_horizon`, and `data_source`, and the schema does not reuse `PlanetPosition`
- [x] `frontend/js/main.js` fetches `/api/v1/artificial-objects` separately from `/api/v1/planets/visible`, and the sky map updates without changing planet cards or sky summary behavior
- [x] `frontend/js/components/sky-map.js` renders ISS in the 2D view at the correct `altitude_deg` and `azimuth_deg`; if `altitude_deg < 0`, the marker is shown with reduced opacity outside the horizon ring
- [x] `frontend/js/components/sky-map-3d.js` renders ISS in the 3D view as a separate sprite/label when `is_above_horizon == true`; if it is below the horizon, it is not rendered in 3D
- [x] Hovering or tapping ISS in the 2D or 3D view shows a tooltip with Swedish UI text such as `Höjd`, `Riktning`, and `Datakälla`
- [x] `backend/tests/test_api_artificial_objects.py` verifies HTTP 200, schema validation, and mocked ISS-source handling

**Key files**
- Create `backend/app/models/artificial_object.py` — Pydantic models for artificial-object response payloads
- Create `backend/app/services/artificial_objects/tracker.py` — fetch and normalize ISS orbital data into local alt/az for the observer
- Create `backend/app/api/routes/artificial_objects.py` — `GET /api/v1/artificial-objects` with validation, error handling, and response schema
- Modify `backend/app/main.py` — register the new artificial-objects router
- Create `backend/tests/test_api_artificial_objects.py` — mock the ISS source and verify response shape and fallback behavior
- Modify `frontend/js/api.js` — add `fetchArtificialObjects(lat, lon)` with Swedish-language error handling
- Modify `frontend/js/main.js` — fetch the artificial-objects endpoint in parallel with planet data, cache the result, and pass it to both sky-map renderers
- Modify `frontend/js/components/sky-map.js` — add `plotArtificialObjects(objects)` for 2D markers, labels, and tooltip targets
- Modify `frontend/js/components/sky-map-3d.js` — add `plotArtificialObjects(objects)` for 3D sprites, labels, and raycaster support
- Modify `frontend/css/components/sky-map.css` — add 2D styles for artificial-object markers and labels
- Modify `frontend/css/components/sky-map-3d.css` — add 3D label and interaction styles for artificial objects

---

#### Phase G2: Artemis II via Mission Ephemeris Source — ✅

**Depends on:** Phase G1
**Parallelisable with:** None

**Intended Outcome**

The artificial-objects endpoint is extended with Artemis II using a mission-specific ephemeris source that is separate from ISS tracking data. The frontend continues to use the same endpoint and rendering flow introduced in G1, but now plots both ISS and Artemis II in the 2D sky map and 3D dome. The solution supports partial-source failure so that one source can fail without breaking the rest of the artificial-objects response or the sky-map UI.

**Definition of Done**
- [x] `GET /api/v1/artificial-objects?lat=55.7&lon=13.4` still returns HTTP 200 after Artemis II support is added, and in mocked backend tests the `objects` array contains entries for both `ISS` and `Artemis II`
- [x] The Artemis II object includes at minimum `name`, `category`, `altitude_deg`, `azimuth_deg`, `direction`, `is_above_horizon`, and `data_source`, using the same response schema introduced in G1
- [x] `frontend/js/components/sky-map.js` renders Artemis II in the 2D view at positions matching its `altitude_deg` and `azimuth_deg`; if it is below the horizon, the marker is shown with reduced opacity outside the horizon ring
- [x] `frontend/js/components/sky-map-3d.js` renders Artemis II in the 3D view as a separate sprite/label when `is_above_horizon == true`; if it is below the horizon, it is not rendered in 3D
- [x] Hovering or tapping Artemis II in the 2D or 3D view shows a tooltip with Swedish UI text such as `Höjd`, `Riktning`, and `Datakälla`
- [x] If the Artemis II source is unavailable, `/api/v1/artificial-objects` still returns HTTP 200 with any remaining valid objects, and the frontend sky map continues to function without JavaScript errors
- [x] `backend/tests/test_api_artificial_objects.py` verifies mocked Artemis II-source ingestion and partial-failure fallback behavior without regressing ISS support

**Key files**
- Modify `backend/app/services/artificial_objects/tracker.py` — add Artemis II mission ephemeris ingestion and normalization into the shared artificial-object model
- Modify `backend/app/api/routes/artificial_objects.py` — extend the endpoint to merge multiple source results and tolerate partial-source failures
- Modify `backend/tests/test_api_artificial_objects.py` — add mocked Artemis II coverage and partial-failure assertions
- Modify `frontend/js/main.js` — continue passing the unified artificial-object list to both sky-map renderers after each refresh
- Modify `frontend/js/components/sky-map.js` — ensure Artemis II renders distinctly alongside ISS in 2D
- Modify `frontend/js/components/sky-map-3d.js` — ensure Artemis II renders distinctly alongside ISS in 3D
- Modify `frontend/css/components/sky-map.css` — add any visual differentiation needed between ISS and Artemis II in the 2D sky map
- Modify `frontend/css/components/sky-map-3d.css` — add any visual differentiation needed between ISS and Artemis II in the 3D sky map

---
