# Sky Map (Phases A1–A4)

**Status:** Completed

**Phases included:** Phase A1 (Tab Shell & Navigation), Phase A2 (SVG Polar Projection Grid), Phase A3 (Planet, Sun & Moon Plotting), Phase A4 (Constellation Lines)

---

## Intended Outcome (User Perspective)

The app gains a "Stjärnkarta" tab that shows an interactive sky map. The map is a circular chart where the centre is directly overhead and the edge is the horizon. Swedish cardinal directions (N, O, S, V) and intermediate directions (NO, SO, SV, NV) are labelled around the edge. Altitude rings at 30° and 60° are drawn for orientation.

All five planets, the Sun, and the Moon are plotted as coloured dots at their real current positions. Planets below the horizon appear faded outside the horizon ring. Hovering or tapping any body shows a tooltip with its Swedish name, altitude, compass direction, and magnitude. Constellation stick figures are drawn behind the planets in a subtle muted colour, each labelled with its IAU abbreviation. The map updates automatically when new data arrives or the location changes. If the constellation data fails to load the planets are still shown correctly.

---

## Definition of Done

### Phase A1 — Tab Shell & Navigation
- A tab bar renders below the header with exactly two tabs labelled "Planeter" and "Stjärnkarta"
- On initial page load the "Planeter" tab is active and the planet cards and sky summary are visible
- Clicking "Stjärnkarta" hides `#skySummary` and `#planetCards` and shows `#skyMapContainer`
- Clicking "Planeter" hides `#skyMapContainer` and shows `#skySummary` and `#planetCards`
- The active tab uses `--color-accent-primary` as its visual indicator
- Tab bar is usable on a 375 px mobile viewport with no horizontal overflow
- Switching tabs does not trigger an API re-fetch; both views share the same data
- No JavaScript console errors when switching tabs rapidly
- `aria-selected` and `role="tab"` / `role="tabpanel"` attributes are set correctly
- Tab bar and container use existing design tokens

### Phase A2 — SVG Polar Projection Grid
- An SVG element renders inside `#skyMapContainer` when the sky map tab is active
- The SVG uses a `viewBox` attribute and scales responsively with no fixed pixel dimensions
- Three concentric circles are drawn at altitudes 0° (horizon), 30°, and 60°
- Each altitude ring is labelled with its degree value using `--color-text-muted`
- Cardinal labels N, O, S, V are placed at the four cardinal positions around the horizon
- Intermediate tick marks (NO, SO, SV, NV) are drawn at 45° intervals
- North (azimuth 0°) is at the top of the chart; East (90°) is to the right
- `altAzToXY(altitude_deg, azimuth_deg)` is exported as a pure function testable in isolation
- Grid lines use `--border-color`; labels use `--color-text-secondary`; background uses `--color-bg-surface`
- The SVG maintains a 1:1 aspect ratio on both 375 px and 1200 px viewports
- No JavaScript console errors when switching to the sky map tab

### Phase A3 — Planet, Sun & Moon Plotting
- All five planets appear on the sky map at positions matching their `altitude_deg` and `azimuth_deg` from the API
- Planet dot radius varies with apparent magnitude: Venus is visibly larger than Saturn
- Each planet dot uses its per-planet colour from `tokens.css`
- Planets with `altitude_deg < 0` are rendered at 0.3 opacity outside the horizon ring
- Planet labels (Swedish name) are rendered next to each dot
- The Sun is plotted as a golden circle at its correct altitude/azimuth position
- The Moon is plotted using `moon.elevation_deg` and `moon.azimuth_deg` from the API response
- Hovering a planet dot shows a tooltip with: Swedish name, altitude, direction, and magnitude
- Sun tooltip shows "Solen" and its elevation; Moon tooltip shows "Månen" and its illumination percentage
- The tooltip reuses the existing `tooltip.js` component
- The sky map re-renders when `loadData()` completes without requiring a tab switch
- No JavaScript console errors when the map contains planets both above and below the horizon
- `SunInfo` model includes `azimuth_deg` field populated from the sun calculation

### Phase A4 — Constellation Lines
- `frontend/data/constellations.json` exists, is < 150 KB uncompressed, and contains at least 30 prominent constellations visible from Sweden (55°–70° N)
- `THIRD_PARTY_LICENSES.md` documents the Stellarium data source, its GPL-2.0-or-later licence, and the URL of the original file
- `frontend/js/astro-projection.js` exports `raDecToAltAz(ra_deg, dec_deg, lat, lon, utc_timestamp)` as a pure function
- Constellation lines render as SVG elements with stroke colour `--color-text-muted` at 0.25 opacity
- Constellation lines are drawn in an SVG `<g>` group layered behind the planet/sun/moon group
- Each visible constellation has its IAU three-letter label rendered near its geometric centre
- Constellations entirely below the horizon are not rendered
- The constellation layer updates when data refreshes (location change or auto-refresh)
- If `constellations.json` fails to load, the sky map renders planets and grid without constellation lines and logs a warning — no JavaScript errors thrown
- `raDecToAltAz()` is unit-tested for at least two known star positions
