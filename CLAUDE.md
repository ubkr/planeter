# Planeter

A Swedish-language web app showing which naked-eye planets (Mercury, Venus, Mars, Jupiter, Saturn) are visible from a given location in Sweden right now and tonight.

## Stack

**Backend**: Python 3.9 + FastAPI with `ephem` library for astronomical calculations. Static files and API served as a single FastAPI app.

**Frontend**: Vanilla JS/HTML/CSS (no build step). Reuses location picker (Leaflet), weather aggregation (Met.no + Open-Meteo fallback), in-memory cache, logger, and CSS design tokens from the `norrsken` project.

**Core Features**: Planet position calculator, visibility scorer (evaluates altitude, magnitude, cloud cover, sun/moon interference), Swedish-language planet cards UI.

## Documentation

- **`PLAN.md`** — Phased implementation plan, what to copy from norrsken vs. build from scratch, and future roadmap (sky map, observation tips).
- **`ARCHITECTURE.md`** — Component hierarchy, data flow, calculation pipeline, visibility scoring algorithm, and API response schema.
- **`TECH_CHOICES.md`** — Rationale for every technology choice: ephem vs alternatives, weather sources, frontend libraries, Python dependencies, and design theme.
