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

## Weather and Cloud Cover

| Source | Role | Rationale |
|---|---|---|
| **Met.no** (Norwegian Meteorological Institute) | Primary | Free, no API key, excellent Nordic coverage. Provides `cloud_area_fraction`. |
| **Open-Meteo** | Fallback | Free, global, no API key. |
| SMHI | Not included | Can be added as a second fallback in the future |

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
| Three.js | r168 | Local (`/lib/three.module.min.js`) | 3D sky-dome renderer |
| Three.js OrbitControls | r168 | Local (`/lib/three/addons/`) | Mouse/touch camera control in 3D view |
| Three.js CSS2DRenderer | r168 | Local (`/lib/three/addons/`) | HTML planet labels in 3D view |

Three.js is loaded via an [import map](https://developer.mozilla.org/en-US/docs/Web/HTML/Element/script/type/importmap) so ES modules use bare specifiers (`import * as THREE from 'three'`). Browsers that do not support import maps (IE, old Safari) detect the missing feature at startup and disable the 3D tab. Vendoring Three.js locally avoids CDN downtime risk and removes the need for a build step.

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

## Deployment

- Backend: `uvicorn` serving FastAPI on port 8000 (`start-backend.sh`)
- Frontend: served as static files by the same FastAPI instance (`start-frontend.sh`)
- No Docker required for development
- No build step: the frontend is plain HTML/CSS/JS served directly
