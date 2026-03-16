---
name: docs-sync
description: Use this skill after completing any feature phase, or when the Reviewer flags stale documentation. Also use it when the user explicitly asks to update docs. Makes no code changes — only updates ARCHITECTURE.md, TECH_CHOICES.md, CLAUDE.md, and PLAN.md to reflect current implementation.
version: 1.0.0
---

## Steps

1. Read all four documentation files in full: `ARCHITECTURE.md`, `TECH_CHOICES.md`, `CLAUDE.md`, and `PLAN.md`.

2. Grep the codebase for components, Pydantic models, and API routes to find anything implemented but not yet documented, or documented but no longer present in code.

3. Update `ARCHITECTURE.md` so that the component hierarchy, data flow description, API response schema, and scoring algorithm table all exactly match the current code. Remove any sections that describe removed features.

4. Update `PLAN.md` to mark completed phases as done, update Definition of Done checklist items to reflect current reality, and remove references that are no longer accurate.

5. Update `TECH_CHOICES.md` to document any new library dependencies added since the last doc sync. Each new dependency must include a rationale for why it was chosen over alternatives.

6. Update `CLAUDE.md` if the stack description or core features list has changed.

7. Scan for any documentation references to files, routes, selectors, or component names that no longer exist in the codebase. The string "norrsken" is one known historical example; treat any mismatch between documented and actual structure the same way. Remove all such stale references from documentation files.

8. Documentation must describe only the current state of the implementation. Do not add changelogs, migration notes, or historical commentary. If something no longer exists in the code, it must not appear in the docs.

9. Make no changes to source code files (`.py`, `.js`, `.css`, `.html`). This skill is documentation-only.
