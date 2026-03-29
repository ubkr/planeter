---
name: new-plan-entry
description: Accepts a brief feature description, autonomously researches the codebase and existing plan to produce a fully-formed PLAN.md entry with correct phase ID, dependencies, tasks, key files, and Definition of Done. Asks the user only for product-intent decisions that cannot be inferred from code. Does NOT write code or modify any source files.
version: 2.0.0
---

## Overview

This skill takes a brief feature description and produces a complete, correctly formatted PLAN.md entry through autonomous codebase research. It asks the user only for product-intent decisions that cannot be inferred from existing code and documentation. It does not modify any files.
If you are instructed to ask questions then use the ask tool if possible. If you are not instructed to ask questions, do not ask any questions.

---

## Step 1: Accept the feature description

The only required input is a brief description of the feature. Even a single sentence is sufficient. Accept it and proceed immediately to Step 2 without asking any questions.

The one exception: if the description is so vague that no research could anchor it (for example, "add a feature" with no domain hint), ask for a slightly more specific description. Do not ask a question list — ask for one clarifying sentence and then proceed.

---

## Step 2: Deep codebase research (autonomous — no user input)

Read the following files in order. Extract the specific information listed for each.

### 2a. Read `PLAN.md`

Extract:
- The highest existing top-level numbered phase ID (e.g. Phase 11 → next would be 12).
- All lettered group headers (e.g. ### Phase A, ### Phase B) and the highest sub-phase ID within each group (e.g. E5 → next in group E would be E6).
- The status of every phase: completed (marked ✅), pending, or deferred.
- The full dependency graph: every "Depends on" and "Parallelisable with" field across all phases.
- The two Markdown heading conventions in use: `##` for top-level numbered phases, `####` for lettered sub-phases, `###` for lettered group headers.

After extracting the above, check whether the lettered group most likely to contain the new sub-phase is marked "Deferred". If so, note this finding explicitly — include a prominent warning in the Step 3 summary message before asking any questions. Rule 8 in Step 4 remains as a safety-net check but the primary warning must appear in Step 3.

### 2b. Read `ARCHITECTURE.md`

Extract:
- The component hierarchy and existing file tree.
- The data-flow pipeline and calculation pipeline.
- The API response schema (field names, types, structure).

Use this to identify which existing source files the feature would modify and what new files would need to be created.

### 2c. Read `TECH_CHOICES.md`

Check whether the feature fits within the existing technology decisions. Note any case where the feature would require a new dependency or library not already present. Flag this in Step 3 if so.

### 2d. Read relevant source files

Based on what ARCHITECTURE.md describes and what the feature description implies, read the actual source files most likely to be affected. The goal is to ground task descriptions and file paths in reality — inferred paths that are not confirmed by reading the files are unreliable.

Common candidates based on this project's structure:
- `backend/main.py`, `backend/calculator.py`, `backend/scorer.py`, `backend/models.py`
- `frontend/app.js`, `frontend/sky-map.js`, `frontend/weather.js`, `frontend/ui.js`
- Any file referenced by name in ARCHITECTURE.md for the relevant component.

### 2e. Infer all entry fields

From the research above, infer all of the following before presenting anything to the user:

- **Entry type**: top-level numbered phase (`##`), sub-phase under an existing lettered group (`####`), or a new lettered group header (`###`) followed by its first sub-phase. Base this on the feature's scope and thematic fit with existing groups.
- **Phase ID**: the next available ID in the chosen sequence. If there is a numbering gap in PLAN.md, pick the next sequential ID after the highest existing one and state the reasoning.
- **Dependencies**: which existing phases must be complete before this one can start. Derive this from the dependency graph and from which phases produce the code or API surface this feature builds on.
- **Parallelizability**: which pending or in-progress phases could run concurrently without blocking each other.
- **Tasks list**: concrete imperative-verb tasks (Create, Build, Extend, Add, Modify) with real file paths rooted in `backend/` or `frontend/`, ordered backend tasks first then frontend tasks.
- **Key files** (for lettered sub-phases): list each file as create or modify with a brief description of the change.
- **Intended Outcome**: one paragraph summarizing what the completed phase delivers, written in present tense.
- **Definition of Done**: at least four concrete, falsifiable criteria referencing observable artifacts — HTTP status codes, DOM elements, function return values, Pydantic field names, specific Swedish UI strings, file paths, etc. No vague criteria.

---

## Step 3: Show research summary and ask only un-inferable questions (0–2 max)

Present a **"Here is what I inferred"** summary in a single message covering:
- Entry type and suggested phase ID (with reasoning if non-obvious).
- Inferred dependencies and parallelizability.
- Planned file list (files to create and files to modify, with paths).
- Whether any new technology is required that is not in TECH_CHOICES.md.

Then apply the minimal question policy: only ask about things that genuinely cannot be determined from code, PLAN.md, ARCHITECTURE.md, or TECH_CHOICES.md. These are typically:
- Ambiguous scope boundaries (e.g. "should this replace the existing feature or appear alongside it?").
- Product-intent choices that have no technical answer (e.g. "should the timeout be 10 s or 30 s?").
- Conflicting design directions found in existing code that require a human decision.

Cap at 0–2 questions. Present them in the same message as the summary. If there are zero questions, say so explicitly and invite the user to correct any wrong assumptions before you proceed.

Wait for the user to confirm the summary (and answer any questions) before proceeding to Step 4.

---

## Step 4: Validate the draft (self-correction — no user input for most rules)

Apply all eleven rules below to your own draft. Self-correct silently where the rule can be applied mechanically. Only surface an issue to the user if self-correction is impossible (e.g. a broken dependency reference you cannot resolve without product context).

1. Every phase ID listed in "Depends on" must exist in PLAN.md. If one does not, remove it or replace it with the closest correct ID.
2. The chosen phase ID must not already exist in PLAN.md. If it does, increment to the next available ID.
3. Each Definition of Done item must reference a concrete observable artifact. Rewrite any item that uses vague language such as "works correctly", "looks good", "is correct", or "functions as expected".
4. Any string that will be visible to the user in the browser (labels, button text, tooltips, status messages) must be written in Swedish. Code identifiers and file paths are exempt. Rewrite any English UI strings in Tasks or Definition of Done.
5. All file paths must be rooted in `backend/` or `frontend/`. If the feature is purely infrastructure (e.g. a config file at project root), relax this rule and add a note explaining the exception.
6. There must be at least four Definition of Done items. If fewer were inferred, add concrete ones based on what the feature must produce.
7. If the task list has more than approximately ten items, flag this to the user and suggest splitting into two sub-phases. Do not proceed past this point without user confirmation on how to handle the split. After user confirmation on whether to split, resume validation from Rule 8 with the (possibly revised) task list.
8. If the parent lettered group for a sub-phase is marked "Deferred" in PLAN.md, warn the user explicitly — for example: "Phase C is currently deferred — this sub-phase will also be treated as deferred. Do you want to proceed anyway?" Wait for confirmation.
9. Backend tasks must appear before frontend tasks in the task list. Reorder silently if needed, then note that reordering was applied.
10. Strip any accidental status suffix from the phase title (e.g. remove "— ✅" or "— Deferred" from the title field itself).
11. If a new technology is required that is not in TECH_CHOICES.md, flag it explicitly and note that TECH_CHOICES.md may also need updating — but this skill does not update it.

---

## Step 5: Produce the formatted Markdown entry

Choose the correct template based on entry type. Fill every placeholder from your research. Present the complete entry in a fenced `markdown` code block.

### Template A — Top-level numbered phase (`##` heading)

```markdown
## Phase N: Title

**Status:** Pending
**Depends on:** Phase X
**Parallelisable with:** Phase Y

### Tasks
- Build `backend/path/to/file.py` — description
- Create `frontend/path/to/file.js` — description

### Intended Outcome
One paragraph describing what this phase delivers, written in present tense.

### Definition of Done
- [ ] Concrete observable criterion referencing a specific artifact
- [ ] Another falsifiable criterion
- [ ] At least four total
- [ ] …

---
```

Notes on Template A:
- `**Status:** Pending` is present only in top-level numbered phases and never in lettered sub-phases.
- Omit the `> **Note:**` block entirely if there are no caveats. Include it only if there is genuine caveat text to communicate.
- Use colon-inside-bold style: `**Depends on:**` and `**Parallelisable with:**` — no colon after the closing `**`.

### Template B — Lettered sub-phase (`####` heading)

```markdown
#### Phase X9: Title

**Depends on:** Phase X8
**Parallelisable with:** Phase X7

**Intended Outcome**
One paragraph describing what this sub-phase delivers, written in present tense.

**Definition of Done**
- [ ] Concrete observable criterion
- [ ] At least four total

**Key files**
- Create `frontend/path/to/file.js` — description of what this file contains
- Modify `backend/path/to/file.py` — description of what changes

---
```

Notes on Template B:
- No `**Status:**` field.
- Key files uses action verbs: Create, Modify, Extend, Add.
- Omit the `> **Note:**` block unless there is genuine caveat text.
- There is no separate `### Tasks` block for lettered sub-phases. The `**Key files**` section serves the same role: each line is a task, expressed as an action verb + file path + description. Do NOT add a `### Tasks` block to a sub-phase entry.

### Template C — New lettered group header (`###` heading) followed by first sub-phase

```markdown
### Phase X: Group Name

One paragraph describing the group's overall scope and the internal dependency structure of its sub-phases.

#### Phase X1: First Sub-phase Title

**Depends on:** Phase Y
**Parallelisable with:** None

**Intended Outcome**
One paragraph describing what this sub-phase delivers.

**Definition of Done**
- [ ] Concrete observable criterion
- [ ] At least four total

**Key files**
- Create `frontend/path/to/file.js` — description
- Modify `backend/path/to/file.py` — description

---
```

Notes on Template C:
- The sub-phase inside Template C follows the same conventions as Template B. There is no separate `### Tasks` block. The `**Key files**` section is the task list: each line is an action verb + file path + description.

---

## Step 6: State the insertion point and await confirmation

After the code block, state the exact location in PLAN.md where this entry should be inserted. Example: "Insert after the `#### Phase E5` entry, before the `### Confirmed Decisions` section." Derive the insertion point from the phase ordering and dependency graph — do not guess.

Verify that the insertion point appears after all phases listed in "Depends on" within the PLAN.md file — not just by phase number, but by actual position in the document. If a dependency appears later in the file (e.g. in a deferred section), note the inconsistency to the user.

Do NOT insert the entry into PLAN.md. Wait for the user to explicitly confirm or request edits.
Use the ask tool for this.

Once the user approves the entry, suggest the appropriate downstream implementation skill based on the feature's scope:
- `full-stack-feature` — changes to both backend and frontend
- `backend-fix` — pure backend or calculation changes
- `frontend-enhancement` — UI changes using existing API data
- `sky-map-feature` — visual sky map layer or interaction
- `cleanup-refactor` — dead-code removal or quality improvement
- `docs-sync` — documentation-only changes

---

## Step 7: No code or file changes

This skill produces Markdown only. It does not modify PLAN.md, source files, test files, or any other file. After the user approves the entry, routing to an implementation skill (Step 6) is the correct next action.

---

## Edge cases

Handle the following situations where they arise, at the point in the steps where they become relevant:

- **Description too vague**: if no codebase research could anchor the feature (e.g. "add a feature"), ask for one more specific sentence. Do not present a question list.
- **Feature spans multiple lettered groups**: pick the best thematic fit and note the mismatch in the summary. Ask whether a new group is needed. This question counts toward the 0–2 question cap. If the cap would be exceeded, the group-structure question takes priority over lower-stakes scope questions.
- **Feature requires a technology not in TECH_CHOICES.md**: flag it in Step 3 and again in Step 4 Rule 11. Note that TECH_CHOICES.md may need updating separately.
- **Numbering gap in PLAN.md**: pick the next sequential ID after the highest existing one and state the reasoning explicitly.
- **Feature touches no `backend/` or `frontend/` files** (e.g. pure config or CI change): relax the file-path rule and add a note explaining the exception.
- **Parent lettered group is Deferred**: warn prominently in the Step 3 summary (detected during Step 2a). Step 4 Rule 8 is a safety-net repeat of the same warning. Wait for user confirmation at Step 4 Rule 8 before producing the formatted entry.
