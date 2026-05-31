# Solar System — Interactive Planet Exploration (Phases F1–F7)

**Status:** Completed

**Phases included:** F1 (Planet Click & Zoom with Info Panel), F2 (Giant Planet Moon Positions), F3 (Saturn Ring Rendering), F4 (Integrated Zoom View with Side Info Panel), F5 (Earth-Moon System Detail View), F6 (Generic Tracked Spacecraft in Earth Detail), F7 (Time Slider for Earth-Moon View)

---

## Intended Outcome (User Perspective)

Clicking any planet dot in the solar system view zooms smoothly into that planet and shows a side panel with Swedish encyclopedic facts: diameter, orbital period, distance from the Sun, number of moons, and a short description of notable features. A "Tillbaka" button or pressing Escape returns to the full overview.

Clicking Jupiter shows its four Galilean moons (Io, Europa, Ganymedes, Callisto) plotted at their current positions around the planet. Clicking Saturn shows the planet with its ring system tilted to match the current Earth–Saturn geometry — nearly edge-on in 2025–2026 — plus its major moons including Titan.

Clicking Earth shows the Earth–Moon system with the Moon's current orbital position, and any tracked spacecraft such as Artemis II as a labelled marker in the diagram. A time slider in the Earth detail view lets the user scrub ±7 days to see where the Moon and any tracked spacecraft will be, with a Swedish offset label ("Nu", "3 dagar sedan", "om 2 dagar"). Moving the slider updates the diagram within half a second.

---

## Definition of Done

### Phase F1 — Planet Click & Zoom with Info Panel
- Clicking a planet dot triggers a smooth viewBox transition that centres the clicked planet within 400 ms
- An info overlay is visible containing the planet's Swedish name, diameter (km), orbital period, mean distance from the Sun (AU), number of known moons, and a 2–3 sentence description — all in Swedish
- `frontend/js/data/planet-info.js` exports encyclopedic data for all five planets and Earth (diameter_km, orbital_period_sv, distance_au, known_moons, description_sv)
- Clicking the Earth dot triggers the zoom and shows Earth's info panel
- A "Tillbaka" button or click-outside reverses the zoom and hides the overlay
- Zoomed state and info panel are usable on both 375 px and 1200 px viewports without overflow
- Info overlay is keyboard-accessible: focusable "Tillbaka" button, Escape key dismisses
- No JavaScript console errors when clicking planets before API data has loaded

### Phase F2 — Giant Planet Moon Positions
- `backend/app/services/planets/moons.py` exports `compute_moon_positions(dt)` returning X/Y offsets (in parent-planet radii) for Jupiter's 4 Galilean moons and Saturn's 7 major moons
- `PlanetPosition` includes `moons: Optional[List[MoonPosition]]` with fields `name`, `name_sv`, `x_offset`, `y_offset`
- `GET /api/v1/planets/visible?lat=55.7&lon=13.4` returns a non-empty `moons` array for Jupiter and Saturn; Mercury, Venus, Mars return null or empty list
- Zoomed Jupiter renders 4 moon dots (Io, Europa, Ganymedes, Callisto) at offsets matching their current X/Y values
- Zoomed Saturn renders at least Titan and other major moons as labelled dots
- Each moon dot has a Swedish label adjacent to it
- Moon dots are visually smaller than the planet circle and use a muted colour
- Hovering or tapping a moon dot shows a tooltip with the moon's Swedish name and offset distance
- Planets without moons show no moon rendering in their detail view — no errors or empty-state clutter
- No regression in existing solar system overview rendering

### Phase F3 — Saturn Ring Rendering
- `PlanetPosition` includes `ring_tilt_deg: Optional[float]` populated only for Saturn
- `GET /api/v1/planets/visible?lat=55.7&lon=13.4` returns a non-null `ring_tilt_deg` for Saturn; all other planets return null
- Zoomed Saturn renders an SVG ellipse around the planet circle; semi-minor axis is proportional to `|sin(ring_tilt_deg)|`
- At the current epoch (2025–2026), Saturn's rings render as a very thin ellipse nearly edge-on
- Ring ellipse uses Saturn's gold colour token at reduced opacity (≈ 0.4) so moons remain visible through it
- Ring rendering does not obscure the Saturn planet circle or its label
- No ring rendering for non-Saturn planets in their zoomed detail view
- No regression in existing solar system overview rendering

### Phase F4 — Integrated Zoom View with Side Info Panel
- Clicking Jupiter or Saturn keeps the zoomed rendering inside the existing solar system panel; no dark fullscreen overlay
- On wider viewports, the info panel renders to the left of the zoomed planet, which remains fully visible to the right
- For Jupiter, all moons in `planet.moons` render simultaneously without being clipped by the panel edge
- For Saturn, the zoomed view renders the planet, ring ellipse from `ring_tilt_deg`, and all moons together
- On 375 px viewport, layout stacks responsively without horizontal overflow, and zoomed rendering remains visible
- "Tillbaka" and Escape restore the normal overview without stale zoom or layout classes
- No JavaScript errors when switching between overview, zoomed, and fullscreen solar system modes

### Phase F5 — Earth-Moon System Detail View
- `GET /api/v1/planets/visible?lat=55.7&lon=13.4` returns a top-level `earth_system` object with a nested `moon` object containing `name_sv`, `x_offset_earth_radii`, `y_offset_earth_radii`, `distance_km`, and `illumination`
- Clicking the Earth dot opens the existing detail layout with title `Jorden` and a right-column Earth/Moon diagram containing one moon marker labelled `Månen`
- Moon marker position derived from `earth_system.moon.x_offset_earth_radii` and `y_offset_earth_radii`, not from a hardcoded angle
- Earth detail view usable on both 375 px and 1200 px viewports without horizontal overflow
- If `earth_system` is missing or null, clicking Jorden still opens the panel with a Swedish fallback message
- `backend/tests/test_api_planets.py` verifies the `earth_system` response shape and Moon offset fields

### Phase F6 — Generic Tracked Spacecraft in Earth Detail
- `GET /api/v1/artificial-objects?lat=55.7&lon=13.4` returns a schema where objects can optionally include an `earth_detail_position` payload; in mocked tests `Artemis II` includes this payload
- Clicking `Jorden` renders `Artemis II` in the Earth detail diagram using the current artificial-objects response, with a Swedish label `Artemis II`
- Objects without `earth_detail_position` are not rendered in the Earth/Moon diagram; ISS is excluded from this view
- Hovering or tapping the `Artemis II` marker shows a Swedish tooltip with `Avstånd från jorden` and `Datakälla`
- The Earth detail renderer can display more than one tracked object without layout breakage
- If no eligible object exists, the Earth/Moon detail still renders with a Swedish empty state: "Inga aktuella rymdfarkoster i jordsystemet"
- `backend/tests/test_api_artificial_objects.py` verifies the Earth-detail payload for `Artemis II` and schema extensibility

### Phase F7 — Time Slider for Earth-Moon View
- `GET /api/v1/earth-detail?lat=55.7&lon=13.4&offset_hours=0` returns HTTP 200 with `timestamp`, `earth_system`, and `objects`; Moon offset values match `/api/v1/planets/visible` at the same instant
- `GET /api/v1/earth-detail?lat=55.7&lon=13.4&offset_hours=-48` returns `earth_system.moon` with different x/y offsets than the `offset_hours=0` call
- `GET /api/v1/earth-detail?lat=55.7&lon=13.4&offset_hours=999` returns HTTP 422 (outside allowed range −168 to 168)
- Earth detail panel shows a `<input type="range">` slider with endpoint labels "−7 dagar" and "+7 dagar" and a centre tick "Nu"; default position is 0
- A Swedish label adjacent to the slider reflects the selected offset: "Nu" at 0, "3 dagar sedan" for −72 h, "om 2 dagar" for +48 h
- Moving the slider updates the Moon marker position within 500 ms after debounce (250 ms debounce)
- If `Artemis II` `earth_detail_position` is present, spacecraft marker moves to its position at the selected time; if absent, Swedish empty-state is shown without JavaScript errors
- Slider and labels visible and usable on both 375 px and 1200 px viewports without horizontal overflow
- Clicking "Tillbaka" resets the slider so next Earth detail entry starts at "Nu"
- `compute_earth_system(dt)` and `compute_horizons_earth_detail(dt)` each accept an explicit `datetime` parameter with no hardcoded "now" reference
