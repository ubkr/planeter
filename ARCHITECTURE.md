# Planeter — Architecture

## High-Level System Design

```
Browser (Vanilla JS)              Python FastAPI Backend
============================      ============================

index.html                        /api/v1/planets/visible
  +-- location-manager.js    -->    +-- PlanetCalculator (ephem)
  +-- map-selector.js               +-- SunCalculator (ephem)
  +-- settings-modal.js             +-- MoonCalculator (ephem)
  +-- planet-cards.js               +-- WeatherAggregator
  +-- sky-summary.js                |     +-- MetNoClient
  +-- sky-map.js                    |     +-- OpenMeteoClient
  +-- sky-map-3d.js                 +-- VisibilityScorer
  +-- events-timeline.js            +-- CacheService
  +-- api.js
```

A stateless FastAPI backend computes planet positions and visibility on demand. The vanilla JavaScript frontend stores the user's location in `localStorage` and passes coordinates to every API call.

## Component Hierarchy

### Backend

```
backend/
  app/
    main.py                       -- FastAPI app, router registration, static file serving
    config.py                     -- Pydantic Settings (defaults, cache TTL, log level)
    models/
      planet.py                   -- PlanetPosition, PlanetVisibility, PlanetsResponse, EventsResponse
      weather.py                  -- WeatherData, WeatherResponse
    services/
      planets/
        calculator.py             -- Core ephem-based planet position calculations
        events.py                 -- Astronomical event detection (conjunctions, oppositions, etc.)
      weather/
        base.py                   -- WeatherSourceBase ABC
        metno_client.py           -- Met.no API client
        openmeteo_client.py       -- Open-Meteo API client
      scoring.py                  -- Planet visibility scoring algorithm
      aggregator.py               -- Weather aggregation with fallbacks
      cache_service.py            -- In-memory TTL cache
    api/
      routes/
        planets.py                -- Planet visibility endpoints
        events.py                 -- Upcoming astronomical events endpoint
        geocode.py                -- Nominatim reverse-geocoding proxy
        health.py                 -- Health check endpoint
    utils/
      logger.py                   -- Logging setup
      sun.py                      -- Sun position/twilight
      moon.py                     -- Moon position/illumination
```

### Frontend

```
frontend/
  index.html                      -- Main page; import map for Three.js bare specifiers
  css/
    tokens.css                    -- CSS custom properties: colours, spacing, typography
    base.css                      -- Reset and base styles
    layout.css                    -- App grid layout
    main.css                      -- Imports all CSS
    components/
      planet-cards.css            -- Planet info card styling
      modal.css                   -- Settings modal
      sky-map.css                 -- 2D SVG sky map
      sky-map-3d.css              -- 3D sky-dome viewer
      tab-nav.css                 -- Tab navigation bar
      events-timeline.css         -- Upcoming events timeline
      event-alerts.css            -- Event alert banners
  js/
    main.js                       -- App entry point, tab orchestration
    api.js                        -- API client (planets, events, geocode)
    location-manager.js           -- Location persistence (localStorage)
    astro-projection.js           -- Alt/az → Cartesian projection utilities
    utils.js                      -- Shared formatting/helper utilities
    data/
      planet-descriptions.js      -- Static Swedish-language planet descriptions
    components/
      planet-cards.js             -- Individual planet visibility cards
      sky-summary.js              -- "Visible tonight" summary banner
      sky-map.js                  -- 2D SVG polar sky chart
      sky-map-3d.js               -- 3D WebGL sky-dome (Three.js)
      events-timeline.js          -- Upcoming astronomical events timeline
      event-alerts.js             -- Event alert banners (Planeter tab)
      tab-nav.js                  -- Tab navigation component
      settings-modal.js           -- Location picker modal (Leaflet)
      map-selector.js             -- Leaflet map widget
      tooltip.js                  -- Tooltip utility
  lib/
    three.module.min.js           -- Three.js r170 (vendored, ES module)
    three/addons/
      controls/OrbitControls.js   -- Mouse/touch camera orbit
      renderers/CSS2DRenderer.js  -- HTML overlay labels in 3D view
```

## Sky Map Components

### SkyMap (2D)

`frontend/js/components/sky-map.js` renders a polar SVG projection of the sky dome. The zenith is at the centre; the horizon is the outer ring; North (azimuth 0°) is at the top; East is to the right (compass-view convention). Public methods:

- `render()` — builds the static SVG grid (altitude rings, cardinal labels). Idempotent.
- `plotBodies(planets, sun, moon, events)` — adds/replaces planet, Sun, and Moon dots with tooltip labels. Also draws conjunction lines and opposition glows from the `events` array.
- `plotConstellations(constellationData, lat, lon, utcTimestamp)` — draws constellation stick-figure lines and IAU labels behind the body layer.

Both `plotBodies` and `plotConstellations` are safe to call before `render()` — arguments are stored and replayed once the SVG grid is ready.

### SkyMap3D (3D)

`frontend/js/components/sky-map-3d.js` renders an immersive WebGL sky dome using Three.js. The camera sits at the origin (inside-out sphere), OrbitControls let the user drag to look around, and the render loop is started/stopped on tab activation/deactivation.

**Public interface:**

- `activate()` — builds the scene on first call (renderer, camera, controls, hemisphere geometry, alt-azimuth grid); on subsequent calls resizes the canvas and restarts the render loop.
- `deactivate()` — stops the render loop (keeps GPU resources alive for fast resume).
- `dispose()` — full teardown: stops the loop, releases GPU resources, removes canvas from DOM.
- `plotBodies(planets, sun, moon, events)` — plots planets, Sun, and Moon as canvas-texture glow sprites. Each body also gets a CSS2D HTML label. Bodies with altitude < 0° are not rendered. Safe to call before `activate()` — arguments are stored and replayed.
- `plotConstellations(constellationData, lat, lon, utcTimestamp)` — converts RA/Dec star endpoints to alt/az (via `raDecToAltAz`), then to Three.js Cartesian space (via `altAzToCartesian`). All visible constellation segments are batched into a single `THREE.LineSegments` draw call. IAU abbreviation labels are rendered as CSS2D overlays. Must be called after `activate()` — data is dropped with a console warning if the scene is not yet initialised.

**CSS2DRenderer overlay:**

`CSS2DRenderer` produces an HTML `<div>` that is positioned `absolute`, anchored at `top: 0; left: 0`, sized to match the WebGL canvas, and has `pointerEvents: none`. It is appended after the WebGL `<canvas>` inside the same container element (which is set to `position: relative` if it is not already). The overlay renders CSS2D label `<div>` elements that follow 3D scene positions without interfering with pointer events on the canvas.

**`altAzToCartesian` coordinate convention:**

`frontend/js/astro-projection.js` exports `altAzToCartesian(altitudeDeg, azimuthDeg, radius)`. Coordinate system: **y-up**, **north along −z**, **east along +x**. The formula is:

```
x =  radius * cos(alt) * sin(az)
y =  radius * sin(alt)
z = -radius * cos(alt) * cos(az)
```

This maps altitude 0° / azimuth 0° (horizon-North) to the −z axis, and altitude 90° (zenith) to the +y axis, consistent with Three.js scene orientation.

### 2D/3D Component Hierarchy (Stjärnkarta tab)

```
SkyMap tab (panelSkyMap)
  +-- .skymap-view-toggle         -- 2D / 3D toggle buttons
  +-- #skyMapContainer            -- SkyMap (2D SVG)
  |     +-- <svg>                 -- polar projection grid
  |           +-- .sky-map-constellations  -- constellation lines + IAU labels
  |           +-- .sky-map-bodies          -- planet/sun/moon dots + text labels
  +-- #skyMap3dContainer          -- SkyMap3D (Three.js WebGL)
        +-- <canvas>              -- WebGL renderer output (aria-hidden)
        +-- CSS2DRenderer <div>   -- HTML label overlay (pointerEvents: none)
              +-- .sky-map-3d-label  -- per-body CSS2D labels
              +-- .sky-map-3d-constellation-label  -- IAU abbreviation labels
```

`SkyMap3D` is not imported at page load. `main.js` lazy-loads it via `await import('./components/sky-map-3d.js')` the first time the user activates 3D mode, so Three.js (~150 KB gzipped) does not affect initial page load.

## Data Flow

### Request Flow

1. Browser loads page; `LocationManager` reads stored location from `localStorage` (key: `planet_location`)
2. If no stored location, defaults to Södra Sandby (55.7°N, 13.4°E)
3. `APIClient` sends `GET /api/v1/planets/visible?lat=55.7&lon=13.4`
4. Backend `PlanetCalculator` uses `ephem` to compute positions of all naked-eye planets
5. Backend `WeatherAggregator` fetches cloud cover from Met.no (with Open-Meteo fallback)
6. Backend `VisibilityScorer` combines positions, sun/moon state, and weather into per-planet scores
7. Response sent to browser; `PlanetCards` and `SkySummary` components render the Planets tab
8. When the user opens the **Stjärnkarta** tab, `SkyMap` (2D) or `SkyMap3D` (Three.js) renders planet positions
9. When the user opens the **Kommande** tab, `APIClient` fetches `GET /api/v1/events` and `EventsTimeline` renders the next 60 days of conjunctions, oppositions, etc.

### Calculation Pipeline (Backend)

```
Input: (lat, lon, datetime_utc)
  |
  v
ephem.Observer(lat, lon, date)
  |
  +---> ephem.Sun()      --> sun_alt, twilight_phase, sun_penalty, limiting_magnitude
  +---> ephem.Moon()     --> moon_alt, moon_illumination, moon_az
  +---> ephem.Mercury()  --> alt, az, mag, rise, set, transit
  +---> ephem.Venus()    --> alt, az, mag, rise, set, transit
  +---> ephem.Mars()     --> alt, az, mag, rise, set, transit
  +---> ephem.Jupiter()  --> alt, az, mag, rise, set, transit
  +---> ephem.Saturn()   --> alt, az, mag, rise, set, transit
  |
  v
Weather API --> cloud_cover_percent
  |
  v
VisibilityScorer:
  For each planet:
    - above_horizon           = (alt > 0)
    - altitude_score          = f(alt)           # peaks around 45 degrees
    - magnitude_score         = f(mag)           # brighter (lower mag) = higher score
    - sun_penalty             = f(sun_alt)       # daylight/twilight penalty
    - cloud_penalty           = f(cloud_cover)   # overcast = not visible
    - extinction_penalty      = f(alt)           # low altitude = atmospheric dimming
    - moon_proximity_penalty  = f(angle_to_moon, moon_illumination)
    - visibility_score        = clamp(0, 100, sum_of_components)
    - is_visible              = above_horizon AND score > threshold AND dark_enough
  |
  v
Response JSON
```

## Planet Visibility Calculation Details

### Using `ephem` for Planet Positions

The `ephem` library provides dedicated classes for all naked-eye planets:

```python
observer = ephem.Observer()
observer.lat  = str(lat)   # ephem expects string degrees
observer.lon  = str(lon)
observer.date = utc_datetime
observer.pressure = 0      # disable atmospheric refraction for raw altitude

mars = ephem.Mars()
mars.compute(observer)

altitude_rad  = float(mars.alt)   # radians — convert to degrees for display
azimuth_rad   = float(mars.az)    # radians
magnitude     = float(mars.mag)   # apparent magnitude

rise_time     = observer.next_rising(mars)
set_time      = observer.next_setting(mars)
transit_time  = observer.next_transit(mars)
```

### Visibility Scoring Algorithm (per planet)

| Component | Max Points | Logic |
|---|---|---|
| Altitude | 40 | 0 pts at horizon; linear ramp to 40 pts at 45°; clamped at 40 pts for higher altitudes |
| Magnitude | 25 | Venus at −4.5 → 25 pts; Saturn at +1 → ~10 pts; scaled inversely |
| Cloud cover | 35 | <25% → 35 pts; 25–50% → 23 pts; 50–75% → 12 pts; ≥75% → 0 pts |
| Sun penalty | −50 to 0 | Continuous magnitude-aware function of sun altitude. Base penalty decreases smoothly from 50 (daylight) to 0 (darkness, sun < −18°). Effective penalty scaled by planet brightness relative to sky limiting magnitude (Schaefer 1993): bright planets (Venus, Jupiter) are penalised less during twilight than faint ones. |
| Atmospheric extinction | −10 to 0 | Progressive penalty below 10° altitude |
| Moon proximity | −10 to 0 | Bright, nearby Moon reduces planet contrast |

**Total** = clamp(0, 100, altitude + magnitude + clouds − sun_penalty − extinction − moon_proximity)

A planet is declared **"visible"** when: altitude > 0, total score > 15, and apparent magnitude < sky limiting magnitude for the current sun altitude. The limiting magnitude is a continuous function of sun depression angle, ranging from approximately −5.0 at sunset to +6.5 in full darkness (Schaefer 1993, "Astronomy and the Limits of Vision", *Vistas in Astronomy* Vol. 36, pp. 311–361).

### Key Astronomical Concepts

- **Inferior planets** (Mercury, Venus): orbit inside Earth's orbit; only visible near sunrise or sunset; Mercury is especially elusive.
- **Superior planets** (Mars, Jupiter, Saturn): can appear anywhere along the ecliptic; best at opposition.
- **Apparent magnitude**: lower = brighter. Venus can reach −4.6; Jupiter −2.9; Mars −2.9; Saturn +0.5; Mercury −1.9 to +5.7.
- **Atmospheric extinction**: objects below ~10° are significantly dimmed; below ~5° very difficult.
- **Twilight limiting magnitude**: the faintest stellar magnitude visible to the naked eye as a function of sun depression angle. Bright objects like Venus (mag −4) become visible well before civil twilight ends, while faint naked-eye stars require full astronomical darkness.

## State Management

### Backend
- **Stateless**: no per-user session state
- **In-memory cache**: weather data cached with TTL (default 30 min); events cached for 1 hour keyed by date + rounded coordinates; planet calculations are fast pure-CPU so not cached
- **Config via `.env`**: default location, cache TTL, log level, Met.no user-agent

### Frontend
- **`localStorage`**: user's selected location persisted under `planet_location` key
- **In-memory**: current planet data, UI state
- **`locationChanged` custom event**: triggers full data reload across all tabs

## API Response Schema

### `GET /api/v1/planets/visible`

```json
{
  "timestamp": "2026-02-28T22:00:00Z",
  "location": { "lat": 55.7, "lon": 13.4, "name": "Södra Sandby" },
  "sun": { "elevation_deg": -25.3, "twilight_phase": "darkness" },
  "moon": { "illumination": 0.45, "elevation_deg": 32.1, "azimuth_deg": 180.0 },
  "weather": { "cloud_cover": 15.0, "source": "met_no" },
  "planets": [
    {
      "name": "Venus",
      "altitude_deg": 25.3,
      "azimuth_deg": 245.0,
      "direction": "WSW",
      "magnitude": -4.2,
      "constellation": "Pisces",
      "is_visible": true,
      "visibility_score": 85,
      "rise_time": "2026-02-28T07:15:00Z",
      "set_time": "2026-02-28T20:30:00Z",
      "transit_time": "2026-02-28T13:45:00Z",
      "next_visible_time": null
    }
  ]
}
```

### `GET /api/v1/planets/tonight`

Same structure as above but includes visibility windows: when each planet rises, when it enters darkness, when it sets or dawn breaks.

### `GET /api/v1/events`

```json
{
  "location": { "lat": 55.7, "lon": 13.4, "name": "Södra Sandby" },
  "timestamp": "2026-03-16T10:00:00Z",
  "events": [
    {
      "event_type": "opposition",
      "bodies": ["Mars"],
      "date": "2026-04-15T00:00:00Z",
      "description_sv": "Mars i opposition – bästa tillfället att observera planeten",
      "elongation_deg": 178.5,
      "days_away": 30,
      "event_icon": "opposition",
      "best_time_start": "2026-04-15T21:30:00Z",
      "best_time_end": "2026-04-15T23:45:00Z",
      "altitude_deg": 42.3,
      "azimuth_deg": 195.7,
      "compass_direction_sv": "syd",
      "observation_tip_sv": "Planeten är synlig hela natten och når sin högsta punkt mot syd på 42° höjd."
    }
  ]
}
```

Covers a 60-day look-ahead window. Events are cached for 1 hour, keyed on rounded coordinates and today's date.

### `GET /api/v1/geocode/reverse`

Proxy to Nominatim. Accepts `lat` and `lon` query parameters; returns a display name string. Proxying through the backend avoids browser CORS restrictions and rate-limit attribution issues.
