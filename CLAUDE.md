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

## Workflow

- Always validate the plan/phase intent against existing code BEFORE implementing. Read relevant files first, don't assume.
- When working with a sibling/reference project, copy needed files and information into the current project immediately. Do not keep referencing the other project.

## Quality Checks

- After implementation, run a self-review pass checking for bugs, NaN issues, missing imports, and CSS/interaction conflicts before presenting as done.

## Agent Patterns

- When asked to use an orchestrator/delegation pattern, ALWAYS delegate to sub-agents via the Task tool. Never do the work directly. If delegation fails, report the failure rather than bypassing the pattern.

## Environment

- Check the Python version in the environment before using modern syntax (3.10+ type unions, tomllib, etc). Target Python 3.9+ unless told otherwise.
