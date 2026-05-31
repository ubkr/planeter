# Observation Tips & Astronomical Events (Phases B1–B12)

**Status:** Completed

**Phases included:** B1 (Best Viewing Times), B2 (Observation Descriptions), B3 (Equipment Guidance), B4 (Astronomical Event Alerts), B5 (Kommande Events Timeline), B6 (Event Detail — Observation Guidance), B7 (Location-Based Event Filtering), B8 (Next Visible Time for Hidden Planets), B9 (6-Month Observation Forecast), B10 (Twilight-Window Forecast for Mercury & Venus), B11 (Sun & Moon Rise/Set Times), B12 (24-Hour Altitude Timeline)

---

## Intended Outcome (User Perspective)

Planet cards become rich observation guides. Each card shows the best window to observe the planet tonight ("Bästa tid: 21:30–23:45") with the peak time highlighted. A collapsible "Vad ska man leta efter?" section describes the planet's colour, brightness, and how to tell it apart from stars. A small badge tells the user whether they need just their eyes or binoculars.

Planets that aren't visible right now collapse into compact cards showing only their name, status, and when they'll next be visible ("Nästa synlig: 22:15"). A "Nästa bra tillfälle" section on each card forecasts the next geometrically ideal observation opportunity up to six months ahead, formatted in Swedish with month names and local times.

Alert banners appear when notable events are happening — conjunctions, oppositions, planet alignments, Venus at its brightest, or the Moon occluding a planet. A third "Kommande" tab shows a scrollable 60-day timeline of upcoming events grouped by month, with how many days away each event is. Clicking an event row reveals where to look in the sky and the best time window. Events that are geometrically unobservable from the user's location are automatically filtered out.

The sky summary shows today's sunrise/sunset and moonrise/moonset times. A fifth "Höjdkurva" tab shows a 24-hour SVG chart of how every planet, the Sun, and the Moon rise and set, making it easy to see when the sky will be darkest and which planets will be at their highest.

---

## Definition of Done

### Phase B1 — Best Viewing Times
- `PlanetPosition` model includes `best_time`, `dark_rise_time`, and `dark_set_time` (UTC ISO 8601 or null)
- The `/visible` endpoint returns non-null `best_time` for a planet above 10° altitude during tonight's dark window
- A planet that sets before nautical twilight begins has null best-time fields
- During midnight sun conditions all planets have null best-time fields
- Planet card shows "Bästa tid: HH:MM–HH:MM" (Europe/Stockholm time) when dark window fields are non-null
- Peak time within the window is visually emphasised (bold or accent colour)
- When all three best-time fields are null, card shows "Ej synlig ikväll" in `--color-text-muted`
- No regressions in existing planet card layout on 375 px and 1200 px viewports

### Phase B2 — Observation Descriptions
- `frontend/js/data/planet-descriptions.js` exists and exports an object keyed by English planet name
- Each entry contains `color_sv`, `appearance_sv`, and `identification_tip_sv`
- Each planet card renders a "Vad ska man leta efter?" toggle
- Clicking the toggle expands a section showing the planet's colour, appearance, and identification tip
- Clicking again collapses the section
- The toggle uses a chevron icon (▸ collapsed, ▾ expanded)
- Section is collapsed by default on page load
- Descriptions use correct Swedish astronomical terminology
- Cards for planets below the horizon still show the description toggle
- No backend changes required; no JavaScript console errors when toggling rapidly

### Phase B3 — Equipment Guidance
- `frontend/js/utils.js` exports `getEquipmentRecommendation(planet)` returning `null`, `"naked_eye"`, `"binoculars"`, or `"telescope"`
- Returns `null` when `planet.is_above_horizon` is false or `planet.visibility_score` is 0
- Returns `"binoculars"` when `planet.altitude_deg` is between 5 and 10 (atmospheric extinction zone)
- Returns `"binoculars"` when `planet.name === "Mercury"` and `planet.magnitude > 1.5`
- Returns `"naked_eye"` for all other visible planets
- Each planet card renders a badge: "Blotta ögat", "Kikare rekommenderas", or "Teleskop"
- Badge not rendered when function returns `null`
- No backend changes required; no JavaScript console errors

### Phase B4 — Astronomical Event Alerts
- `AstronomicalEvent` Pydantic model includes `event_type`, `bodies`, `date`, `separation_deg`, `elongation_deg`, `description_sv`
- `PlanetsResponse` includes `events: List[AstronomicalEvent]` (default empty list)
- `detect_events(lat, lon, start_dt, end_dt)` exports with six detector sub-functions (conjunction, opposition, mercury_elongation, alignment, venus_brilliancy, moon_occultation)
- The `/visible` and `/tonight` endpoints call `detect_events()` inside try/except fallback
- `EventAlerts` class renders a banner for each event; banner hidden when array is empty
- Active events use `--color-status-excellent` styling; upcoming use `--color-status-fair`
- Sky map `plotBodies()` draws dashed lines for conjunctions/occultations and opposition glow
- No regressions in existing endpoint response schemas

### Phase B5 — Kommande Events Timeline
- `GET /api/v1/events?lat=&lon=` endpoint exists with 1-hour cache returning `EventsResponse` over 60-day window
- `frontend/js/components/events-timeline.js` renders month-grouped rows with days-away badges and skeleton loading state
- `frontend/js/api.js` exports `fetchEvents(lat, lon)`
- "Kommande" tab button (`#tabEvents`) and `#panelEvents` panel exist in `index.html`
- `tab-nav.js` refactored to generic N-tab loop; dispatches `tabChanged` custom event
- Events lazy-loaded on first switch; `eventsLoaded` flag resets on location change
- Empty state shows "Inga speciella händelser de närmaste 60 dagarna 🌙" when response is empty
- No regressions in existing planet cards or sky map tabs

### Phase B6 — Event Detail — Observation Guidance
- `AstronomicalEvent` model includes optional fields: `best_time_start`, `best_time_end`, `altitude_deg`, `azimuth_deg`, `compass_direction_sv`, `observation_tip_sv`
- Event detection pipeline computes sky position and optimal viewing window for each event type
- Events below horizon or during daylight carry a Swedish explanatory note in `observation_tip_sv`
- Clicking/tapping an event in the Kommande timeline reveals detail content without full-page navigation
- Clicking/tapping an event alert card reveals the same detail content
- Detail content is keyboard-accessible (Enter/Space to toggle) with appropriate ARIA attributes
- No regressions in existing event rendering, planet cards, or sky map tabs

### Phase B7 — Location-Based Event Filtering
- `GET /api/v1/events?lat=55.7&lon=13.4` returns no event objects where `altitude_deg` is negative
- Events where `altitude_deg` is `null` are still present (conservative pass-through)
- Switching to a southern hemisphere location produces a different events list for the same date
- When all events are filtered out, returns `{"events": [], ...}` with HTTP 200
- The 1-hour cache stores the already-filtered list

### Phase B8 — Next Visible Time for Hidden Planets
- `PlanetPosition` includes `next_visible_time: Optional[str]` (UTC ISO 8601 or null)
- `/visible` endpoint computes `next_visible_time` for every planet where `is_visible == False` by sampling next 24 hours at 15-minute intervals
- A planet that never meets both `altitude_deg > 10` and `sun_altitude < -12` within 24 hours has `next_visible_time: null`
- A currently visible planet has `next_visible_time: null`
- Compact planet cards show a tooltip on the visibility pill: "Nästa synlig: HH:MM" or "Ej synlig nästa 24h"
- Full (non-compact) planet cards do not show next-visible-time information
- Tooltip reuses existing `tooltip.js` component
- No regressions in existing planet card layout on 375 px and 1200 px viewports
- Sampling adds no more than 100 ms to the `/visible` endpoint median latency

### Phase B9 — 6-Month Observation Forecast
- `backend/app/services/planets/forecast.py` exports `compute_next_good_observation(planet_name, lat, lon, start_dt)` scanning up to 180 nights ahead
- Scanner evaluates one sample per night at the planet's peak-altitude moment within nautical darkness; midnight-sun nights are skipped
- Geometric quality score considers altitude (min 15°), apparent magnitude, and moon angular separation
- `PlanetPosition` includes `next_good_observation: Optional[NextGoodObservation]` with fields: `date`, `start_time`, `end_time`, `peak_time`, `peak_altitude_deg`, `magnitude`, `quality_score`
- `/visible` endpoint calls the forecast for each planet and populates `next_good_observation`
- Forecast results are cached per `(lat_rounded, lon_rounded)` with 6-hour TTL
- A planet in excellent current conditions returns today's date as `next_good_observation`
- Mercury and Venus have a lower quality threshold than outer planets
- Each planet card renders a "Nästa bra tillfälle" row with the date as "DD månad" in Swedish and a time window
- When `next_good_observation` is null, card shows "Inga bra tillfällen kommande 6 mån" in muted colour
- Date display uses Swedish month names
- No regressions on 375 px and 1200 px viewports
- Forecast completes within 500 ms for all five planets combined

### Phase B10 — Twilight-Window Forecast for Mercury & Venus
- `forecast.py` exports `_compute_twilight_window_for_night(lat, lon, night_dt, is_evening)` returning the twilight window boundaries
- `compute_next_good_observation()` branches: Mercury and Venus use twilight windows; Mars, Jupiter, Saturn use existing nautical-darkness logic
- Mercury at 20° altitude during evening civil twilight returns a recommendation with correct start/end times
- Venus at 15° altitude during morning nautical twilight returns a morning window recommendation
- Mars at 30° altitude during nautical darkness continues to use the existing dark window unchanged
- When both twilight windows qualify on the same night, the higher `quality_score` wins; ties favour evening
- Forecast cache keys remain unchanged
- No regression in forecast performance: all five planets complete within 500 ms

### Phase B11 — Sun & Moon Rise/Set Times in Sky Summary
- `SunInfo` in `/api/v1/planets/visible` response includes `today_rise_time`, `today_set_time`, `next_rise_time`, `next_set_time`
- `MoonInfo` in the same response includes the same four time fields
- Sky summary renders two labelled blocks with headings `Solen` and `Månen` to the right of existing summary on 1200 px viewport
- Sky summary stacks the blocks below existing content on 375 px viewport without horizontal overflow
- `backend/tests/test_api_planets.py` verifies the new `SunInfo` and `MoonInfo` time fields in `/visible` response

### Phase B12 — 24-Hour Altitude Timeline
- `GET /api/v1/planets/timeline?lat=55.7&lon=13.4` returns HTTP 200 with fields `timestamp`, `location`, `sample_interval_minutes`, and `series` containing exactly seven objects (Mercury, Venus, Mars, Jupiter, Saturn, Sun, Moon)
- Each `series[*].samples` covers next 24 hours in 15-minute intervals; first sample within 15 minutes of timestamp, last sample between 23h45m and 24h15m later
- A "Höjdkurva" main-navigation tab is visible and activates `#panelAltitudeTimeline` using the same ARIA tab pattern
- Chart renders a horizon line at 0°, a y-axis in degrees, and an x-axis from "Nu" to "+24 h"
- Lines for all seven bodies use existing colour tokens
- Chart remains readable on 375 px without horizontal scroll; on 1200 px no line is clipped
- `backend/tests/test_api_planets.py` verifies response schema, seven series names, and 24-hour interval coverage
