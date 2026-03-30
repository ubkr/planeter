/**
 * sky-map-3d.js - Immersive 3D sky-dome viewer using Three.js.
 *
 * Renders a WebGL hemisphere scene with:
 *   - A dark celestial sphere (inside-out, camera at origin)
 *   - A flat horizon ground plane
 *   - An alt-azimuth grid (altitude rings at 0°/30°/60°, azimuth lines every 45°)
 *   - Cardinal direction labels (N, O, S, V) and intercardinal labels (NO, SO, SV, NV) rendered as canvas-texture sprites
 *   - OrbitControls for drag-to-look navigation (zoom and pan disabled)
 *   - Celestial body sprites (planets, Sun, Moon) with CSS2D tooltip labels
 *
 * Import paths assume the file lives at:
 *   frontend/js/components/sky-map-3d.js
 */

import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import { CSS2DRenderer, CSS2DObject } from 'three/addons/renderers/CSS2DRenderer.js';
import { altAzToCartesian, raDecToAltAz } from '../astro-projection.js';
import { azimuthToCompass } from '../utils.js';

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

/** Radius of the celestial sphere and horizon circle. */
const SPHERE_RADIUS = 500;

/** Altitude rings drawn at these elevations (degrees). */
const ALT_RINGS = [0, 30, 60];

/** Azimuth lines drawn at these bearings (degrees, N=0, clockwise). */
const AZ_LINES = [0, 45, 90, 135, 180, 225, 270, 315];

/** Number of points used to approximate each ring as a polyline. */
const RING_SEGMENTS = 128;

/** Grid line colour — bright enough to be clearly visible against the dark sky background. */
const GRID_COLOR = 0x4488bb;

/** Grid lines are drawn at this fraction of SPHERE_RADIUS to avoid z-fighting with the sphere surface. */
const GRID_RADIUS = SPHERE_RADIUS * 0.98;

/** Constellation lines sit slightly inside the grid to render behind it. */
const CONSTELLATION_RADIUS = SPHERE_RADIUS * 0.96;

/** Background stars sit slightly inside the constellation sphere so they render behind lines. */
const STAR_RADIUS = SPHERE_RADIUS * 0.95;

/** Constellation line colour — must match --color-text-muted in tokens.css. */
const CONSTELLATION_LINE_COLOR = 0x53627d;

/** Default camera field-of-view in degrees. Matches the initial PerspectiveCamera argument. */
const DEFAULT_FOV = 60;

/** Cardinal label definitions: text (Swedish), azimuth, and canvas text colour. */
const CARDINALS = [
    { text: 'N', azimuth: 0   },
    { text: 'O', azimuth: 90  },
    { text: 'S', azimuth: 180 },
    { text: 'V', azimuth: 270 },
];

/** Intercardinal label definitions: text (Swedish), azimuth. */
const INTERCARDINALS = [
    { text: 'NO', azimuth: 45  },
    { text: 'SO', azimuth: 135 },
    { text: 'SV', azimuth: 225 },
    { text: 'NV', azimuth: 315 },
];

/**
 * Colour for each celestial body used when rendering glow sprites.
 * Keys are lowercase body names.
 */
const BODY_COLORS = {
    mercury: '#9ca3af',
    venus:   '#fbbf24',
    mars:    '#ef4444',
    jupiter: '#f59e0b',
    saturn:  '#d4a017',
    sun:     '#f59e0b', // intentionally same amber as jupiter — both use #f59e0b by design
    moon:    '#c084fc',
};

// ---------------------------------------------------------------------------
// Private helpers
// ---------------------------------------------------------------------------

/**
 * Build a THREE.Line that traces one altitude ring at a given elevation.
 *
 * @param {number} altitudeDeg - Elevation in degrees (0 = horizon, 60 = high).
 * @param {THREE.Material} material
 * @returns {THREE.Line}
 */
function buildAltitudeRing(altitudeDeg, material) {
    const points = [];
    for (let i = 0; i <= RING_SEGMENTS; i++) {
        const az = (i / RING_SEGMENTS) * 360;
        const { x, y, z } = altAzToCartesian(altitudeDeg, az, GRID_RADIUS);
        points.push(new THREE.Vector3(x, y, z));
    }
    const geo = new THREE.BufferGeometry().setFromPoints(points);
    return new THREE.Line(geo, material);
}

/**
 * Build a THREE.Line that traces one azimuth great-circle arc from the
 * horizon (alt=0°) up to the zenith (alt=90°).
 *
 * @param {number} azimuthDeg - Azimuth bearing in degrees.
 * @param {THREE.Material} material
 * @returns {THREE.Line}
 */
function buildAzimuthLine(azimuthDeg, material) {
    const points = [];
    for (let i = 0; i <= RING_SEGMENTS; i++) {
        const alt = (i / RING_SEGMENTS) * 90;
        const { x, y, z } = altAzToCartesian(alt, azimuthDeg, GRID_RADIUS);
        points.push(new THREE.Vector3(x, y, z));
    }
    const geo = new THREE.BufferGeometry().setFromPoints(points);
    return new THREE.Line(geo, material);
}

/**
 * Create a canvas texture containing a single text label, then wrap it in a
 * THREE.Sprite so it always faces the camera.
 *
 * @param {string} text - Label text (e.g. 'N').
 * @returns {THREE.Sprite}
 */
function buildCardinalSprite(entry, options = {}) {
    const {
        fontSize    = 'bold 72px sans-serif',
        fillStyle   = '#aabbcc',
        scaleFactor = 0.07,
    } = options;

    // Render the label onto an off-screen canvas.
    // Canvas is 192×128 (3:2) so two-character labels like "NO"/"SV"/"NV"
    // have sufficient horizontal margin at bold 72px.
    const canvas = document.createElement('canvas');
    canvas.width  = 192;
    canvas.height = 128;
    const ctx = canvas.getContext('2d');

    ctx.clearRect(0, 0, 192, 128);
    ctx.fillStyle    = fillStyle;
    ctx.font         = fontSize;
    ctx.textAlign    = 'center';
    ctx.textBaseline = 'middle';
    ctx.fillText(entry.text, 96, 64);

    const texture = new THREE.CanvasTexture(canvas);
    const material = new THREE.SpriteMaterial({ map: texture, transparent: true, depthWrite: false });
    const sprite = new THREE.Sprite(material);

    // Scale the sprite to match the 3:2 canvas aspect ratio so the text
    // is not stretched.  scaleH drives the vertical size; scaleW is 1.5×.
    const scaleH = SPHERE_RADIUS * scaleFactor;
    const scaleW = scaleH * 1.5;
    sprite.scale.set(scaleW, scaleH, 1);

    return sprite;
}

/**
 * Build the complete grid group: altitude rings + azimuth lines.
 *
 * @returns {THREE.Group}
 */
function buildGrid() {
    const group = new THREE.Group();
    const mat   = new THREE.LineBasicMaterial({ color: GRID_COLOR });

    for (const alt of ALT_RINGS) {
        group.add(buildAltitudeRing(alt, mat));
    }
    for (const az of AZ_LINES) {
        group.add(buildAzimuthLine(az, mat));
    }

    return group;
}

/**
 * Build the group of cardinal direction sprites placed just above the horizon.
 *
 * @returns {THREE.Group}
 */
function buildCardinalLabels() {
    const group = new THREE.Group();
    // Altitude slightly above 0° so sprites clear the ground plane.
    const labelAlt = 4;
    const labelRadius = SPHERE_RADIUS * 0.92;

    for (const entry of CARDINALS) {
        const { x, y, z } = altAzToCartesian(labelAlt, entry.azimuth, labelRadius);
        const sprite = buildCardinalSprite(entry);
        sprite.position.set(x, y, z);
        group.add(sprite);
    }

    for (const entry of INTERCARDINALS) {
        const { x, y, z } = altAzToCartesian(labelAlt, entry.azimuth, labelRadius);
        const sprite = buildCardinalSprite(entry, {
            fillStyle: 'rgba(170, 187, 204, 0.75)',
        });
        sprite.position.set(x, y, z);
        group.add(sprite);
    }

    return group;
}

/**
 * Create a CanvasTexture rendering a filled circle with a soft radial gradient
 * glow for use as a body sprite.
 *
 * @param {string} color - CSS colour string (e.g. '#fbbf24').
 * @returns {THREE.CanvasTexture}
 */
function buildBodyTexture(color) {
    const canvas = document.createElement('canvas');
    canvas.width  = 64;
    canvas.height = 64;
    const ctx = canvas.getContext('2d');

    // Radial gradient: body colour at centre, transparent at edge.
    const gradient = ctx.createRadialGradient(32, 32, 0, 32, 32, 32);
    gradient.addColorStop(0,   color);
    gradient.addColorStop(1,   'rgba(0,0,0,0)');

    ctx.fillStyle = gradient;
    ctx.fillRect(0, 0, 64, 64);

    // Solid filled circle in the centre.
    ctx.beginPath();
    ctx.arc(32, 32, 20, 0, Math.PI * 2);
    ctx.fillStyle = color;
    ctx.fill();

    return new THREE.CanvasTexture(canvas);
}

/**
 * Compute the sprite scale for a celestial body based on its magnitude.
 * Brighter bodies (lower magnitude) produce a larger sprite.
 *
 * @param {number} magnitude
 * @returns {number} World-space scale value.
 */
function bodyScale(magnitude) {
    return SPHERE_RADIUS * Math.max(0.025, Math.min(0.08, 0.055 - magnitude * 0.008));
}

// ---------------------------------------------------------------------------
// SkyMap3D class
// ---------------------------------------------------------------------------

/**
 * SkyMap3D manages a WebGL Three.js scene that renders an immersive 3D sky dome.
 *
 * Lifecycle:
 *   const map3d = new SkyMap3D(containerEl);
 *   map3d.activate();     // start rendering
 *   map3d.deactivate();   // pause rendering
 *   map3d.dispose();      // full teardown
 *
 * Body plotting:
 *   map3d.plotBodies(planets, sun, moon, events);
 *   Safe to call before activate() — arguments are stored and replayed once
 *   the scene is ready.
 */
export default class SkyMap3D {
    /**
     * @param {HTMLElement} container - The DOM element that will contain the canvas.
     *   Does NOT modify the container until activate() is called.
     */
    constructor(container) {
        this.container = container;

        // All Three.js state is null until activate() initialises it.
        this._renderer    = null;
        this._cssRenderer = null;
        this._scene       = null;
        this._camera      = null;
        this._controls    = null;

        // Body, label, constellation, and star groups — created once in _initScene().
        this._bodiesGroup        = null;
        this._labelsGroup        = null;
        this._constellationsGroup = null;
        this._starsGroup         = null;

        // Tracks only the CSS2DObjects added by _addBodySprite(), so _clearBodies()
        // can remove them from _labelsGroup without touching star label objects.
        this._bodyLabelsArray = [];

        // Raycaster for cursor feedback on body sprites.
        this._raycaster = null;
        this._pointer   = null;

        // Tracks the label element currently under the pointer, so mouseout can
        // be dispatched when the pointer moves away.
        this._hoveredLabel = null;

        // Tracks whether the render loop is currently active, used to prevent
        // double-registration of the window resize listener.
        this._active = false;

        // Guard against duplicate wheel event listener registration.
        this._wheelListenerAttached = false;
        // Touch pinch-zoom state. _pinchStartDistance holds the pixel distance
        // between the two touch points at the start of a pinch gesture.
        this._pinchStartDistance = null;
        // Guard against duplicate touch event listener registration.
        this._touchListenerAttached = false;

        // Bound resize handler so it can be removed cleanly.
        this._onResize = this._handleResize.bind(this);

        // Deferred plotBodies arguments stored when activate() has not yet run.
        this._pendingBodies = null;

        // Deferred plotStars arguments stored when activate() has not yet run.
        this._pendingStars = null;

        // Deferred plotConstellations arguments stored when activate() has not yet run.
        this._pendingConstellations = null;
    }

    // -----------------------------------------------------------------------
    // Public API
    // -----------------------------------------------------------------------

    /**
     * Activate the 3D view.
     *
     * On the first call: builds the full scene (renderer, camera, controls,
     * geometry). On subsequent calls: simply resizes the canvas to the current
     * container dimensions and restarts the render loop.
     *
     * @throws {Error} If WebGL is not supported by the browser.
     */
    activate() {
        if (!window.WebGLRenderingContext) {
            throw new Error('WebGL stöds inte av din webbläsare');
        }

        if (this._renderer === null) {
            this._initScene();
        }

        this._handleResize();
        this._startLoop();

        if (!this._active) {
            window.addEventListener('resize', this._onResize);
            this._active = true;
        }

        // Replay any plotBodies() call that arrived before the scene was ready.
        if (this._pendingBodies !== null) {
            const { planets, sun, moon, events } = this._pendingBodies;
            this._pendingBodies = null;
            this.plotBodies(planets, sun, moon, events);
        }

        // Replay any plotStars() call that arrived before the scene was ready.
        if (this._pendingStars !== null) {
            const p = this._pendingStars;
            this._pendingStars = null;
            this.plotStars(...p);
        }

        // Replay any plotConstellations() call that arrived before the scene was ready.
        if (this._pendingConstellations !== null) {
            const p = this._pendingConstellations;
            this._pendingConstellations = null;
            this.plotConstellations(...p);
        }
    }

    /**
     * Deactivate the 3D view.
     *
     * Stops the render loop but keeps all Three.js objects alive so activate()
     * can restart quickly without rebuilding the scene.
     */
    deactivate() {
        this._stopLoop();
        window.removeEventListener('resize', this._onResize);
        this._active = false;
    }

    /**
     * Full teardown: stop the render loop, release GPU resources, and remove
     * the canvas from the DOM.
     */
    dispose() {
        this._stopLoop();
        window.removeEventListener('resize', this._onResize);

        if (this._renderer !== null) {
            this._renderer.dispose();
            if (this._renderer.domElement.parentNode) {
                this._renderer.domElement.parentNode.removeChild(this._renderer.domElement);
            }
            this._renderer = null;
        }

        if (this._cssRenderer !== null) {
            if (this._cssRenderer.domElement.parentNode) {
                this._cssRenderer.domElement.parentNode.removeChild(this._cssRenderer.domElement);
            }
            this._cssRenderer = null;
        }

        if (this._controls !== null) {
            this._controls.dispose();
        }
        this._controls            = null;
        this._camera              = null;
        this._scene               = null;

        if (this._starsGroup !== null) {
            this._clearStars();
            this._starsGroup = null;
        }

        this._bodiesGroup         = null;
        this._labelsGroup         = null;
        this._constellationsGroup = null;
        this._bodyLabelsArray     = [];
        this._raycaster           = null;
        this._pointer             = null;
    }

    /**
     * Plot celestial bodies (planets, Sun, Moon) as glow sprites with CSS2D
     * tooltip labels into the 3D scene.
     *
     * Safe to call before activate() — arguments are stored and replayed once
     * the scene is ready. Safe to call multiple times — all previous sprites
     * and labels are disposed and removed before rebuilding.
     *
     * Bodies whose altitude is strictly below 0° are not rendered.
     *
     * @param {Object[]} planets - Array of planet objects from the API.
     *   Each must have: name, name_sv, altitude_deg, azimuth_deg, direction, magnitude.
     * @param {Object} sun - Sun object with elevation_deg and azimuth_deg.
     * @param {Object} moon - Moon object with elevation_deg, azimuth_deg, illumination.
     * @param {Object[]} [events=[]] - Astronomical event objects (reserved for E4).
     */
    plotBodies(planets, sun, moon, events = []) {
        // Defer if the scene has not been initialised yet.
        if (this._scene === null) {
            this._pendingBodies = { planets, sun, moon, events };
            return;
        }

        if (!Array.isArray(planets)) return;

        // Clear previous sprites (dispose GPU resources) and labels.
        this._clearBodies();

        // --- Planets ---
        for (const planet of planets) {
            if (planet.altitude_deg < 0) continue;

            const color = BODY_COLORS[planet.name.toLowerCase()] ?? '#ffffff';
            const tooltipText =
                `${planet.name_sv}\n` +
                `Höjd: ${planet.altitude_deg.toFixed(1)}°\n` +
                `Riktning: ${planet.direction}\n` +
                `Magnitud: ${planet.magnitude.toFixed(1)}`;

            this._addBodySprite(
                planet.altitude_deg,
                planet.azimuth_deg,
                color,
                planet.magnitude,
                planet.name_sv,
                tooltipText,
                { name_sv: planet.name_sv, altitude_deg: planet.altitude_deg, azimuth_deg: planet.azimuth_deg, direction: planet.direction, magnitude: planet.magnitude, type: 'planet' },
            );
        }

        // --- Sun ---
        if (sun && sun.elevation_deg >= 0) {
            const tooltipText =
                `Solen\n` +
                `Höjd: ${sun.elevation_deg.toFixed(1)}°\n` +
                `Riktning: ${sun.direction || sun.azimuth_deg.toFixed(0) + '°'}`;

            // Use a fixed large scale for the Sun (1.5× the brightest-star formula).
            const sunMagnitude = -26; // effectively forces max scale, overridden below
            this._addBodySprite(
                sun.elevation_deg,
                sun.azimuth_deg,
                BODY_COLORS.sun,
                sunMagnitude,
                'Solen',
                tooltipText,
                { name_sv: 'Solen', altitude_deg: sun.elevation_deg, azimuth_deg: sun.azimuth_deg, type: 'sun' },
                /* scaleFactor */ 1.5,
            );
        }

        // --- Moon ---
        if (moon && moon.elevation_deg >= 0) {
            const tooltipText =
                `Månen\nHöjd: ${moon.elevation_deg.toFixed(1)}°\nRiktning: ${moon.direction || moon.azimuth_deg.toFixed(0) + '°'}\nBelysning: ${Math.round(moon.illumination * 100)}%`;

            this._addBodySprite(
                moon.elevation_deg,
                moon.azimuth_deg,
                BODY_COLORS.moon,
                // Use a fixed moderate magnitude so the Moon is distinctly large.
                -12,
                'Månen',
                tooltipText,
                { name_sv: 'Månen', altitude_deg: moon.elevation_deg, azimuth_deg: moon.azimuth_deg, type: 'moon' },
                /* scaleFactor */ 1.3,
            );
        }

        // TODO E4: render event indicators
    }

    /**
     * Decrease camera FOV to zoom in, clamped to a minimum of 20°.
     *
     * @param {number} [step=10] - Degrees to decrease FOV by.
     */
    zoomIn(step = 10) {
        if (this._camera === null) return;
        this._camera.fov = Math.max(20, this._camera.fov - step);
        this._camera.updateProjectionMatrix();
    }

    /**
     * Increase camera FOV to zoom out, clamped to a maximum of 90°.
     *
     * @param {number} [step=10] - Degrees to increase FOV by.
     */
    zoomOut(step = 10) {
        if (this._camera === null) return;
        this._camera.fov = Math.min(90, this._camera.fov + step);
        this._camera.updateProjectionMatrix();
    }

    /**
     * Reset camera FOV to the default value (DEFAULT_FOV = 60°).
     */
    resetZoom() {
        if (this._camera === null) return;
        this._camera.fov = DEFAULT_FOV;
        this._camera.updateProjectionMatrix();
    }

    /**
     * Toggle visibility of constellation lines and labels.
     *
     * @param {boolean} enabled - True to show constellations, false to hide.
     */
    setConstellationsVisible(enabled) {
        if (this._constellationsGroup === null) return;
        this._constellationsGroup.visible = enabled;
    }

    /**
     * Plot constellation lines and IAU abbreviation labels into the 3D scene.
     *
     * Converts each star endpoint from equatorial (RA/Dec) to horizontal
     * (Alt/Az) coordinates for the given observer and time, then maps to
     * Three.js world space at CONSTELLATION_RADIUS.
     *
     * Line segments where BOTH endpoints are below the horizon (alt ≤ 0) are
     * skipped.  Partially-visible segments are included in full — the ground
     * plane naturally occludes the below-horizon portion.
     *
     * All valid segments across every constellation are batched into a single
     * THREE.LineSegments draw call.  A CSS2D label bearing the IAU abbreviation
     * is placed at the average world position of that constellation's
     * above-horizon star endpoints.
     *
     * @param {Object[]} constellationData - Array from constellations.json.
     *   Each element has: iau {string}, lines {number[][]} where each inner
     *   array is [ra1_deg, dec1_deg, ra2_deg, dec2_deg].
     * @param {number}      lat           - Observer latitude in degrees.
     * @param {number}      lon           - Observer longitude in degrees.
     * @param {Date|number} utcTimestamp  - UTC instant as a Date or Unix ms.
     * @param {number}      [opacity=0.25] - Line opacity (0-1), default 0.25.
     */
    plotConstellations(constellationData, lat, lon, utcTimestamp, opacity = 0.25) {
        if (this._scene === null) {
            // Store raw slider value — remapping happens at render time, not here.
            this._pendingConstellations = [constellationData, lat, lon, utcTimestamp, opacity];
            return;
        }
        if (!Array.isArray(constellationData)) return;

        // Clamp input then remap to compensate for WebGL line dimness relative
        // to antialiased SVG strokes at the same nominal opacity.
        // ^0.5 (square root) for lines: aggressive boost because WebGL 1px lines
        //   lack subpixel antialiasing.
        // ^0.7 for labels: gentler boost because CSS opacity on HTML overlays
        //   behaves more like SVG.
        // Both mappings preserve the endpoints 0→0 and 1→1.
        const safeOpacity = Math.max(0, Math.min(1, opacity || 0));
        const effectiveLineOpacity  = Math.pow(safeOpacity, 0.5);
        const effectiveLabelOpacity = Math.pow(safeOpacity, 0.7);

        this._clearConstellations();

        // Collect all valid segment positions into one flat array for a
        // single LineSegments draw call.
        const segmentPositions = [];

        const lineMat = new THREE.LineBasicMaterial({
            color:       CONSTELLATION_LINE_COLOR,
            transparent: effectiveLineOpacity < 1,
            opacity:     effectiveLineOpacity,
            depthWrite:  false,
        });

        for (const constellation of constellationData) {
            if (!Array.isArray(constellation.lines)) continue;

            // Accumulate above-horizon endpoint positions for this constellation's
            // label anchor, averaged over all visible star endpoints.
            const labelPoints = [];

            for (const seg of constellation.lines) {
                const [ra1, dec1, ra2, dec2] = seg;

                const { altitude_deg: alt1, azimuth_deg: az1 } =
                    raDecToAltAz(ra1, dec1, lat, lon, utcTimestamp);
                const { altitude_deg: alt2, azimuth_deg: az2 } =
                    raDecToAltAz(ra2, dec2, lat, lon, utcTimestamp);

                // Skip segments where both endpoints are below the horizon.
                if (alt1 <= 0 && alt2 <= 0) continue;

                const p1 = altAzToCartesian(alt1, az1, CONSTELLATION_RADIUS);
                const p2 = altAzToCartesian(alt2, az2, CONSTELLATION_RADIUS);

                segmentPositions.push(p1.x, p1.y, p1.z, p2.x, p2.y, p2.z);

                // Track above-horizon endpoints for the label anchor.
                if (alt1 > 0) labelPoints.push(p1);
                if (alt2 > 0) labelPoints.push(p2);
            }

            // Place a label if at least one endpoint of this constellation is
            // above the horizon.
            if (labelPoints.length === 0) continue;

            let sumX = 0, sumY = 0, sumZ = 0;
            for (const p of labelPoints) {
                sumX += p.x;
                sumY += p.y;
                sumZ += p.z;
            }
            const n = labelPoints.length;
            let cx = sumX / n;
            let cy = sumY / n;
            let cz = sumZ / n;
            const len = Math.sqrt(cx * cx + cy * cy + cz * cz);
            if (len > 0) {
                cx = (cx / len) * CONSTELLATION_RADIUS;
                cy = (cy / len) * CONSTELLATION_RADIUS;
                cz = (cz / len) * CONSTELLATION_RADIUS;
            }

            const labelEl = document.createElement('div');
            labelEl.className = 'sky-map-3d-constellation-label';
            labelEl.textContent = constellation.iau;
            labelEl.style.opacity = effectiveLabelOpacity;

            const labelObj = new CSS2DObject(labelEl);
            labelObj.position.set(cx, cy, cz);
            this._constellationsGroup.add(labelObj);
        }

        // Build the single LineSegments object only if there is at least one
        // valid segment to render.
        if (segmentPositions.length > 0) {
            const positions = new Float32Array(segmentPositions);
            const geo = new THREE.BufferGeometry();
            geo.setAttribute('position', new THREE.BufferAttribute(positions, 3));
            const lines = new THREE.LineSegments(geo, lineMat);
            this._constellationsGroup.add(lines);
        } else {
            // No visible segments — dispose the material to avoid a GPU leak.
            lineMat.dispose();
        }
    }

    /**
     * Plot background stars as small glow sprites in the 3D scene.
     *
     * Stars are rendered at STAR_RADIUS (slightly inside the constellation
     * sphere) so they appear behind constellation lines.  Each star receives a
     * CSS2D label object (with class `sky-map-3d-star-label info-icon`) that
     * carries a data-tooltip-title attribute, making it raycaster-interactive
     * via the same TooltipManager path used by planet labels.
     *
     * Safe to call before activate() — arguments are stored and replayed once
     * the scene is ready.  Safe to call multiple times — previous sprites and
     * their CSS2D labels are disposed before rebuilding.
     *
     * Stars above limitingMagnitude are skipped, as are any whose computed
     * altitude is at or below the horizon.
     *
     * @param {Object[]} stars          - Array of star objects.
     *   Each must have: ra_deg {number}, dec_deg {number}, magnitude {number},
     *   name {string}.
     * @param {number}   limitingMagnitude - Faintest magnitude to render (inclusive).
     * @param {number}   lat            - Observer latitude in degrees.
     * @param {number}   lon            - Observer longitude in degrees.
     * @param {Date|number} utcTimestamp - UTC instant as a Date or Unix ms.
     */
    plotStars(stars, limitingMagnitude, lat, lon, utcTimestamp) {
        // Defer if the scene has not been initialised yet.
        if (this._scene === null) {
            this._pendingStars = [stars, limitingMagnitude, lat, lon, utcTimestamp];
            return;
        }

        if (!Array.isArray(stars)) return;

        this._clearStars();

        for (const star of stars) {
            if (star.magnitude > limitingMagnitude) continue;

            const { altitude_deg, azimuth_deg } = raDecToAltAz(
                star.ra_deg, star.dec_deg, lat, lon, utcTimestamp,
            );

            if (isNaN(altitude_deg) || isNaN(azimuth_deg) || altitude_deg <= 0) continue;

            const { x, y, z } = altAzToCartesian(altitude_deg, azimuth_deg, STAR_RADIUS);

            const texture  = buildBodyTexture('#d0e8ff');
            const material = new THREE.SpriteMaterial({
                map:         texture,
                transparent: true,
                depthWrite:  false,
            });
            const sprite = new THREE.Sprite(material);

            const scale = SPHERE_RADIUS * Math.max(0.012, Math.min(0.02, 0.015 - star.magnitude * 0.003));
            sprite.scale.set(scale, scale, 1);
            sprite.position.set(x, y, z);

            // Build CSS2D label for tooltip interactivity.
            const compassDirection = azimuthToCompass(azimuth_deg);
            const tooltipText =
                `${star.name}\n` +
                `Höjd: ${altitude_deg.toFixed(1)}°\n` +
                `Riktning: ${compassDirection}\n` +
                `Magnitud: ${star.magnitude.toFixed(2)}`;

            const labelEl = document.createElement('div');
            labelEl.className = 'sky-map-3d-label sky-map-3d-star-label info-icon';
            labelEl.textContent = star.name;
            labelEl.dataset.tooltipTitle = tooltipText;
            labelEl.style.pointerEvents = 'none';

            const labelObject = new CSS2DObject(labelEl);
            labelObject.position.set(x, y, z);

            // Keep a reference on the sprite for cleanup and raycaster hit handling.
            sprite.userData.labelObject = labelObject;

            this._labelsGroup.add(labelObject);
            this._starsGroup.add(sprite);
        }
    }

    // -----------------------------------------------------------------------
    // Private — scene initialisation
    // -----------------------------------------------------------------------

    /**
     * Build the renderer, scene, camera, controls, and all static geometry.
     * Called exactly once on the first activate() call.
     */
    _initScene() {
        // --- Renderer ---
        // Use a local variable so this._renderer remains null until the entire
        // initialisation succeeds. The null check in activate() thereby
        // correctly reflects whether a full init has completed.
        const renderer = new THREE.WebGLRenderer({ antialias: true });

        // Validate the WebGL context before calling any other renderer methods.
        if (renderer.getContext() === null) {
            throw new Error('WebGL-kontext kunde inte skapas');
        }

        renderer.setClearColor(0x0a0a1a, 1);

        // --- CSS2DRenderer (overlays HTML labels on the WebGL canvas) ---
        const cssRenderer = new CSS2DRenderer();
        cssRenderer.domElement.style.position     = 'absolute';
        cssRenderer.domElement.style.top          = '0';
        cssRenderer.domElement.style.left         = '0';
        cssRenderer.domElement.style.pointerEvents = 'none';
        cssRenderer.domElement.style.width        = '100%';
        cssRenderer.domElement.style.height       = '100%';

        // --- Scene ---
        const scene = new THREE.Scene();

        // --- Camera ---
        // Aspect ratio is corrected in _handleResize(); use 1 as a placeholder.
        const camera = new THREE.PerspectiveCamera(60, 1, 0.1, SPHERE_RADIUS * 2.5);
        // The +Z offset causes OrbitControls to orient the camera toward -Z,
        // which is North in this coordinate system — a correct horizon-facing
        // initial view. (Exact origin would produce a degenerate up vector.)
        camera.position.set(0, 0, 0.001);

        // --- OrbitControls ---
        const controls = new OrbitControls(camera, renderer.domElement);
        controls.enableZoom = false;
        controls.enablePan  = false;
        controls.target.set(0, 0, 0);
        // Negative rotateSpeed gives the sky-dome feel: dragging right rotates
        // the camera left, as if the observer is turning their head.
        // Negative rotateSpeed inverts drag direction for the sky-dome feel:
        // dragging UP increases phi internally → phi=π means camera looks toward zenith.
        controls.rotateSpeed = -0.5;
        // With inverted controls phi increases upward, so:
        //   maxPolarAngle near π  → allows full zenith viewing
        //   minPolarAngle ~81°    → prevents looking more than ~9° below the horizon
        controls.maxPolarAngle = Math.PI * 0.99;
        controls.minPolarAngle = Math.PI * 0.45;
        controls.update();

        // --- Celestial sphere (inside-out, camera inside) ---
        const sphereGeo = new THREE.SphereGeometry(SPHERE_RADIUS, 32, 32);
        const sphereMat = new THREE.MeshBasicMaterial({
            color: 0x0a0a1a,
            side: THREE.BackSide,
        });
        scene.add(new THREE.Mesh(sphereGeo, sphereMat));

        // --- Horizon ground plane ---
        // A flat disc at y=0 that visually separates sky from "ground".
        const groundGeo = new THREE.CircleGeometry(SPHERE_RADIUS, 64);
        const groundMat = new THREE.MeshBasicMaterial({
            color: 0x111122,
            side: THREE.DoubleSide,
            transparent: true,
            opacity: 0.8,
        });
        const ground = new THREE.Mesh(groundGeo, groundMat);
        // CircleGeometry lies in the XY plane; rotate so it lies in the XZ plane (y=0).
        ground.rotation.x = -Math.PI / 2;
        scene.add(ground);

        // --- Alt-azimuth grid ---
        scene.add(buildGrid());

        // --- Cardinal direction labels ---
        scene.add(buildCardinalLabels());

        // --- Constellation group (line segments and IAU abbreviation labels) ---
        // Added first so constellation lines render behind stars, planets, and labels.
        const constellationsGroup = new THREE.Group();
        scene.add(constellationsGroup);

        // --- Star group (background star sprites, rendered behind planets) ---
        const starsGroup = new THREE.Group();
        scene.add(starsGroup);

        // --- Body groups (sprites and CSS2D labels) ---
        // bodiesGroup is added before labelsGroup so labels render on top.
        const bodiesGroup = new THREE.Group();
        const labelsGroup = new THREE.Group();
        scene.add(bodiesGroup);
        scene.add(labelsGroup);

        // --- Raycaster for cursor feedback ---
        const raycaster = new THREE.Raycaster();
        const pointer   = new THREE.Vector2();

        // Commit scene/camera/controls to the instance before touching the DOM.
        // If any of these assignments were to throw, no canvas will have been
        // orphaned in the DOM and this._renderer remains null (the sentinel).
        this._scene               = scene;
        this._camera              = camera;
        this._controls            = controls;
        this._starsGroup          = starsGroup;
        this._bodiesGroup         = bodiesGroup;
        this._labelsGroup         = labelsGroup;
        this._constellationsGroup = constellationsGroup;
        this._raycaster           = raycaster;
        this._pointer             = pointer;

        // Attach the WebGL canvas to the DOM.
        renderer.domElement.setAttribute('aria-hidden', 'true');
        this.container.appendChild(renderer.domElement);

        // The container must be positioned so the CSS2DRenderer overlay is
        // correctly layered over the WebGL canvas.
        if (getComputedStyle(this.container).position === 'static') {
            this.container.style.position = 'relative';
        }

        // Attach the CSS2DRenderer overlay after the canvas.
        this.container.appendChild(cssRenderer.domElement);

        // Register pointermove for cursor feedback on body sprites.
        renderer.domElement.addEventListener('pointermove', (event) => {
            this._handlePointerMove(event);
        });

        // Register pointerdown to trigger tooltips on tap (mobile) and click.
        renderer.domElement.addEventListener('pointerdown', (event) => {
            if (this._renderer === null || this._bodiesGroup === null) return;

            const rect = this._renderer.domElement.getBoundingClientRect();
            const ndcX =  ((event.clientX - rect.left) / rect.width)  * 2 - 1;
            const ndcY = -((event.clientY - rect.top)  / rect.height) * 2 + 1;

            const pointer = new THREE.Vector2(ndcX, ndcY);
            this._raycaster.setFromCamera(pointer, this._camera);

            // Bodies are listed first so they take priority over stars when overlapping.
            const starsChildren = this._starsGroup !== null ? this._starsGroup.children : [];
            const hits = this._raycaster.intersectObjects([...this._bodiesGroup.children, ...starsChildren]);
            if (hits.length > 0) {
                const hit = hits[0].object;
                // Resolve label element: planets use userData.labelEl; stars use userData.labelObject.element.
                const labelEl = hit.userData.labelEl ?? (hit.userData.labelObject ? hit.userData.labelObject.element : null);
                if (labelEl) {
                    labelEl.dispatchEvent(new MouseEvent('mouseover', { bubbles: true, cancelable: true }));
                }
            }
        });

        // Register wheel event for FOV-based zoom. { passive: false } is
        // required so that event.preventDefault() can suppress page scroll.
        // The guard prevents duplicate listeners if _initScene were ever called
        // more than once.
        if (!this._wheelListenerAttached) {
            renderer.domElement.addEventListener('wheel', (event) => {
                event.preventDefault();
                if (event.deltaY < 0) {
                    this.zoomIn();
                } else if (event.deltaY > 0) {
                    this.zoomOut();
                }
            }, { passive: false });
            this._wheelListenerAttached = true;
        }

        // Register touch pinch-zoom listeners once. OrbitControls uses
        // pointermove for single-finger rotation; touch events are distinct,
        // so two-finger pinch detection here does not interfere with drag.
        // { passive: false } is required so preventDefault() can suppress
        // native browser pinch-to-zoom on the canvas element.
        if (!this._touchListenerAttached) {
            renderer.domElement.addEventListener('touchstart', (event) => {
                if (event.touches.length === 2) {
                    this._pinchStartDistance = this._getTouchDistance(event.touches);
                    event.preventDefault();
                }
            }, { passive: false });

            renderer.domElement.addEventListener('touchmove', (event) => {
                if (event.touches.length === 2 && this._pinchStartDistance !== null) {
                    const currentDistance = this._getTouchDistance(event.touches);
                    const delta = currentDistance - this._pinchStartDistance;
                    // Only trigger zoom when finger movement exceeds 5 px to
                    // reduce jitter from small fluctuations in touch coordinates.
                    if (delta > 5) {
                        this.zoomIn();
                        this._pinchStartDistance = currentDistance;
                    } else if (delta < -5) {
                        this.zoomOut();
                        this._pinchStartDistance = currentDistance;
                    }
                    event.preventDefault();
                }
            }, { passive: false });

            const resetPinch = () => { this._pinchStartDistance = null; };
            renderer.domElement.addEventListener('touchend',    resetPinch);
            renderer.domElement.addEventListener('touchcancel', resetPinch);

            this._touchListenerAttached = true;
        }

        // this._renderer and this._cssRenderer are assigned last so that the
        // null check in activate() is a reliable sentinel for complete
        // initialisation — any earlier throw leaves them null.
        this._setPixelRatio(renderer);
        this._renderer    = renderer;
        this._cssRenderer = cssRenderer;
    }

    // -----------------------------------------------------------------------
    // Private — render loop
    // -----------------------------------------------------------------------

    /** Start (or restart) the WebGL animation loop. */
    _startLoop() {
        if (this._renderer === null) return;
        this._renderer.setAnimationLoop(() => {
            if (this._controls !== null) {
                this._controls.update();
            }
            this._renderer.render(this._scene, this._camera);
            this._cssRenderer.render(this._scene, this._camera);
        });
    }

    /** Stop the WebGL animation loop without disposing resources. */
    _stopLoop() {
        if (this._renderer !== null) {
            this._renderer.setAnimationLoop(null);
        }
    }

    // -----------------------------------------------------------------------
    // Private — resize handling
    // -----------------------------------------------------------------------

    /**
     * Recalculate the renderer size and camera aspect ratio to match the
     * current container dimensions.
     */
    _handleResize() {
        if (this._renderer === null) return;

        const width  = this.container.clientWidth;
        const height = this.container.clientHeight;

        if (width === 0 || height === 0) return;

        this._camera.aspect = width / height;
        this._camera.updateProjectionMatrix();
        this._renderer.setSize(width, height);
        this._cssRenderer.setSize(width, height);
    }

    // -----------------------------------------------------------------------
    // Private — pixel ratio
    // -----------------------------------------------------------------------

    /**
     * Apply the device pixel ratio (capped at 2 to avoid excessive GPU load
     * on very high-DPI displays).
     *
     * @param {THREE.WebGLRenderer} [renderer] - Renderer to configure.
     *   Defaults to this._renderer. Pass the local renderer instance when
     *   calling from _initScene() before this._renderer has been assigned.
     */
    _setPixelRatio(renderer = this._renderer) {
        if (renderer === null) return;
        renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    }

    // -----------------------------------------------------------------------
    // Private — body sprite management
    // -----------------------------------------------------------------------

    /**
     * Remove and dispose all body sprites and CSS2D label objects from the
     * _bodiesGroup and _labelsGroup.
     *
     * SpriteMaterial and CanvasTexture are explicitly disposed to prevent
     * GPU memory leaks on each plotBodies() call.
     */
    _clearBodies() {
        // Dismiss any active tooltip to prevent stale activeIcon references
        if (this._hoveredLabel !== null) {
            this._hoveredLabel.dispatchEvent(new MouseEvent('mouseout', { bubbles: true, cancelable: true }));
            this._hoveredLabel = null;
        }

        // Dispose sprite materials and textures.
        for (const child of this._bodiesGroup.children) {
            if (child.material) {
                if (child.material.map) {
                    child.material.map.dispose();
                }
                child.material.dispose();
            }
        }
        this._bodiesGroup.clear();

        // CSS2DObjects do not hold GPU resources, but their DOM elements are
        // removed from the overlay when the object leaves the scene graph.
        // Only remove body labels — star labels are owned by _starsGroup and
        // must not be disturbed here.
        for (const labelObj of this._bodyLabelsArray) {
            this._labelsGroup.remove(labelObj);
        }
        this._bodyLabelsArray = [];
    }

    /**
     * Remove and dispose all constellation geometry, materials, and CSS2D
     * label objects from _constellationsGroup.
     *
     * The LineSegments geometry and material are explicitly disposed to prevent
     * GPU memory leaks on each plotConstellations() call.
     */
    _clearConstellations() {
        for (const child of this._constellationsGroup.children) {
            if (child.geometry) {
                child.geometry.dispose();
            }
            if (child.material) {
                child.material.dispose();
            }
        }
        this._constellationsGroup.clear();
    }

    /**
     * Remove and dispose all star sprites from _starsGroup.
     *
     * SpriteMaterial and CanvasTexture are explicitly disposed to prevent
     * GPU memory leaks on each plotStars() call.
     */
    _clearStars() {
        for (const child of this._starsGroup.children) {
            // Remove the CSS2DObject from _labelsGroup before clearing sprites.
            if (child.userData.labelObject && this._labelsGroup !== null) {
                this._labelsGroup.remove(child.userData.labelObject);
            }
            if (child.material) {
                if (child.material.map) {
                    child.material.map.dispose();
                }
                child.material.dispose();
            }
        }
        this._starsGroup.clear();
    }

    /**
     * Create one body sprite and its CSS2D label, then add both to their
     * respective groups.
     *
     * @param {number} altitudeDeg - Body altitude in degrees.
     * @param {number} azimuthDeg  - Body azimuth in degrees.
     * @param {string} color       - CSS colour string for the glow texture.
     * @param {number} magnitude   - Apparent magnitude (drives sprite scale).
     * @param {string} nameSv      - Swedish name shown as label text.
     * @param {string} tooltipText - Plain-text tooltip content.
     * @param {Object} userData    - Metadata stored in sprite.userData.
     * @param {number} [scaleFactor=1] - Multiplier applied on top of the
     *   magnitude-based scale formula (used for Sun/Moon).
     */
    _addBodySprite(altitudeDeg, azimuthDeg, color, magnitude, nameSv, tooltipText, userData, scaleFactor = 1) {
        const { x, y, z } = altAzToCartesian(altitudeDeg, azimuthDeg, GRID_RADIUS);
        const position = new THREE.Vector3(x, y, z);

        // --- Sprite ---
        const texture  = buildBodyTexture(color);
        const material = new THREE.SpriteMaterial({ map: texture, transparent: true, depthWrite: false });
        const sprite   = new THREE.Sprite(material);

        const scale = bodyScale(magnitude) * scaleFactor;
        sprite.scale.set(scale, scale, 1);
        sprite.position.copy(position);
        sprite.userData = { ...userData };

        this._bodiesGroup.add(sprite);

        // --- CSS2D label ---
        const element = document.createElement('div');
        element.className = 'sky-map-3d-label info-icon';
        element.dataset.tooltipTitle = tooltipText;
        element.textContent = nameSv;
        element.style.pointerEvents = 'none';
        element.setAttribute('tabindex', '0');
        element.setAttribute('role', 'button');
        element.setAttribute('aria-label', nameSv);

        // Store label element reference on the sprite so the pointerdown
        // handler can trigger the tooltip without relying on pointer-events.
        sprite.userData.labelEl = element;

        const labelObject = new CSS2DObject(element);
        // Offset upward slightly so the label clears the sprite.
        labelObject.position.set(x, y + SPHERE_RADIUS * 0.04, z);

        this._labelsGroup.add(labelObject);
        this._bodyLabelsArray.push(labelObject);
    }

    // -----------------------------------------------------------------------
    // Private — touch helpers
    // -----------------------------------------------------------------------

    /**
     * Compute the pixel distance between two touch points.
     *
     * @param {TouchList} touches - The TouchList from a TouchEvent. Must have
     *   at least two entries.
     * @returns {number} Euclidean distance in CSS pixels.
     */
    _getTouchDistance(touches) {
        if (touches.length < 2) return 0;
        return Math.hypot(
            touches[0].clientX - touches[1].clientX,
            touches[0].clientY - touches[1].clientY,
        );
    }

    // -----------------------------------------------------------------------
    // Private — pointer move (cursor feedback)
    // -----------------------------------------------------------------------

    /**
     * Update the canvas cursor style based on whether the pointer is over
     * any body sprite.
     *
     * @param {PointerEvent} event
     */
    _handlePointerMove(event) {
        if (this._renderer === null || this._bodiesGroup === null) return;

        const rect = this._renderer.domElement.getBoundingClientRect();
        this._pointer.x =  ((event.clientX - rect.left)  / rect.width)  * 2 - 1;
        this._pointer.y = -((event.clientY - rect.top)   / rect.height) * 2 + 1;

        this._raycaster.setFromCamera(this._pointer, this._camera);

        // Bodies are listed first so they take priority over stars when overlapping.
        const starsChildren = this._starsGroup !== null ? this._starsGroup.children : [];
        const hits = this._raycaster.intersectObjects([...this._bodiesGroup.children, ...starsChildren]);

        if (hits.length > 0) {
            const hit = hits[0].object;
            // Resolve label element: planets use userData.labelEl; stars use userData.labelObject.element.
            const labelEl = hit.userData.labelEl ?? (hit.userData.labelObject ? hit.userData.labelObject.element : null);
            if (labelEl && labelEl !== this._hoveredLabel) {
                labelEl.dispatchEvent(new MouseEvent('mouseover', { bubbles: true, cancelable: true }));
            }
            this._hoveredLabel = labelEl;
            this._renderer.domElement.style.cursor = 'pointer';
        } else if (this._hoveredLabel !== null) {
            this._hoveredLabel.dispatchEvent(new MouseEvent('mouseout', { bubbles: true, cancelable: true }));
            this._hoveredLabel = null;
            this._renderer.domElement.style.cursor = '';
        }
    }
}
