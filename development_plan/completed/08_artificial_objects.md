# Artificial Objects in the Sky Map (Phases G1–G2)

**Status:** Completed

**Phases included:** G1 (ISS via Separate Artificial Objects Endpoint), G2 (Artemis II via Mission Ephemeris Source)

---

## Intended Outcome (User Perspective)

Both the 2D and 3D sky maps now show human-made objects alongside the natural bodies. ISS appears as a labelled marker on the sky map at its current position. When ISS is above the horizon the user can hover or tap it to see a Swedish tooltip with its altitude, direction, and data source. Artemis II is shown alongside ISS using data from its mission ephemeris. If Artemis II's trajectory data is unavailable, the sky map continues to work normally and only ISS is shown. The planets API and planet cards are completely unaffected by this addition.

---

## Definition of Done

### Phase G1 — ISS via Separate Artificial Objects Endpoint
- `GET /api/v1/artificial-objects?lat=55.7&lon=13.4` returns HTTP 200 with top-level fields `timestamp`, `location`, and `objects`
- In mocked backend tests, the `objects` array contains an entry with `name` = `ISS`
- Each object contains at minimum `name`, `category`, `altitude_deg`, `azimuth_deg`, `direction`, `is_above_horizon`, and `data_source`; schema does not reuse `PlanetPosition`
- `frontend/js/main.js` fetches `/api/v1/artificial-objects` separately from `/api/v1/planets/visible`; sky map updates without changing planet cards or sky summary behaviour
- `sky-map.js` renders ISS in the 2D view at the correct `altitude_deg` and `azimuth_deg`; if `altitude_deg < 0`, marker shown with reduced opacity outside the horizon ring
- `sky-map-3d.js` renders ISS in the 3D view as a sprite/label when `is_above_horizon == true`; if below the horizon, not rendered in 3D
- Hovering or tapping ISS in the 2D or 3D view shows a tooltip with Swedish text including `Höjd`, `Riktning`, and `Datakälla`
- `backend/tests/test_api_artificial_objects.py` verifies HTTP 200, schema validation, and mocked ISS-source handling

### Phase G2 — Artemis II via Mission Ephemeris Source
- `GET /api/v1/artificial-objects?lat=55.7&lon=13.4` still returns HTTP 200 after Artemis II support is added; in mocked backend tests `objects` contains entries for both `ISS` and `Artemis II`
- Artemis II object includes `name`, `category`, `altitude_deg`, `azimuth_deg`, `direction`, `is_above_horizon`, and `data_source` using the same schema as G1
- `sky-map.js` renders Artemis II in the 2D view at positions matching its `altitude_deg` and `azimuth_deg`; if below horizon, marker shown with reduced opacity outside the horizon ring
- `sky-map-3d.js` renders Artemis II in the 3D view as a sprite/label when `is_above_horizon == true`; not rendered in 3D if below the horizon
- Hovering or tapping Artemis II shows a tooltip with Swedish UI text
- If the Artemis II source is unavailable, `/api/v1/artificial-objects` still returns HTTP 200 with any remaining valid objects; frontend sky map continues to function without JavaScript errors
- `backend/tests/test_api_artificial_objects.py` verifies mocked Artemis II ingestion and partial-failure fallback without regressing ISS support
