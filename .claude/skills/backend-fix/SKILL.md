---
name: backend-fix
description: Use this skill for pure Python backend work that has no frontend component: fixing a calculation in `calculator.py`, tuning scoring weights in `scoring.py`, fixing a weather client, adding a new planet field that doesn't need UI changes, or correcting astronomical math. Do not use this for changes that also require frontend rendering updates (use `full-stack-feature` instead) or for non-behavioral cleanup (use `cleanup-refactor` instead).
version: 1.0.0
---

## Steps

1. Read `ARCHITECTURE.md` to understand the calculation pipeline and scoring algorithm.

2. Read `backend/app/services/planets/calculator.py`, `backend/app/services/scoring.py`, and any relevant utility files (`backend/app/utils/`) to understand the current implementation. Also read `backend/app/services/planets/events.py` if the fix involves event detection.

3. Read `backend/app/models/planet.py` to understand the data model.

4. Read `backend/app/api/routes/planets.py` and `backend/app/api/routes/events.py` to understand how calculated data is exposed — confirm whether the API contract needs to change or can stay the same.

5. If adding or modifying a Pydantic field, use `Optional` types with defaults for backward compatibility.

6. If modifying scoring weights or thresholds, check `ARCHITECTURE.md`'s scoring table and update it if the documented values change.

7. All four public endpoints (`/visible`, `/tonight`, `/{name}`, `/events`) must remain consistent after the change — verify each one is still correct.

8. Do not make any changes to `frontend/` files in this skill — if a frontend change turns out to be necessary, escalate to `full-stack-feature` instead.

9. Run `pytest backend/tests/` and confirm all tests pass. If fixing a calculation, add or update a test in the appropriate file (`test_calculator.py` or `test_scoring.py`) to prevent regression.

10. Weather service calls must be mocked in tests — do not remove or bypass existing `httpx`/`requests` mocks.
