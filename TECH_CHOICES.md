# Planetvis (Planeter) — Technical Choices

## Language and Framework

| Aspect | Choice | Rationale |
|---|---|---|
| Backend language | **Python 3.9+** | Matches norrsken; `ephem` is Python-native; no context switching |
| Backend framework | **FastAPI** | Matches norrsken; async support; auto-generated OpenAPI docs; Pydantic validation |
| Frontend | **Vanilla JS / HTML / CSS** | Matches norrsken; no build step; simple deployment; sufficient for this scope |
| Frontend serving | **FastAPI static files** | Matches norrsken; single deployment unit; no separate web server needed |

## Astronomical Library

| Aspect | Choice | Rationale |
|---|---|---|
| Planet positions | **ephem (PyEphem) 4.1.5** | Already a dependency in norrsken. Provides `ephem.Mars()`, `ephem.Venus()`, etc. with altitude, azimuth, magnitude, rise/set/transit times. Based on VSOP87 — sufficient precision for naked-eye visibility. Zero new dependencies. |

### Alternatives Considered

| Library | Verdict | Reason not chosen |
|---|---|---|
| **astronomy-engine** (cosinekitty) | Good alternative | `ephem` is already proven in norrsken, same results, zero extra dependencies |
| **Skyfield** (Brandon Rhodes, successor to PyEphem) | Higher precision | Requires downloading JPL ephemeris files (~30 MB); overkill for visual planet visibility |
| **astropy** | Very comprehensive | Very heavy (~200 MB); far more than needed |

### What `ephem` Provides

- Planet altitude and azimuth from any observer location and time
- Apparent magnitude per planet
- Rise, set, and transit times
- Sun and Moon positions (already proven in norrsken)
- Constellation of each planet
- All calculations are local (no network), fast (~1 ms per planet)

## Weather and Cloud Cover

| Source | Role | Rationale |
|---|---|---|
| **Met.no** (Norwegian Meteorological Institute) | Primary | Reused from norrsken. Free, no API key, excellent Nordic coverage. Provides `cloud_area_fraction`. |
| **Open-Meteo** | Fallback | Reused from norrsken. Free, global, no API key. |
| SMHI | Not included initially | Currently returning HTML instead of JSON in norrsken; can be added later if fixed |

Files copied directly from norrsken (no modification):
- `backend/app/services/weather/base.py`
- `backend/app/services/weather/metno_client.py`
- `backend/app/services/weather/openmeteo_client.py`
- `backend/app/models/weather.py`
- `backend/app/services/cache_service.py`

## Geolocation and Location Picker

| Aspect | Choice | Rationale |
|---|---|---|
| Map library | **Leaflet 1.9.4** (CDN) | Reused from norrsken. Draggable marker, click-to-select, OpenStreetMap tiles. |
| Location persistence | **localStorage** (`planet_location` key) | Reused from norrsken pattern; key renamed to avoid collision |
| Reverse geocoding | **Nominatim** (via backend proxy) | Same approach as norrsken's `/api/v1/geocode/reverse` |

Files adapted from norrsken:
- `frontend/js/location-manager.js` — change `STORAGE_KEY` to `planet_location`; remove aurora-specific bounds warning (planets visible globally)
- `frontend/js/components/map-selector.js` — copy as-is
- `frontend/js/components/settings-modal.js` — copy as-is

## Frontend Libraries (CDN, no build step)

| Library | Version | Purpose |
|---|---|---|
| Leaflet | 1.9.4 | Map for location selection |
| Chart.js | 4.x | Future: altitude-over-time charts for each planet |

Chart.js is not required for MVP but can be included from the start to simplify future roadmap work.

## Python Dependencies

No new dependencies beyond norrsken's `requirements.txt`:

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

> Note: `apscheduler` and `aiofiles` from norrsken are not needed (no scheduled tasks or file I/O in the MVP).

## Configuration

```bash
# .env
LOCATION_LAT=55.7
LOCATION_LON=13.4
LOCATION_NAME=Södra Sandby
CACHE_TTL_WEATHER=1800
LOG_LEVEL=info
METNO_USER_AGENT=PlanetVisibility/1.0 (contact@example.com)
```

## Design Theme

| Aspect | Choice | Rationale |
|---|---|---|
| Background | Same dark tokens as norrsken (`#050814`, `#0f1322`) | Night-sky context fits both aurora and planet observation |
| Accent colour | Warm gold / deep blue (replacing aurora green) | Planetary/celestial feel |
| Per-planet colours | Mercury → grey; Venus → warm yellow; Mars → red-orange; Jupiter → amber; Saturn → gold | Matches each planet's real appearance |

## Deployment

Same approach as norrsken:
- Backend: `uvicorn` serving FastAPI on port 8000
- Frontend: served as static files by the same FastAPI instance
- No Docker required for development
- Start scripts: `start-backend.sh`, `start-frontend.sh`
