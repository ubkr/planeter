---
name: cleanup-refactor
description: Use this skill to remove dead code, eliminate redundant computation, and improve internal code quality without changing the external API contract or visible frontend behavior. Trigger after a burst of feature work or when the user asks to clean up or refactor.
version: 1.0.0
---

## Steps

1. Read the target module in full before making any changes.

2. Grep for all callers of every function being considered for removal or signature change. A function with no callers is a deletion candidate. A function with callers requires a coordinated update plan before touching it.

3. Read `backend/app/api/routes/planets.py` and all Pydantic models to establish the current external API contract. This contract must be identical before and after the refactor.

4. Identify dead code: unused return values, CSS selectors with no matching HTML elements, unreachable branches, functions never called from outside their own file.

5. Identify redundant computation: the same value computed more than once per request, repeated dictionary lookups that could be cached in a local variable, or duplicate logic across route handlers that could be extracted into a shared utility.

6. Plan the changes so that all four endpoints (`/visible`, `/tonight`, `/{name}`, `/events`) remain internally consistent after the refactor — they must continue to return the same fields in the same shapes.

7. Check `backend/tests/` and read the existing test files before modifying any function. If a test asserts on an internal signature that will change, plan the test update alongside the code change. Do not break tests and leave them broken. Weather service calls must be mocked in tests — do not allow any refactor to remove or bypass existing `httpx`/`requests` mocks in the test suite.

8. Confirm before writing any code that the planned change is pure cleanup: no new features, no API response changes visible to callers, no new or removed UI behavior visible to users. If the change introduces any of those, stop and use a different skill instead.
