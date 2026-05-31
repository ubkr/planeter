# Visibility & Scoring Enhancements (Phases 8–12)

**Status:** Completed

**Phases included:** Phase 8 (Visibility Reason Tooltips), Phase 9 (Scoring Accuracy & Scale Calibration), Phase 10 (Backend Cleanup), Phase 11 (Frontend Cleanup), Phase 12 (Magnitude-Aware Twilight Visibility)

---

## Intended Outcome (User Perspective)

Hovering over the visibility text on any planet card reveals a plain-Swedish tooltip explaining exactly why that planet is or is not visible right now — for example "Molnen blockerar sikten" or "Planeten är under horisonten". Multiple reasons can appear at the same time. Planets in excellent conditions show "Goda observationsförhållanden".

The score each planet receives is now accurate across the full 0–100 range and reflects real-world conditions. Bright planets like Venus and Jupiter are correctly marked visible during early twilight (when the sky is still slightly bright), while fainter planets still require deeper darkness. Hemisphere labels on the location display are correct for any point on Earth, not just Sweden.

---

## Definition of Done

### Phase 8 — Visibility Reason Tooltips
- `PlanetData` includes a non-empty `visibility_reasons` list for every planet whose score is below 100
- A planet below the horizon always carries the reason `"below_horizon"` and never a positive score
- A planet hidden by cloud cover carries `"molnighet"` regardless of altitude or score
- Hovering the visibility text shows a tooltip with at least one Swedish-language reason string
- Multiple simultaneous factors (low altitude + partial cloud cover) each appear as separate lines
- Planets with high score and no active penalties show no tooltip or "Goda observationsförhållanden"
- Tooltip is keyboard-accessible (visible on focus) and dismissed on blur or mouse-leave
- No JavaScript errors when `visibility_reasons` is an empty array

### Phase 9 — Scoring Accuracy & Scale Calibration
- `apply_scores()` sets `is_visible = False` when sun altitude is −8° (between civil and nautical twilight)
- `apply_scores()` sets `is_visible = True` when sun altitude is −14°, planet at 30° altitude, 0% cloud cover
- A planet at 45° altitude with magnitude −4.0, 0% cloud cover, sun at −20°, and no moon penalty scores 100
- `scoreToLevel` returns `"excellent"` for a score of 95
- Sky summary visible count shows 0 when all five planets have scores between 16 and 50
- `ARCHITECTURE.md` scoring table matches the new component weights in `score_planet()`
- No existing Phase 8 tooltip behaviour is broken

### Phase 10 — Backend Cleanup
- `calculate_moon_penalty()` no longer contains a `penalty_pts` key in its returned dict
- `_build_moon_info()` still constructs a valid `MoonInfo` object after removal
- The `/visible` endpoint makes exactly one call to `calculate_sun_penalty()` and one call to `calculate_moon_penalty()` per request
- The `/tonight` and `/{name}` endpoints also avoid double computation
- `fetchTonightPlanets()` in `frontend/js/api.js` carries a comment marking it reserved for a future phase
- All three API endpoints return identical response shapes as before
- `GET /api/v1/health` still returns HTTP 200

### Phase 11 — Frontend Cleanup
- `layout.css` contains no rules targeting `.score-section`, `.data-grid-section`, or `.chart-section`
- The `@media (min-width: 900px)` block contains only planeter-relevant rules or is removed
- `formatLocation({ lat: 55.7, lon: 13.4 })` returns `"55.70°N, 13.40°Ö"`
- `formatLocation({ lat: -33.9, lon: 18.4 })` returns `"33.90°S, 18.40°Ö"` (southern hemisphere)
- `formatLocation({ lat: 40.7, lon: -74.0 })` returns `"40.70°N, 74.00°V"` (western hemisphere)
- `formatLocation({ lat: -34.6, lon: -58.4 })` returns `"34.60°S, 58.40°V"` (southern and western)
- `formatLocation({ lat: 55.7, lon: 13.4, name: "Södra Sandby" })` returns `"Södra Sandby"` unchanged
- Page renders correctly at 375px and 1200px with no layout regressions
- No JavaScript console errors on initial page load

### Phase 12 — Magnitude-Aware Twilight Visibility
- `calculate_sun_penalty()` returns a `limiting_magnitude` float field alongside existing fields
- Limiting magnitude at sun altitude −6° ≈ magnitude −1 to 0 (empirically correct)
- Limiting magnitude at sun altitude −12° ≈ magnitude +3 to +4
- Limiting magnitude at sun altitude −18° ≈ magnitude +5.5 to +6.5
- `apply_scores()` sets `is_visible = True` for Venus (mag −3.8) at sun altitude −8° above horizon with clear skies
- `apply_scores()` sets `is_visible = True` for Jupiter (mag −2.2) at sun altitude −8° above horizon with clear skies
- `apply_scores()` sets `is_visible = False` for Saturn (mag +0.5) at sun altitude −8°
- `score_planet()` produces a higher score for Venus than Saturn at identical sun altitude −8°, all other factors equal
- Sun penalty in `score_planet()` is a continuous function (no abrupt score jumps at twilight boundaries)
- All existing unit tests continue to pass
- `ARCHITECTURE.md` documents the magnitude-aware twilight model and references Schaefer (1993)
