# Planetvis (Planeter) — Architecture

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
  +-- api.js                        |     +-- OpenMeteoClient
                                    +-- VisibilityScorer
                                    +-- CacheService
```

The architecture mirrors norrsken: a stateless FastAPI backend that computes planet positions and visibility on demand, and a vanilla JavaScript frontend that stores location in `localStorage` and passes coordinates to every API call.

## Component Hierarchy

### Backend

```
backend/
  app/
    main.py                       -- FastAPI app, router registration, static file serving
    config.py                     -- Pydantic Settings (defaults, cache TTL, log level)
    models/
      planet.py                   -- PlanetPosition, PlanetVisibility, PlanetsResponse
      weather.py                  -- WeatherData, WeatherResponse (copied from norrsken)
    services/
      planets/
        calculator.py             -- Core ephem-based planet position calculations
      weather/
        base.py                   -- WeatherSourceBase ABC (copied from norrsken)
        metno_client.py           -- Met.no API client (copied from norrsken)
        openmeteo_client.py       -- Open-Meteo API client (copied from norrsken)
      scoring.py                  -- Planet visibility scoring algorithm
      aggregator.py               -- Weather aggregation with fallbacks
      cache_service.py            -- In-memory TTL cache (copied from norrsken)
    api/
      routes/
        planets.py                -- Planet visibility endpoints
        health.py                 -- Health check endpoint (copied from norrsken)
    utils/
      logger.py                   -- Logging setup (copied from norrsken)
      sun.py                      -- Sun position/twilight (copied from norrsken)
      moon.py                     -- Moon position/illumination (adapted from norrsken)
```

### Frontend

```
frontend/
  index.html                      -- Main page
  css/
    tokens.css                    -- Design tokens (adapted from norrsken, planetary theme)
    base.css                      -- Reset and base styles (from norrsken)
    layout.css                    -- Grid layout (from norrsken)
    main.css                      -- Imports all CSS
    components/
      planet-cards.css            -- Planet info card styling (new)
      modal.css                   -- Settings modal (from norrsken)
  js/
    main.js                       -- App entry point, initialization
    api.js                        -- API client for planet endpoints
    location-manager.js           -- Location persistence (adapted from norrsken)
    components/
      planet-cards.js             -- Individual planet visibility cards (new)
      sky-summary.js              -- "Visible tonight" overview (new)
      settings-modal.js           -- Location picker modal (from norrsken)
      map-selector.js             -- Leaflet map (from norrsken)
      tooltip.js                  -- Tooltip utility (from norrsken)
```

## Data Flow

### Request Flow

1. Browser loads page; `LocationManager` reads stored location from `localStorage` (key: `planet_location`)
2. If no stored location, defaults to Södra Sandby (55.7°N, 13.4°E)
3. `APIClient` sends `GET /api/v1/planets/visible?lat=55.7&lon=13.4`
4. Backend `PlanetCalculator` uses `ephem` to compute positions of all naked-eye planets
5. Backend `WeatherAggregator` fetches cloud cover from Met.no (with Open-Meteo fallback)
6. Backend `VisibilityScorer` combines positions, sun/moon state, and weather into per-planet scores
7. Response sent to browser
8. `PlanetCards` component renders one card per planet

### Calculation Pipeline (Backend)

```
Input: (lat, lon, datetime_utc)
  |
  v
ephem.Observer(lat, lon, date)
  |
  +---> ephem.Sun()      --> sun_alt, twilight_phase, sun_penalty
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

The `ephem` library (already used in norrsken for Sun and Moon) provides dedicated classes for all planets:

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
| Altitude | 30 | 0 pts at horizon; peaks at ~45° (30 pts); slight decrease toward zenith |
| Magnitude | 20 | Venus at −4.5 → 20 pts; Saturn at +1 → ~10 pts; scaled inversely |
| Cloud cover | 30 | <25% → 30 pts; 25–50% → 20 pts; 50–75% → 10 pts; >75% → 0 pts |
| Sun penalty | −50 to 0 | Same twilight bands as norrsken's `sun.py` |
| Atmospheric extinction | −10 to 0 | Progressive penalty below 10° altitude |
| Moon proximity | −10 to 0 | Bright, nearby Moon reduces planet contrast |

**Total** = clamp(0, 100, altitude + magnitude + clouds − sun_penalty − extinction − moon_proximity)

A planet is declared **"visible"** when: altitude > 0°, total score > 15, and sun elevation < -6°.

### Key Astronomical Concepts

- **Inferior planets** (Mercury, Venus): orbit inside Earth's orbit; only visible near sunrise or sunset; Mercury is especially elusive.
- **Superior planets** (Mars, Jupiter, Saturn): can appear anywhere along the ecliptic; best at opposition.
- **Apparent magnitude**: lower = brighter. Venus can reach −4.6; Jupiter −2.9; Mars −2.9; Saturn +0.5; Mercury −1.9 to +5.7.
- **Atmospheric extinction**: objects below ~10° are significantly dimmed; below ~5° very difficult.

## State Management

### Backend
- **Stateless**: no per-user session state (same as norrsken)
- **In-memory cache**: weather data cached with TTL (default 30 min); planet calculations are fast pure-CPU so no caching needed
- **Config via `.env`**: default location, cache TTL, log level, Met.no user-agent

### Frontend
- **`localStorage`**: user's selected location persisted under `planet_location` key
- **In-memory**: current planet data, UI state
- **`locationChanged` custom event**: triggers full data reload (same pattern as norrsken)

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
      "transit_time": "2026-02-28T13:45:00Z"
    }
  ]
}
```

### `GET /api/v1/planets/tonight`

Same structure as above but includes visibility windows: when each planet rises, when it enters darkness, when it sets or dawn breaks.
