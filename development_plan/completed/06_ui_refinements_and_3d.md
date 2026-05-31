# UI Refinements & 3D Sky View (Phases E1–E13)

**Status:** Completed

**Phases included:** E1 (Collapse Non-Visible Planets), E2 (3D Sky Setting & Navigation), E3 (Plotting Celestial Bodies in 3D), E4 (3D Constellations & Environment Polish), E5 (Documentation Update), E6 (Sky Map Expand Button), E7 (Zoom in 2D and 3D Sky Map), E8 (Constellation Toggle & Intensity Slider), E8.1 (Constellation Data Rebuild Pipeline), E9 (Bright Stars in Sky Map), E10 (Star Tooltips), E11 (Match Constellation Intensity 2D/3D), E12 (Intermediate Compass Labels & Colour Consistency), E13 (Fullscreen Solar System View)

---

## Intended Outcome (User Perspective)

Planets that aren't currently visible shrink into compact cards so the user can immediately see the visible planets without scrolling past irrelevant detail. Non-visible planets show only their name, status, and when they become visible tonight.

The "Stjärnkarta" tab gains a "3D Vy" toggle. In 3D mode the user is placed inside a realistic sky dome and can drag to look in any direction — north, south, up at the zenith — as if standing outside. Planets, the Sun, and the Moon appear as coloured sprites at their real positions. Constellation lines and labels carry over from the 2D view. The brightest naked-eye stars (those actually visible given current twilight) are plotted as small white dots sized by brightness. Hovering or tapping any star, planet, or the Sun/Moon in either the 2D or 3D view shows a Swedish tooltip with observation data.

An expand button in the sky map panel fills the entire browser window with the sky map (2D or 3D), and +/− buttons zoom in and out. A constellation toggle instantly shows or hides all constellation lines and labels, and an intensity slider adjusts how bright the lines appear — the same slider affects both the 2D and 3D views at matching visual strength.

The solar system view similarly gains a fullscreen button. Intermediate compass labels (NO, SO, SV, NV) are added to the 3D dome, and the Sun and Moon colours in 3D match their colours in the 2D map.

---

## Definition of Done

### Phase E1 — Collapse Non-Visible Planets
- `buildCard()` branches: planets with `is_visible == false` or `is_above_horizon == false` use a compact layout
- Compact card hides score bar, detailed grid (altitude, direction, magnitude, constellation), and generic rise/transit/set times
- Compact card displays planet name, visibility condition pill, and "Bästa tid" section
- `.planet-card--compact` class added to CSS with reduced padding and adjusted flex layout
- Non-visible planets still maintain their greyed-out appearance
- "Vad ska man leta efter?" toggle hidden on compact cards
- Equipment badge (B3) hidden on compact cards
- Visibility pill distinguishes "Under horisonten" from "Ej synlig"
- Skeleton loading cards retain full height; compact mode only applies after API data has loaded
- No backend changes required
- Page renders neatly on both mobile and desktop, mixing full-height and compact cards

### Phase E2 — 3D Sky Setting & Navigation
- Three.js r0.174.0 and OrbitControls are vendored as local ES module files under `frontend/lib/`, resolved via an import map in `index.html` — no CDN dependency
- A view toggle is added to the "Stjärnkarta" tab allowing switching between 2D and 3D views
- Selecting "3D Vy" instantiates a full-width immersive 3D canvas
- A camera at (0,0,0) with drag-to-look controls allows full 360° panning and tilting
- A horizon line/plane defines where sky meets earth
- A celestial grid (azimuth lines every 30°–45°, altitude lines at 30° and 60°) is drawn in 3D space
- Changing screen size resizes the 3D canvas with correct aspect ratio
- Render loop started when 3D view is active; cleanly stopped on switch to 2D or another tab
- User's 2D/3D view preference is stored in `localStorage` and restored on page load
- Mobile touch controls use single-finger drag for rotation only; pinch-zoom is disabled
- 2D SVG sky map remains the default view and accessible fallback; 3D canvas has `aria-hidden="true"`

### Phase E3 — Plotting Celestial Bodies in 3D
- Spherical coordinate math correctly converts altitude/azimuth into Cartesian coordinates
- Planets, the Sun, and the Moon render as billboarded sprite quads based on live API data
- Bodies with altitude < 0 are hidden entirely (ground plane acts as occlusion boundary)
- Hovering (desktop) or tapping (mobile) on a 3D celestial object works via raycaster
- Triggering an object displays the existing Swedish tooltip with name, altitude, azimuth, and magnitude
- Each celestial body has a text label rendered as a CSS2D HTML overlay
- `SkyMap3D` exposes `plotBodies(planets, sun, moon, events)` with the same signature as the 2D `SkyMap.plotBodies()`
- Sun rendered as a larger warm-coloured sprite; Moon shows illumination percentage in its tooltip
- Updating the geographic location dynamically refreshes object placement in the 3D scene

### Phase E4 — 3D Constellations & Environment Polish
- Constellation JSON data points are projected using `altAzToCartesian()` and connected with `LineBasicMaterial` line segments (`LineSegments`)
- Constellation lines align with the planets, Sun, and Moon
- CSS2DRenderer renders N, O, S, V cardinal labels around the 3D horizon ring
- Constellation labels appear at their celestial geometric centres as CSS2D overlays
- Constellations below the horizon are not rendered
- Constellation line geometry is built once per data update, not rebuilt every render frame
- Geometry rebuild profiled on a mid-range mobile browser: only on data updates

### Phase E5 — Documentation Update
- `ARCHITECTURE.md` describes the `SkyMap3D` class, its public interface (`plotBodies`, `plotConstellations`), and its relationship to the 2D `SkyMap`
- `ARCHITECTURE.md` includes the 2D/3D component hierarchy
- `TECH_CHOICES.md` documents the Three.js choice with rationale
- `TECH_CHOICES.md` documents the vendored-over-CDN decision
- `TECH_CHOICES.md` documents the lazy-loading strategy (Three.js loaded only on first 3D activation)
- `CLAUDE.md` stack section updated with Three.js if confirmed as permanent

### Phase E6 — Sky Map Expand Button
- A "Förstora"/"Minimera" button appears in `.sky-map-panel` for both 2D and 3D modes
- Clicking toggles `.sky-map-panel--expanded`, covering the entire browser window (100vw × 100vh) without scrollbars
- 3D canvas redraws without black borders or incorrect proportions in expanded mode
- 2D SVG fills the expanded space without distortion (aspect ratio preserved via `viewBox`)

### Phase E7 — Zoom in 2D and 3D Sky Map
- Two buttons "+" and "−" are visible in `.sky-map-panel` in both 2D and 3D mode
- Clicking "+" zooms in (smaller sky portion, more detail); "−" zooms out (larger sky portion)
- Pinch-zoom on mobile and scroll wheel on desktop work in both views
- 2D SVG `viewBox` adjusts dynamically around centre point (250, 250) within range 200×200 to 500×500
- 3D `PerspectiveCamera.fov` adjusts within range 20° (maximum zoom-in) to 90° (maximum zoom-out), default 60°
- Camera in 3D stays at origin (0, 0, 0.001) regardless of zoom level
- Zoom level resets to default on switching 2D/3D and on location change
- Zoom buttons work correctly in both normal and expanded fullscreen mode
- No JavaScript console errors on rapid zoom or on zooming an empty map

### Phase E8 — Constellation Toggle & Intensity Slider
- A checkbox labelled "Stjärnbilder" appears in sky map controls; unchecking instantly hides all constellation elements in both 2D and 3D without requiring a re-fetch
- A range slider labelled "Intensitet" (min 0, max 1, step 0.05) updates constellation opacity in real time in both views
- Enabled state and opacity value stored in `localStorage` under `planet_constellation_enabled` and `planet_constellation_opacity` and restored on page load
- Hardcoded `opacity: 0.25` in `sky-map.css` removed; slider is the sole opacity source
- Hardcoded `opacity: 0.5` in `sky-map-3d.js` `plotConstellations()` replaced by the stored/current slider value
- New controls styled consistently with existing `.sky-map-zoom-controls` and `.sky-map-expand-btn`

### Phase E8.1 — Constellation Data Rebuild Pipeline
- `tools/download_sources.sh` exists and fetches source data with validation
- `tools/build_constellations.py` generates `constellations.json` with coordinate validation
- Downloaded source files excluded from git (tools/data/*.csv, *.fab in .gitignore)
- `ARCHITECTURE.md` documents two-step rebuild workflow
- `TECH_CHOICES.md` explains data source selection (Stellarium + HYG)
- `THIRD_PARTY_LICENSES.md` includes Stellarium GPL-2.0-or-later attribution
- Build script includes comprehensive docstring with usage instructions
- Validation against `bright-stars.json` passes (< 0.1° tolerance)
- Generated `constellations.json` matches schema (30 constellations, valid RA/Dec ranges)

### Phase E9 — Bright Stars in Sky Map
- `SunInfo` in `/api/v1/planets/visible` response contains `limiting_magnitude` float; value ≈ 6.5 at sun −20°, ≈ −1 at sun −6°
- `frontend/data/bright-stars.json` contains at least 40 stars with visual magnitude ≤ 2.5 and fields `ra_deg`, `dec_deg`, `magnitude`, `name`
- Sirius appears as an SVG dot in the 2D `.sky-map-stars` group at the correct position when above horizon and sun < −18°; no dot when sun > 0°
- In 3D the same visibility filter applies and matching stars are visible at matching positions
- Stars with altitude ≤ 0° are not rendered in either view
- Star dots are visually smaller than planet dots; Sirius is smaller than Venus in both views
- `SkyMap.plotStars()` and `SkyMap3D.plotStars()` both accept `(stars, limitingMagnitude, lat, lon, utcTimestamp)`
- No JavaScript console errors when `plotStars()` called with an empty array
- Star layer renders behind all planetary bodies in both views

### Phase E10 — Star Tooltips
- Visible stars in 2D view render as interactive tooltip targets; hover or keyboard focus shows tooltip with name, altitude, direction, and magnitude
- Visible stars in 3D view participate in the raycaster flow; hovering or tapping shows the corresponding tooltip
- Star tooltip content reuses existing `TooltipManager` convention; no new tooltip component introduced
- Stars filtered out by `limiting_magnitude` or below horizon have no tooltip and leave no invisible interaction targets
- Sirius shows a tooltip with name `Sirius` and its magnitude when visible; no tooltip in daylight
- No regression in existing planet tooltips in 2D or 3D
- No JavaScript errors when `plotStars()` called with an empty array or pointer moved over a map with no visible stars

### Phase E11 — Match Constellation Intensity Between 2D and 3D
- With intensity slider at maximum (1), constellation lines in 3D are visually as strong as in the 2D view
- `frontend/js/main.js` uses a single shared `constellationOpacity` value for both renderers
- Moving the slider updates both views immediately; switching 2D/3D preserves the same stored slider value
- Constellation labels in 3D remain legible at maximum intensity
- No regressions in constellation visibility toggling
- No JavaScript errors when slider dragged repeatedly between minimum and maximum while switching 2D/3D

### Phase E12 — Intermediate Compass Labels & Colour Consistency in 3D
- 3D sky dome renders NO, SO, SV, NV labels at azimuths 45°, 135°, 225°, and 315°
- Intermediate sprites are visually subordinate to main cardinal sprites (N, O, S, V) — smaller scale or dimmer colour
- `BODY_COLORS.moon` in `sky-map-3d.js` equals `'#c084fc'` (purple, matching `--color-moon-penalty`)
- `BODY_COLORS.sun` in `sky-map-3d.js` equals `'#f59e0b'` (amber, matching `--color-sun-penalty`)
- Existing cardinal labels N, O, S, V in 3D are unchanged
- No JavaScript console errors when switching between 2D and 3D or on sky map re-render after location change

### Phase E13 — Fullscreen Solar System View
- A "Förstora"/"Minimera" button appears in `#panelSolarSystem` container
- Clicking toggles `.solar-system-panel--expanded`, covering the entire browser window without scrollbars
- Clicking again returns the view to its original layout
- SVG fills expanded space without distortion (aspect ratio preserved via viewBox)
- Planet tooltips continue to work in both normal and expanded modes
- No regression in solar system view rendering on 375 px and 1200 px viewports
