---
name: frontend-enhancement
description: Use this skill when adding or modifying UI elements using data already available in the API response or from static content. Trigger when the request is about adding badges, toggles, sections, or visual elements to existing cards, and no new backend computation is needed.
version: 1.0.0
---

## Steps

1. Read `frontend/css/tokens.css` to understand all available design tokens before writing any CSS.

2. Read the target component file to understand the existing rendering structure, element hierarchy, and CSS class naming conventions.

3. Read `frontend/js/main.js` to understand initialization order and how data flows from API responses to components.

4. Check `frontend/js/data/` for existing static data file patterns if the enhancement involves hardcoded or lookup data rather than live API data. Follow the pattern of existing files like `planet-descriptions.js` for any new static data file — the project has no build step, so CommonJS or bundler-specific syntax is not allowed.

5. Add HTML elements following the structural patterns already present in the component. Do not invent a new pattern when an equivalent one already exists in the file.

6. Use only existing CSS token variables for all color, spacing, and typography values. If a new token is genuinely required, add it to `tokens.css` and document why the existing tokens are insufficient.

7. All user-facing strings must be in Swedish.

8. Verify the enhancement works at both 375 px (mobile) and 1200 px (desktop) viewport widths before considering it done.

9. If the enhancement introduces a new module or component, wire it into `main.js` following the existing instantiation and initialization pattern used by other components.
