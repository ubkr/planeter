# Development Plan

This directory contains the project's phased implementation plan, split into thematic files. Each file covers one logical group of related phases.

---

## Directory Structure

```
development_plan/
├── README.md                        ← this file
├── phase_c_extended_bodies.md       ← deferred / not yet started
├── phase_d_notifications.md         ← deferred / not yet started
└── completed/                       ← fully implemented groups
    ├── 01_core_mvp.md
    ├── 02_visibility_scoring.md
    ├── 03_solar_system_static.md
    ├── 04_sky_map.md
    ├── 05_observation_tips_and_events.md
    ├── 06_ui_refinements_and_3d.md
    ├── 07_solar_system_interactive.md
    └── 08_artificial_objects.md
```

Files in the **root** of this directory are upcoming or deferred work. Files in **`completed/`** are fully implemented.

---

## Workflow

### Starting a new phase group
1. Create a new file in `development_plan/` following the file template below.
2. Assign it a descriptive name, e.g. `phase_h_user_accounts.md`.

### During implementation
- Work through the Definition of Done checklist item by item.
- Check off items with `[x]` as they are verified in code.

### Marking a group as complete
1. Confirm every DoD item is checked `[x]`.
2. Change the **Status** line at the top of the file to `Completed`.
3. Move the file into `completed/` and prefix it with the next available two-digit number (e.g. `09_user_accounts.md`).

---

## File Template

Use this template when creating a new development plan file.

```markdown
# <Group Title> (<Phase IDs>)

**Status:** Planned | In Progress | Completed

**Phases included:** Phase X (Short Name), Phase Y (Short Name), ...

**Depends on:** Phase / group this work requires to be done first (or "none")

---

## Intended Outcome (User Perspective)

One or more paragraphs describing what the user sees and experiences after this
group is implemented. Write in plain language as if explaining to someone who
has never seen the codebase. Avoid technical terms where possible. Focus on
what the user can do, see, or understand — not on how the code is structured.

---

## Definition of Done

### Phase X — Short Name
- [ ] Concrete, verifiable item
- [ ] Concrete, verifiable item
- [ ] ...

### Phase Y — Short Name
- [ ] Concrete, verifiable item
- [ ] ...

---

## Notes (optional)

Architecture decisions, deferred sub-phases, known constraints, or anything
that should inform the implementer but is not a DoD item.
```

### Writing good DoD items

Each DoD item should be independently verifiable — someone who was not involved in writing the plan should be able to check it against the running app or the source code without ambiguity. Prefer:

- Specific values: `"returns HTTP 200"`, `"score above 70"`, `"renders as a CSS2D overlay"`
- Observable behaviour: `"hovering the dot shows a tooltip with…"`, `"the slider resets on location change"`
- File-level facts: `"frontend/data/bright-stars.json contains at least 40 entries"`

Avoid vague items like `"works correctly"` or `"is implemented"`.

### Writing a good Intended Outcome

The Intended Outcome is written **from the user's point of view**, not the developer's. It answers: *What can the user now do that they could not do before?* Describe the experience, not the implementation. A useful test: if you removed all code references and technical terms, would a non-technical product owner understand what was delivered? If yes, the outcome is well written.
