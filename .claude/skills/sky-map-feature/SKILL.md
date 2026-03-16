---
name: sky-map-feature
description: Use this skill when adding a new visual layer or interaction to the sky map. Trigger when the request mentions adding something to the sky map or sky dome — new objects, grid overlays, labels, interactions. Always implements both the 2D SVG renderer and the 3D Three.js renderer.
version: 1.0.0
---

## Steps

1. Read `frontend/js/components/sky-map.js` (2D SVG renderer) and `frontend/js/components/sky-map-3d.js` (3D Three.js renderer) in full to understand existing rendering patterns before writing any new code.

2. Read `frontend/js/astro-projection.js` and `frontend/js/components/sky-map.js` to understand the coordinate conversion utilities: `altAzToXY` (exported from `sky-map.js`) for 2D projection, and `altAzToCartesian` and `raDecToAltAz` (in `astro-projection.js`) for 3D.

3. Read `frontend/js/main.js` to understand how observation data flows from the API response into both renderer instances.

4. Plan the 2D implementation first. Use SVG elements with CSS classes defined in `frontend/css/components/sky-map.css`. Do not create inline styles on SVG elements — all visual properties must go through CSS classes.

5. Plan the 3D implementation using Three.js primitives. Reference styles from `frontend/css/components/sky-map-3d.css`. For Three.js documentation, check the bundled library at `frontend/lib/three.module.min.js` to confirm the version in use, then consult the official Three.js docs at https://threejs.org/docs/ for that version. Do not rely on MCP tools that may not be available.

6. Both renderers must handle the "below horizon" case consistently. In the 2D renderer, objects below the horizon get reduced opacity outside the horizon ring. In the 3D renderer, objects below the horizon are hidden by the ground plane. The visual treatment may differ, but the logical threshold (altitude < 0) must be the same.

7. In the 3D renderer, build all geometry and materials once per data update — never inside the render loop. The render loop must remain side-effect-free and purely draw what was already set up.

8. Keep the `plotBodies()` method signature identical between the 2D and 3D classes. If the method needs a new parameter, add it to both classes at the same time and update all call sites in `main.js` together.

9. `SkyMap3D` is lazy-loaded via dynamic `import()` on the first '3D' tab activation in `main.js`. `SkyMap` is imported statically. Any code path that calls into `skyMap3d` must guard against a `null` instance — do not change this lazy-load pattern.

10. After implementing both renderers, verify in `main.js` that both receive the same data and are called at the same points in the update cycle.

11. After implementation, run `node frontend/tests/test-astro-projection.mjs` to verify projection math is still correct. If any backend coordinate data was changed, also run `pytest backend/tests/`.
