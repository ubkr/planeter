# Phase C: Extended Bodies

**Status:** Deferred — planned for a future iteration

---

## Intended Outcome (User Perspective)

The app expands beyond the five naked-eye planets to include additional celestial objects that require a small telescope or binoculars:

- **Uranus and Neptune** appear on the planet cards and sky map as telescope targets with their own scores and positions.
- **Bright asteroids** (Vesta, Ceres) appear when they are at a favourable magnitude, with telescope-target badges.
- **Active comets** appear when a notable comet is visible, with a dynamically computed position and brightness estimate.
- **International Space Station pass predictions** show when ISS will make a visible pass over the user's location in the next 24 hours, with start/end azimuth and maximum elevation.

---

## Definition of Done

- [ ] Uranus and Neptune appear in the planet cards and sky map alongside the five naked-eye planets; each has a `requires_telescope: true` flag and a telescope-target badge
- [ ] The visibility scorer applies appropriate magnitude penalties for Uranus (mag ≈ +5.7) and Neptune (mag ≈ +7.9), so they score lower than naked-eye planets under equivalent conditions
- [ ] Bright asteroids Vesta and Ceres are fetched from a suitable ephemeris source and rendered on the sky map when their visual magnitude is brighter than the current sky limiting magnitude
- [ ] At least one currently active notable comet (if any) is fetched from a live data source (e.g. JPL Small-Body Database or MPC) and rendered on the sky map with a predicted magnitude
- [ ] ISS pass predictions for the next 24 hours appear in a dedicated section; each pass shows the start time, peak altitude, direction at peak, and end time in Europe/Stockholm local time
- [ ] All new objects follow the existing Swedish-language convention for labels, tooltips, and card text
- [ ] No regression in existing planet cards, sky map, or artificial-objects views

---

## Dependencies

- Phase 5 (API Layer)
- Phase A3 (Sky Map — Planet, Sun & Moon Plotting)
- Phase G1 (ISS via Separate Artificial Objects Endpoint) — for ISS pass predictions

---

## Notes

- Uranus and Neptune can reuse the existing `ephem`-based calculation pipeline with minimal changes to `calculator.py`.
- Asteroid and comet data require a decision on an appropriate live ephemeris source (e.g. JPL Horizons, MPC).
- ISS pass predictions require a Two-Line Element (TLE) source and a satellite propagation library (e.g. `skyfield` or `ephem`).
- Phase scope and order within this group may be split into sub-phases (C1: Uranus/Neptune, C2: Asteroids, C3: Comets, C4: ISS Passes) when implementation begins.
