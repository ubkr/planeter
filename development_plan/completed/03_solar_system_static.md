# Solar System View — Static Snapshot (Phase 13)

**Status:** Completed

**Depends on:** Phase 6 (Frontend), Phase 2 (Planet Calculation Engine)

---

## Intended Outcome (User Perspective)

The app gains a fourth tab called "Solsystemet". Clicking it shows a top-down view of the inner solar system: the Sun sits at the centre as a golden circle, and the five planets appear as coloured dots on their correctly scaled orbital rings. The user can immediately see how the planets are currently arranged in space. Hovering or tapping any planet dot shows a tooltip with the planet's Swedish name and its current distance from the Sun in astronomical units. The diagram updates when the user changes location.

---

## Definition of Done

- `PlanetPosition` includes three new optional float fields: `heliocentric_x_au`, `heliocentric_y_au`, `heliocentric_z_au`; Venus on 2026-03-29 has non-null values for all three
- `GET /api/v1/planets/visible?lat=55.7&lon=13.4` returns heliocentric coordinates for all five planets; each planet's distance from origin is within 0.1 AU of its known semi-major axis
- A "Solsystemet" tab button renders as the fourth tab in the tab bar, after "Kommande"
- Clicking "Solsystemet" hides the other three panels and shows an SVG diagram with the Sun at the centre and five planetary orbit circles
- All five planets (Merkurius, Venus, Mars, Jupiter, Saturnus) render as coloured dots on or near their respective orbit rings at positions matching their heliocentric coordinates
- Hovering a planet dot on desktop or tapping it on mobile shows a tooltip with the Swedish planet name and distance formatted as "X.XX AU"
- Mercury's orbit circle is visibly smaller than Earth's implied orbit (1 AU reference), and Saturn's orbit is the outermost ring
- Planet dot colours match the existing per-planet CSS tokens: Mercury grey, Venus yellow, Mars red, Jupiter amber, Saturn gold
- The Sun is rendered as a larger golden circle at the origin with the label "Solen"
- Switching to a different location (via the map picker) triggers a re-render of planet positions
- No JavaScript console errors when switching to the "Solsystemet" tab before API data has loaded
- The SVG maintains correct aspect ratio and is centred in its container on both 375 px and 1200 px viewports
