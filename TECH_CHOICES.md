# Planeter — Technical Choices

## Language and Framework

| Aspect | Choice | Rationale |
|---|---|---|
| Backend language | **Python 3.9+** | `ephem` is Python-native; straightforward async ecosystem |
| Backend framework | **FastAPI** | Async support; auto-generated OpenAPI docs; Pydantic validation; serves static files |
| Frontend | **Vanilla JS / HTML / CSS** | No build step; simple deployment; no framework overhead for this scope |
| Frontend serving | **FastAPI static files** | Single deployment unit; no separate web server needed |

## Astronomical Library

| Aspect | Choice | Rationale |
|---|---|---|
| Planet positions | **ephem (PyEphem) 4.1.5** | Provides `ephem.Mars()`, `ephem.Venus()`, etc. with altitude, azimuth, magnitude, rise/set/transit times. Based on VSOP87 — sufficient precision for naked-eye visibility. Lightweight, no network required. |

### Alternatives Considered

| Library | Verdict | Reason not chosen |
|---|---|---|
| **astronomy-engine** (cosinekitty) | Good alternative | `ephem` gives equivalent results with a smaller footprint |
| **Skyfield** (Brandon Rhodes, successor to PyEphem) | Higher precision | Requires downloading JPL ephemeris files (~30 MB); overkill for visual planet visibility |
| **astropy** | Very comprehensive | Very heavy (~200 MB); far more than needed |

### What `ephem` Provides

- Planet altitude and azimuth from any observer location and time
- Apparent magnitude per planet
- Rise, set, and transit times
- Sun and Moon positions
- Constellation of each planet
- All calculations are local (no network), fast (~1 ms per planet)
- ISS orbit propagation via `ephem.readtle()` (TLE-based SGP4/SDP4 propagation built into PyEphem)

### ISS Orbit Propagation

ISS position is computed with `ephem.readtle(name, line1, line2)` using Two-Line Element (TLE) data fetched from CelesTrak. Alternatives considered:

| Library | Verdict | Reason not chosen |
|---|---|---|
| **sgp4** (Brandon Rhodes) | Pure SGP4 propagator | Adds a new dependency; `ephem.readtle()` wraps the same propagator and is already installed |
| **pyorbital** (Pytroll) | Feature-rich | Heavy dependency; far more than needed for a single topocentric alt/az calculation |
| **ephem.readtle()** | **Chosen** | Already installed; accepts standard 3-line TLE format; returns an `ephem.Body`-compatible object so the existing `ephem.Observer` pattern is reused without changes |

## Weather and Cloud Cover

| Source | Role | Rationale |
|---|---|---|
| **Met.no** (Norwegian Meteorological Institute) | Primary | Free, no API key, excellent Nordic coverage. Provides `cloud_area_fraction`. |
| **Open-Meteo** | Fallback | Free, global, no API key. |
| SMHI | Not included | Can be added as a second fallback in the future |

## Satellite TLE Data

| Source | Role | Rationale |
|---|---|---|
| **CelesTrak** (`celestrak.org`) | ISS TLE provider | Free, no API key required, authoritative NORAD-sourced TLE data. Endpoint: `https://celestrak.org/NORAD/elements/gp.php?CATNR=25544&FORMAT=TLE` |

TLE data is cached in-memory for 2 hours (key: `tle_iss`, TTL: 7200 s). The 2-hour TTL aligns with CelesTrak's acceptable-use policy, which discourages fetching the same element set more frequently than once per two hours. TLE accuracy degrades on the order of days, so a 2-hour cache does not introduce meaningful positional error for a visual-tracking use case.

## JPL Horizons Ephemeris API

| Aspect | Detail |
|---|---|
| Purpose | Observer-based ephemeris for cislunar and deep-space objects where TLEs are inappropriate (e.g. Artemis II Orion spacecraft) |
| Endpoint | `https://ssd.jpl.nasa.gov/api/horizons.api` |
| Query mode | `EPHEM_TYPE=OBSERVER`, `CENTER=coord@399`, `COORD_TYPE=GEODETIC`, `QUANTITIES=4` (apparent azimuth + elevation) |
| Cache TTL | 300 seconds; cache key includes `command_id`, `round(lat, 1)`, and `round(lon, 1)` so that observers at different locations receive correctly positioned ephemerides |
| Concurrency | Capped at 3 simultaneous Horizons requests via `asyncio.Semaphore(3)` |

### Why TLEs Do Not Work for Cislunar Trajectories

SGP4/SDP4 (the propagator used by `ephem.readtle()` and all TLE-based tools) assumes a two-body Earth-centred orbit. Cislunar trajectories such as the Artemis II free-return loop require numerical integration of multiple gravitational bodies (Earth, Moon, Sun). Propagating such a trajectory with SGP4 produces large positional errors within hours. JPL Horizons integrates these trajectories with high-fidelity force models and exposes a REST API for topocentric observer ephemerides, making it the correct source for spacecraft beyond low Earth orbit.

### Adding a New Tracked Object

Add a single dict to `HORIZONS_OBJECTS` in `backend/app/services/artificial_objects/horizons_provider.py`. No other code changes are required:

```python
{
    "name": "My Spacecraft",
    "command_id": "-9999",        # JPL Horizons COMMAND parameter
    "category": "spacecraft",
    "label_sv": "Mitt rymdskepp",  # Swedish display label
    "colour": "#ff9900",           # CSS hex colour for sky-map dot/sprite
    "data_source": "jpl_horizons",
}
```

### Mission Lifetime Handling

When a mission is inactive or the spacecraft has re-entered, the Horizons API returns an empty data block (no rows between `$$SOE` / `$$EOE`). The provider detects this, logs a warning, and omits the object from the response. The endpoint continues to return HTTP 200 with any remaining valid objects.

## Geolocation and Location Picker

| Aspect | Choice | Rationale |
|---|---|---|
| Map library | **Leaflet 1.9.4** (CDN) | Draggable marker, click-to-select, OpenStreetMap tiles. Lightweight and well-supported. |
| Location persistence | **localStorage** (`planet_location` key) | No backend needed; survives page reloads |
| Reverse geocoding | **Nominatim** (via backend proxy) | Free, no API key; proxied through `/api/v1/geocode/reverse` to avoid CORS and rate-limit issues |

## Frontend Libraries

| Library | Version | Source | Purpose |
|---|---|---|---|
| Leaflet | 1.9.4 | CDN (`unpkg.com`) with SRI hashes | Map for location selection |
| Three.js | r170 | Local (`/lib/three.module.min.js`) | 3D sky-dome renderer |
| Three.js OrbitControls | r170 | Local (`/lib/three/addons/`) | Mouse/touch camera control in 3D view |
| Three.js CSS2DRenderer | r170 | Local (`/lib/three/addons/`) | HTML planet labels in 3D view |

Three.js is loaded via an [import map](https://developer.mozilla.org/en-US/docs/Web/HTML/Element/script/type/importmap) so ES modules use bare specifiers (`import * as THREE from 'three'`). Browsers that do not support import maps (IE, old Safari) detect the missing feature at startup and disable the 3D tab. Vendoring Three.js locally avoids CDN downtime risk and removes the need for a build step.

### Why Three.js for the 3D sky view

| Alternative | Verdict | Reason not chosen |
|---|---|---|
| **Babylon.js** | Full-featured | Much larger bundle; API complexity exceeds project needs |
| **Raw WebGL** | Possible | Requires writing shaders, matrix math, and render-loop boilerplate from scratch — significant effort for no benefit |
| **A-Frame** | HTML-centric | Adds a full ECS framework on top of Three.js; unnecessary abstraction layer |
| **Three.js** | **Chosen** | Actively maintained, well-documented, ships a pure ES module build (`three.module.min.js`) that works with import maps and no bundler; wide ecosystem; OrbitControls and CSS2DRenderer are available as drop-in addons |

### Vendored over CDN

Three.js (and its addons) are vendored as local files under `frontend/lib/` rather than loaded from a CDN. Rationale:

- **No runtime CDN dependency** — the app works without network access to third-party servers after the initial page load.
- **Consistent with offline-capable constraint** — the rest of the app (all JS/CSS) is already served from the FastAPI static files mount; Three.js follows the same pattern.
- **SRI hash not required** — the file is already in the repo and served from the same origin, so there is no supply-chain risk.
- **No build step** — the ES module build is consumable directly from the import map without bundling or transpilation.

### Lazy-loading strategy

Three.js is approximately 600 KB minified (~150 KB gzipped). To avoid impacting initial page load, `sky-map-3d.js` is **not** imported statically. Instead, `main.js` loads it dynamically the first time the user activates 3D mode:

```js
const mod = await import('./components/sky-map-3d.js');
skyMap3d = new mod.default(skyMap3dContainerEl);
```

This deferred `import()` means users who never open 3D mode never download Three.js. The `SkyMap3D` instance is cached after the first load so subsequent tab switches do not re-import the module.

## Python Dependencies

Current `backend/requirements.txt`:

```
fastapi==0.109.0
uvicorn[standard]==0.27.0
pydantic==2.5.3
pydantic-settings==2.1.0
httpx==0.26.0
python-dotenv==1.0.0
ephem==4.1.5
pytest==7.4.3
pytest-asyncio==0.21.1
```

No scheduled tasks or file I/O are needed, so heavier dependencies like `apscheduler` and `aiofiles` are intentionally omitted.

## API Surface

| Endpoint | Purpose |
|---|---|
| `GET /api/v1/planets/visible` | Current planet positions and visibility scores |
| `GET /api/v1/planets/tonight` | Tonight's window summary per planet |
| `GET /api/v1/planets/{name}` | Single-planet detail |
| `GET /api/v1/events` | Upcoming astronomical events (conjunctions, oppositions, etc.) for the next 60 days |
| `GET /api/v1/artificial-objects` | Current position of tracked artificial objects (ISS); TLE cached 2 h |
| `GET /api/v1/geocode/reverse` | Nominatim proxy for reverse geocoding |
| `GET /api/v1/health` | Health check |

## Configuration

```bash
# .env (optional — these are the defaults)
LOCATION_LAT=55.7
LOCATION_LON=13.4
LOCATION_NAME=Södra Sandby
CACHE_TTL_WEATHER=1800
LOG_LEVEL=info
METNO_USER_AGENT=PlanetVisibility/1.0 (contact@example.com)
```

All settings are managed through Pydantic `BaseSettings` in `backend/app/config.py`, which reads from the `.env` file and falls back to the defaults shown above.

## Design Theme

| Aspect | Choice |
|---|---|
| Background | Deep space dark: `#050814` (deep), `#0f1322` (surface) |
| Primary accent | Warm gold `#f5c842` |
| Secondary accent | Deep blue `#3b82f6` |
| Status colours | Excellent `#00ffc8` → Good `#a6ff00` → Fair `#ffcc00` → Poor `#ff3366` |
| Per-planet colours | Mercury → grey; Venus → warm yellow; Mars → red-orange; Jupiter → amber; Saturn → gold |

Design tokens are defined as CSS custom properties in `frontend/css/tokens.css` and imported by all component stylesheets.

## Constellation Data Sources

### Why Stellarium + HYG Database?

The constellation stick-figure patterns use two authoritative sources:

**Stellarium v24.4 Modern Skyculture** (`constellationship.fab`)
- Widely-used open-source planetarium software
- Modern astronomical conventions (IAU standard constellation boundaries)
- Actively maintained with regular updates
- GPL-2.0-or-later license (compatible with our project)
- Provides topology: which Hipparcos (HIP) star IDs connect to form each constellation

**HYG Database v3.8** (`hyg_v38.csv`)
- Comprehensive star catalog combining Hipparcos, Yale Bright Star, and Gliese catalogs
- ~120,000 stars with accurate J2000 epoch coordinates
- Public domain license
- Actively maintained (latest release 2024)
- Provides precise RA/Dec coordinates for each HIP star ID

**Alternatives Considered**:
- Hand-authoring coordinates: Error-prone, hard to verify
- Yale BSC only: Missing some dimmer constellation stars
- Older Stellarium formats: Legacy .fab format more stable than new JSON

**Validation**: Constellation coordinates are cross-checked against [frontend/data/bright-stars.json](frontend/data/bright-stars.json) (sourced from SIMBAD) to catch lookup errors. Mismatches >0.1° fail the build.

**File Size**: Downloaded source data is 30-35 MB total and excluded from git (via `.gitignore`). The generated output is ~28 KB for the current 30-constellation subset (Planeter-relevant visible patterns).

**Rebuild Time**: <5 seconds on modern hardware.

**Note on Language**: Constellation names remain in Latin/English (e.g., "Ursa Major", "Orion") following international astronomical convention established by the IAU. Swedish translations are not used in professional astronomy and could cause confusion when cross-referencing with astronomical resources. This is the standard approach used by planetariums worldwide regardless of UI language.

## Deployment

- Backend: `uvicorn` serving FastAPI on port 8000 (`start-backend.sh`)
- Frontend: served as static files by the same FastAPI instance (`start-frontend.sh`)
- No Docker required for development
- No build step: the frontend is plain HTML/CSS/JS served directly
