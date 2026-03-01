# Planeter — Bug Tracker

## Overview

This file tracks known bugs in the Planeter project. Each entry follows the same structure as phases in PLAN.md: a short title, metadata, symptoms, root cause, fix tasks, intended outcome, and definition of done. Open bugs are marked `[ ]` and resolved bugs are marked `[x]`.

---

## BUG-001: Browser loads stale norrsken JS instead of planeter JS — [x]

**Severity**: Critical
**Affects**: Phase 6 (Frontend) — `frontend/js/api.js`, `frontend/js/main.js`
**Status**: Resolved — no code change required

### Symptoms

- The browser console prints "Initializing Aurora Visibility app..." on startup, which is the norrsken app name, not Planeter.
- All API calls go to `/api/v1/prediction/current`, which is a norrsken endpoint that does not exist in the planeter backend.
- The backend returns HTTP 404 for every API request.
- The UI never receives planet data; the app fails silently after logging "Error loading core prediction data".
- The auto-refresh timer still starts (logged as "App initialized. Auto-refresh every 5 minutes"), confirming the wrong app's `main.js` ran to completion.

### Root Cause

The browser is executing the norrsken versions of `main.js` and `api.js` rather than the planeter replacements. The call stack in the error trace names `APIClient.getCurrentPrediction` (a norrsken method) and the request targets `/api/v1/prediction/current` (a norrsken route). Neither of these exist anywhere in the planeter codebase. The planeter API exposes `/api/v1/planets/visible`, `/api/v1/planets/tonight`, and `/api/v1/planets/{name}`.

There are two likely causes, which may both apply simultaneously:

1. **Stale browser cache** — the browser cached the old norrsken `main.js` and/or `api.js` and is serving them from cache instead of fetching the new planeter files from disk.
2. **Files not yet overwritten** — the planeter-specific `frontend/js/api.js` and `frontend/js/main.js` have not been written yet (they are listed as "Build from Scratch" items in the PLAN.md Phase 6 task table), so the norrsken originals remain on disk and are served unchanged.

The Phase 6 task table in PLAN.md confirms that `frontend/js/api.js` and the main application entry point are in the "Build from Scratch" column, meaning no planeter version of these files has been created yet.

### Resolution

The root cause was confirmed to be only a stale browser cache. A hard-reload cleared the cache and the planeter `main.js` and `api.js` created in Phase 6 loaded correctly. No files were missing or incorrect; no code fix was needed.

### Fix Tasks

No fix tasks were required. The issue was purely a browser cache problem resolved by a hard-reload (Cmd+Shift+R / Ctrl+Shift+R). The planeter-specific `main.js` and `api.js` were already in place and correct.

### Intended Outcome

The browser console shows "Initializing Planeter app..." (or equivalent Swedish text) on startup. All API calls go to `/api/v1/planets/visible` (or the appropriate planeter endpoint). The backend returns HTTP 200 with planet data. No 404 errors appear in the network tab.

### Definition of Done

- [x] Browser console contains no reference to "Aurora Visibility" or `getCurrentPrediction` on startup
- [x] Network tab shows requests to `/api/v1/planets/visible` (not `/api/v1/prediction/current`)
- [x] Backend responds HTTP 200 to the planet visibility request
- [x] Planet cards render in the UI with live data from the planeter API
- [x] No 404 errors appear in the browser console or network tab on initial load
