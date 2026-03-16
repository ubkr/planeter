---
name: full-stack-feature
description: Use this skill when implementing a new feature that requires both backend data changes and frontend rendering. Trigger when the request mentions showing new data on the cards or sky map, and that data doesn't yet exist in the API response. Covers adding Pydantic model fields, wiring through API routes, building frontend components, and styling with CSS tokens.
version: 1.0.0
---

## Steps

1. Read `ARCHITECTURE.md` for the current API schema and scoring pipeline before touching any code.

2. Read `backend/app/models/planet.py` and `backend/app/api/routes/planets.py` to understand the existing data flow end-to-end.

3. Read the target frontend component and its corresponding CSS file to understand the rendering pattern before making changes.

4. Extend the Pydantic model with any new fields. Use `Optional` types with sensible defaults so existing clients are not broken by the addition.

5. Update the API route to compute and populate the new field. Keep all three endpoints (`/visible`, `/tonight`, `/{name}`) in sync — every endpoint must include the new field. A field present in one response but absent from another is a bug. Also check `backend/app/api/routes/events.py` — if the new field is relevant to event data (e.g. a planet involved in a conjunction), that endpoint must be updated too.

6. Extend the frontend component's rendering method (e.g., `buildCard()` or `plotBodies()`) to consume and display the new data.

7. Add CSS using only token variables from `frontend/css/tokens.css`. Never hardcode color or spacing values. If a new token is genuinely needed, add it to `tokens.css` first, then reference it.

8. All user-facing strings must be in Swedish.

9. Update `ARCHITECTURE.md` if the API response schema changed. The docs must describe the current state of the code, not a previous version.

10. Run `pytest backend/tests/` to verify no backend tests were broken. If the feature touches `frontend/js/astro-projection.js` or any sky-map coordinate logic, also run `node frontend/tests/test-astro-projection.mjs` to verify the projection math.
