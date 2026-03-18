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

#### Phase B1: Best Viewing Times

**Depends on:** Phase 5 (API Layer), Phase 6 (Frontend)
**Parallelisable with:** Phase B2, Phase B3

**Intended Outcome**

Each planet card gains a "Bästa observationstid" section showing the optimal viewing window during tonight's darkness. The backend computes, for each planet, the time interval when the planet is above 10° altitude while the sun is below −12° (nautical twilight or darker), and identifies the moment of peak altitude within that window. The `/visible` and `/tonight` endpoints both include this data so the UI always shows it. Planets that never enter the dark window display "Ej synlig ikväll" instead of a time range.

**Definition of Done**
- [ ] `PlanetPosition` model includes `best_time: Optional[str]` (UTC ISO 8601 timestamp of the planet's **peak altitude** within the dark window), `dark_rise_time: Optional[str]`, and `dark_set_time: Optional[str]`
- [ ] The `/visible` endpoint response includes non-null `best_time` for a planet that is above 10° altitude during tonight's dark window
- [ ] A planet that sets before nautical twilight begins has `best_time: null`, `dark_rise_time: null`, `dark_set_time: null`
- [ ] During midnight sun conditions (no dark window), all planets have null best-time fields
- [ ] The planet card shows "Bästa tid: HH:MM–HH:MM" (in Europe/Stockholm time) beneath the existing rise/transit/set row when `dark_rise_time` and `dark_set_time` are non-null
- [ ] The peak time within the window is visually emphasised (bold or accent colour)
- [ ] When all three best-time fields are null, the card shows "Ej synlig ikväll" in `--color-text-muted`
- [ ] The `/tonight` endpoint also populates the best-time fields using its existing night-window sampling logic
- [ ] No regressions in existing planet card layout on 375 px and 1200 px viewports
- [ ] No new API endpoints are introduced; the fields are added to the existing response schema
- [ ] `dark_rise_time`, `dark_set_time`, and `best_time` are stored as UTC ISO 8601 strings, consistent with all other time fields; the existing `formatTime()` helper in `planet-cards.js` handles conversion to Europe/Stockholm for display — no backend timezone conversion is added

**Key files**
- Modify `backend/app/models/planet.py` — add `best_time`, `dark_rise_time`, `dark_set_time` optional string fields to `PlanetPosition`
- Modify `backend/app/api/routes/planets.py` — compute per-planet dark window using existing `_compute_tonight_window()` and `_sample_times()`; find peak altitude time within the window; populate the three new fields on each `PlanetPosition` before returning. For the `/visible` endpoint specifically (which currently computes only an instantaneous snapshot), B1 adds a single call to `_compute_tonight_window()` once per request (not per planet), then for each planet samples its altitude at 15-minute intervals within that window to find the dark rise/set/peak — estimated latency impact is approximately 7 samples × 5 planets ≈ 35 additional `ephem` calls, well under 50 ms
- Modify `frontend/js/components/planet-cards.js` — add "Bästa observationstid" row to `buildCard()` showing the dark window and peak time, or "Ej synlig ikväll" when fields are null
- Modify `frontend/css/components/planet-cards.css` — style the new best-time row, including accent treatment for the peak time

---

#### Phase B2: Observation Descriptions ("What to Look For")

**Depends on:** Phase 6 (Frontend)
**Parallelisable with:** Phase B1, Phase B3

**Intended Outcome**

Each planet card gains a collapsible "Vad ska man leta efter?" section containing a short Swedish-language description of the planet's visual appearance: characteristic colour, typical brightness compared to nearby stars, and how to distinguish it from stars (steady light vs. twinkling). The descriptions are static factual content stored in a frontend data file — no backend changes are needed. The section is collapsed by default to keep cards compact and can be expanded by clicking a toggle.

**Definition of Done**
- [ ] `frontend/js/data/planet-descriptions.js` exists and exports an object keyed by English planet name (Mercury, Venus, Mars, Jupiter, Saturn)
- [ ] Each entry contains at minimum: `color_sv` (string, e.g. "Gulvit"), `appearance_sv` (1–2 sentence description), `identification_tip_sv` (1–2 sentences on how to spot the planet)
- [ ] Each planet card renders a "Vad ska man leta efter?" toggle below the visibility pill
- [ ] Clicking the toggle expands a section showing the planet's colour, appearance, and identification tip
- [ ] Clicking again collapses the section
- [ ] The toggle uses a chevron icon (▸ collapsed, ▾ expanded) and the expanded state is visually distinct
- [ ] The section is collapsed by default on page load
- [ ] Descriptions use correct Swedish astronomical terminology (e.g. "magnitud", "stjärnbild", "fast sken")
- [ ] Descriptions are factually accurate for the current epoch (2020s)
- [ ] Cards for planets below the horizon still show the description toggle (the information is useful regardless of current visibility)
- [ ] No backend changes are required
- [ ] No JavaScript console errors when toggling descriptions rapidly

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
- [ ] `frontend/js/utils.js` exports a `getEquipmentRecommendation(planet)` function returning `null`, `"naked_eye"`, `"binoculars"`, or `"telescope"`
- [ ] The function returns `null` when `planet.is_above_horizon` is false or `planet.visibility_score` is 0
- [ ] The function returns `"binoculars"` when `planet.altitude_deg` is between 5 and 10 (atmospheric extinction zone)
- [ ] The function returns `"binoculars"` when `planet.name === "Mercury"` and `planet.magnitude > 1.5`
- [ ] The function returns `"naked_eye"` for all other visible planets
- [ ] Each planet card renders a badge with the Swedish label: "Blotta ögat" (naked_eye), "Kikare rekommenderas" (binoculars), or "Teleskop" (telescope)
- [ ] The badge uses an appropriate icon or emoji (👁 for naked eye, 🔭 for binoculars/telescope) or a simple text pill
- [ ] The badge is not rendered for planets where the function returns `null`
- [ ] Badge styling uses `--color-text-secondary` background with `--color-text-primary` text, consistent with existing card design tokens
- [ ] No backend changes are required
- [ ] No JavaScript console errors on page load or data refresh

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
- [ ] Three.js r0.174.0 and OrbitControls are vendored as local ES module files under `frontend/lib/`, resolved via a `<script type="importmap">` block in `index.html` — no CDN dependency, no build step required.
- [ ] A view toggle (e.g. standard buttons or a switch) is added to the "Stjärnkarta" tab allowing switching between 2D and 3D views.
- [ ] Selecting "3D Vy" instantiates a full-width immersive 3D canvas instead of the SVG map.
- [ ] A camera placed at the center (0,0,0) with drag-to-look controls allows full 360-degree panning and tilting.
- [ ] A horizon line/plane is drawn to define where the sky meets the earth.
- [ ] A celestial grid (lines marking azimuth every 30° to 45°, and lines for altitude at 30° and 60°) is drawn natively in 3D space.
- [ ] Changing screen size / rotating a mobile device resizes the 3D canvas while maintaining a correct aspect ratio.
- [ ] The Three.js render loop is started when the 3D view becomes active and cleanly stopped via `renderer.setAnimationLoop(null)` when the user switches to 2D view or navigates away from the Stjärnkarta tab.
- [ ] The user's 2D/3D view preference is stored in `localStorage` and restored on page load.
- [ ] Mobile touch controls use single-finger drag for rotation only; pinch-zoom is disabled (fixed-radius sphere view).
- [ ] The 2D SVG sky map remains the default view and the accessible fallback; the 3D canvas element has `aria-hidden="true"` with a visible or screen-reader-accessible hint pointing users to the 2D view.

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

