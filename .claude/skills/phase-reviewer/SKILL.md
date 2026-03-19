---
name: phase-reviewer
description: Reviews a specific completed phase by its ID against the actual codebase. Verifies that every Task, Intended Outcome, and Definition of Done item from PLAN.md is genuinely satisfied in source code. Runs tests and performs static inspection. Writes a structured pass/fail report to a caller-supplied output file. Does NOT implement missing items — it only reports them.
version: 1.0.0
---

## Overview

This skill audits a single PLAN.md phase. By the end it produces a structured report that answers: "Is this phase truly done, or are there gaps between the plan and the code?"

**Required inputs (both supplied by the caller):**
- **Phase ID** — the identifier as written in PLAN.md (e.g. `6`, `A1`, `12`, `B2`). Match it case-insensitively.
- **Output file path** — absolute or workspace-relative path where the report will be written (e.g. `review-phase-6.md`). Create the file; overwrite if it already exists.

---

## Step 1: Parse the phase from PLAN.md

Read `PLAN.md` in full. Locate the phase matching the supplied ID. Extract, verbatim:

- **Phase title**
- **Status line** (e.g. `✅`, `Pending`, `Deferred`)
- **Tasks list** — every bullet under `### Tasks`
- **Intended Outcome** — the full paragraph under `### Intended Outcome`
- **Definition of Done** — every checklist item under `### Definition of Done`
- **Key files** (if present, for lettered sub-phases)

If the phase ID is not found in PLAN.md, write a one-line error to the output file (`Phase <ID> not found in PLAN.md`) and stop.

If the phase is not marked `✅` in its **Status** line, note this prominently in the report header but continue the review — the caller may be reviewing an in-progress phase.

---

## Step 2: Classify the phase scope

Based on the Tasks list and Key files, categorise the phase as one or more of:

- **Backend** — touches `backend/` Python files
- **Frontend** — touches `frontend/` JS/CSS/HTML files
- **Docs-only** — touches only `*.md` documentation files
- **Infrastructure** — config, scripts, or project-root files

This determines which test commands to run in Step 5 and which source files to audit in Steps 3–4.

---

## Step 3: Audit each Task against the source code

For every task bullet extracted in Step 1, verify that the described change exists in the actual source files.

Work systematically through each task:

a. **Identify the target file(s)** — read the file path from the task description. If the path is implicit, infer it from context (e.g. "Extend the scoring module" → `backend/app/services/scoring.py`).

b. **Read the relevant section** of the target file. Do not skim — read enough to confirm the described implementation is present, not just that the file exists.

c. **For backend tasks**: look for the function, class, field, or logic described. Check Pydantic model fields, function signatures, scoring weights, `if` branches, and return values.

d. **For frontend tasks**: look for the DOM rendering, CSS rule, event handler, API call, or Swedish string described. Check `buildCard()`, `render()`, `fetch*()` functions, and CSS selector presence.

e. **For documentation tasks**: confirm the described content exists verbatim or paraphrastically in the target `.md` file.

f. **Assign a verdict** for each task:
   - `✅ DONE` — the implementation matches the task description
   - `❌ MISSING` — the file exists but the described change is absent
   - `⚠️ PARTIAL` — the change is present but incomplete or different from what was described
   - `❓ UNVERIFIABLE` — the task is too abstract to verify by code inspection alone (note why)

---

## Step 4: Audit each Definition of Done item

Every DoD item is a falsifiable criterion. Verify each one by inspecting code, grepping for identifiers, or reading specific values.

Apply these verification strategies by DoD item type:

**HTTP status code assertions** (e.g. "`GET /api/v1/planets/visible` returns HTTP 200"):
- Read `backend/app/api/routes/planets.py` to confirm the endpoint exists and returns the expected type.

**Field presence assertions** (e.g. "each planet object contains `name`, `altitude`, `azimuth`"):
- Read the relevant Pydantic model in `backend/app/models/` and confirm every named field is defined and populated.

**Score/value assertions** (e.g. "a planet at −1° altitude returns score 0"):
- Read the scoring logic in `backend/app/services/scoring.py` to confirm the described boundary condition is handled, or check the corresponding test in `backend/tests/`.

**UI assertions** (e.g. "all five planet cards render without console errors", "labels are in Swedish"):
- Read the rendering code in the relevant `frontend/js/components/` file. Grep for the Swedish strings mentioned. Check the CSS file for the described visual class.

**Test assertions** (e.g. "`pytest` exits with code 0"):
- Defer to the test run in Step 5 rather than inspecting test files.

**Regex/function-value assertions** (e.g. "`formatLocation({ lat: -33.9, lon: 18.4 })` returns `"33.90°S, 18.40°Ö"`"):
- Read the function implementation directly and trace the logic for the given input.

**Assign a verdict** for each DoD item using the same scale as Step 3 (`✅ DONE`, `❌ MISSING`, `⚠️ PARTIAL`, `❓ UNVERIFIABLE`).

---

## Step 5: Run tests

Run only the test suite(s) relevant to the phase scope identified in Step 2.

**If the phase is Backend or Full-stack:**
```
cd backend && python -m pytest tests/ -v 2>&1 | tail -40
```
Capture the exit code and the final summary line (e.g. `5 passed, 2 failed`).

**If the phase touches astro-projection or sky-map coordinate logic:**
```
node frontend/tests/test-astro-projection.mjs 2>&1
```
Capture the exit code and any failure lines.

**If tests fail**, record each failing test name and its assertion error in the report. Do not attempt to fix failures — report them.

**If the phase is Docs-only**, skip this step and note that no tests apply.

---

## Step 6: Evaluate the Intended Outcome

The Intended Outcome is a qualitative paragraph — verify it as a user-facing holistic check rather than a per-item audit.

Read it carefully. For each distinct claim in the paragraph:

a. Identify the claim (e.g. "bright planets receive a smaller twilight penalty than faint planets").
b. Find the code, data, or test that substantiates the claim.
c. Mark the claim `✅ Supported`, `❌ Unsupported`, or `⚠️ Partially supported`.

Pay attention to user-visible outcomes specifically: what would a user see in the browser, what JSON does the API return, what does "a single function call returns X" actually produce? If the Intended Outcome mentions something observable, confirm the observable artifact exists.

---

## Step 7: Write the report to the output file

Write the report using **the same Markdown conventions as PLAN.md** so that the findings can be fed directly into any other skill (`backend-fix`, `full-stack-feature`, etc.) without reformatting.

Concretely:

- Use `##` for the top-level phase heading.
- Use the same bold metadata fields (`**Status**`, `**Reviewed**`, `**Scope**`, `**Overall result**`).
- Use `### Tasks`, `### Definition of Done`, and `### Intended Outcome` as section headings, matching PLAN.md exactly.
- Use `- [x]` for items that **pass** and `- [ ]` for items that **fail or are partial** — identical to the PLAN.md DoD checkbox convention.
- Include a `### Gaps Requiring Action` section at the end that lists only the `- [ ]` items, each annotated with the file and the specific change needed — formatted as actionable task bullets matching the PLAN.md task style.
- Include a `### Test Results` section with the raw pytest/node output summary.

Use this exact template:

```markdown
## Phase Review: Phase <ID> — <Title>

**Reviewed:** <current date>
**Status in PLAN.md:** <✅ / Pending / Deferred>
**Scope:** <Backend | Frontend | Full-stack | Docs-only | Infrastructure>
**Overall result:** ✅ COMPLETE | ⚠️ PARTIAL | ❌ INCOMPLETE

### Intended Outcome

<One-paragraph verdict on whether the Intended Outcome is met. For each distinct claim in the original Intended Outcome paragraph, prefix the sentence with ✅, ⚠️, or ❌ and append the evidence in parentheses. Keep the paragraph prose form.>

### Tasks

- [x] <Exact or abbreviated task text> — *<evidence: file:line or identifier confirmed>*
- [ ] <Exact or abbreviated task text> — *<what is missing or wrong>*

### Definition of Done

- [x] <Exact DoD item text> — *<evidence: file:line, grep match, or test name>*
- [ ] <Exact DoD item text> — *<what is missing, wrong value, or absent identifier>*

### Test Results

**Backend:** exit <code> — <pytest summary line, e.g. "12 passed, 0 failed in 4.2s">
**Frontend:** exit <code> — <summary> | N/A

<If any tests failed, list each failing test name and its assertion error as a sub-bullet here.>

### Gaps Requiring Action

<List only the items that have - [ ] above. Each gap must name the exact file and describe the precise change needed, in the same imperative-verb style as PLAN.md task bullets. If the phase is fully complete, write "None — phase is complete.">

- [ ] <Imperative verb + file path + specific change required, e.g. "Add `visibility_reasons` field to `PlanetData` in `backend/app/models/planet.py`">
```

---

## Step 8: Update PLAN.md DoD checkboxes (conditional)

After writing the report:

- If **every** DoD item is `✅ DONE` and the test run passed (exit code 0), update `PLAN.md` to replace each `- [ ]` checkbox under this phase's Definition of Done with `- [x]`.
- If **any** item is `❌ MISSING`, `⚠️ PARTIAL`, or a test failed, do **not** modify PLAN.md. Leave the checkboxes as-is so the gaps remain visible.

Do not modify any other part of PLAN.md — not the Status line, tasks, or text content.

---

## Important constraints

- **Do not implement fixes.** If the review reveals a missing feature, report it in the Gaps section. Use a different skill (`backend-fix`, `full-stack-feature`, etc.) to address gaps.
- **Do not modify source files** (`*.py`, `*.js`, `*.css`, `*.html`). This skill is read-only except for writing the report file and conditionally checking off DoD boxes in PLAN.md.
- **Be specific in evidence.** Every verdict must cite a concrete artifact: a file path, line range, grep match, field name, function name, or test name. Verdicts without evidence are not acceptable.
- **Swedish strings matter.** If a DoD or Task item specifies a Swedish label or string, grep for that exact string in the frontend source. A UI string present in English when Swedish is required is a `❌ MISSING`.
- **Boundary condition logic matters.** For scoring and calculation tasks, read the actual numeric thresholds in the code — do not assume the implementation matches the spec.
