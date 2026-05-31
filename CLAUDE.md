# Planeter

A Swedish-language web app showing which naked-eye planets (Mercury, Venus, Mars, Jupiter, Saturn) are visible from a given location in Sweden right now and tonight.

## Stack

**Backend**: Python 3.9 + FastAPI with `ephem` library for astronomical calculations. Static files and API served as a single FastAPI app.

**Frontend**: Vanilla JS/HTML/CSS (no build step). Location picker (Leaflet), 3D sky dome (Three.js r170, vendored), weather aggregation (Met.no + Open-Meteo fallback), in-memory cache, logger, and CSS design tokens.

**Core Features**: Planet position calculator, visibility scorer (evaluates altitude, magnitude, cloud cover, sun/moon interference), Swedish-language planet cards UI, 2D/3D sky map, and astronomical event detection.

## Documentation

- **`development_plan/`** — Phased implementation plan split into thematic files. Completed phases live in `development_plan/completed/`; upcoming and deferred phases live in the root of that directory. See `development_plan/README.md` for the workflow and file template.
- **`ARCHITECTURE.md`** — Component hierarchy, data flow, calculation pipeline, visibility scoring algorithm, and API response schema.
- **`TECH_CHOICES.md`** — Rationale for every technology choice: ephem vs alternatives, weather sources, frontend libraries, Python dependencies, and design theme.

## Confirmed Decisions

| Question | Decision |
|---|---|
| Planet scope | Naked-eye only: Mercury, Venus, Mars, Jupiter, Saturn |
| Time selection | Right now + tonight: current positions, plus tonight's visibility windows (sunset → sunrise) |
| UI language | Swedish: all labels, planet names, and UI text in Swedish |
| Cloud cover | Affects visibility score: overcast sky reduces or zeroes a planet's score |
| Default location | Södra Sandby (55.7°N, 13.4°E) |
| Uranus/Neptune | Not in scope for MVP; planned in Phase C (deferred) |

## Workflow

- Always validate the plan/phase intent against existing code BEFORE implementing. Read relevant files first, don't assume.
- When working with a sibling/reference project, copy needed files and information into the current project immediately. Do not keep referencing the other project.

## Quality Checks

- After implementation, run a self-review pass checking for bugs, NaN issues, missing imports, and CSS/interaction conflicts before presenting as done.

## Agent Patterns

- When asked to use an orchestrator/delegation pattern, ALWAYS delegate to sub-agents via the Task tool. Never do the work directly. If delegation fails, report the failure rather than bypassing the pattern.

## Environment

- Check the Python version in the environment before using modern syntax (3.10+ type unions, tomllib, etc). Target Python 3.9+ unless told otherwise.
