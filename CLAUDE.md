# Planeter

A Swedish-language web app showing which naked-eye planets (Mercury, Venus, Mars, Jupiter, Saturn) are visible from a given location in Sweden right now and tonight.

## Stack

**Backend**: Python 3.9 + FastAPI with `ephem` library for astronomical calculations. Static files and API served as a single FastAPI app.

**Frontend**: Vanilla JS/HTML/CSS (no build step). Location picker (Leaflet), weather aggregation (Met.no + Open-Meteo fallback), in-memory cache, logger, and CSS design tokens.

**Core Features**: Planet position calculator, visibility scorer (evaluates altitude, magnitude, cloud cover, sun/moon interference), Swedish-language planet cards UI, 2D/3D sky map, and astronomical event detection.

## Documentation

- **`PLAN.md`** — Phased implementation plan and future roadmap.
- **`ARCHITECTURE.md`** — Component hierarchy, data flow, calculation pipeline, visibility scoring algorithm, and API response schema.
- **`TECH_CHOICES.md`** — Rationale for every technology choice: ephem vs alternatives, weather sources, frontend libraries, Python dependencies, and design theme.
