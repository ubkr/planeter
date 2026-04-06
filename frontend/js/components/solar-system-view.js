/**
 * solar-system-view.js — SVG top-down solar system renderer.
 *
 * Draws a simplified heliocentric view of the inner solar system with:
 *   - The Sun at the centre
 *   - Orbit rings using square-root scaling so outer planets remain visible
 *   - Planet dots projected onto their orbit rings using the same sqrt scaling
 *   - Earth reference orbit ring (dashed) labelled "1 AU"
 *   - Earth dot showing the actual Earth position from the API
 *
 * Clicking a planet dot zooms the SVG viewBox to that planet and shows
 * an encyclopedic detail overlay sourced from planet-info.js.
 *
 * Orbit ring radii use sqrt scaling for visual readability:
 *   radius_px = MAX_RADIUS * sqrt(sma / MAX_SMA)
 *
 * Planet dot positions also use sqrt scaling (preserving angle, compressing
 * radial distance) so dots land on their correct orbit rings:
 *   scaledDist = MAX_RADIUS * sqrt(actualAU / MAX_SMA)
 *   svgX = 250 + scaledDist * cos(angle)
 *   svgY = 250 - scaledDist * sin(angle)   (Y flipped for SVG coordinate system)
 */

import PLANET_INFO from '../data/planet-info.js';

const SVG_NS = 'http://www.w3.org/2000/svg';

// Coordinate constants
const VIEW_SIZE = 500;
const CENTER = 250;
const MAX_RADIUS = 230;

// Saturn's semi-major axis — used as the scaling reference
const MAX_SMA = 9.537;

// Semi-major axes in AU for all tracked planets plus Earth reference
const SEMI_MAJOR_AXES = {
    mercury: 0.387,
    venus:   0.723,
    earth:   1.0,
    mars:    1.524,
    jupiter: 5.203,
    saturn:  9.537,
};

// Zoom animation duration in milliseconds
const ZOOM_DURATION_MS = 400;

// Half-size of the zoomed viewBox window (planet is centred in a 120×120 region)
const ZOOM_HALF = 60;

// Fallback English→Swedish name map for the detail overlay
const SWEDISH_NAMES = {
    mercury: 'Merkurius',
    venus:   'Venus',
    earth:   'Jorden',
    mars:    'Mars',
    jupiter: 'Jupiter',
    saturn:  'Saturnus',
};

// Planet colour tokens — earth has no dedicated token, falls back to CSS var
const PLANET_COLOR_TOKEN = {
    mercury: 'var(--color-planet-mercury)',
    venus:   'var(--color-planet-venus)',
    earth:   'var(--color-accent-secondary)',
    mars:    'var(--color-planet-mars)',
    jupiter: 'var(--color-planet-jupiter)',
    saturn:  'var(--color-planet-saturn)',
};

// ---------------------------------------------------------------------------
// Internal SVG helpers
// ---------------------------------------------------------------------------

/**
 * Create an SVG element in the SVG namespace.
 *
 * @param {string} tag
 * @returns {SVGElement}
 */
function svgEl(tag) {
    return document.createElementNS(SVG_NS, tag);
}

/**
 * Set multiple attributes on an SVG element at once.
 *
 * @param {SVGElement} el
 * @param {Object.<string, string|number>} attrs
 */
function setAttrs(el, attrs) {
    for (const [key, value] of Object.entries(attrs)) {
        el.setAttribute(key, String(value));
    }
}

/**
 * Compute the SVG pixel radius for a given semi-major axis using sqrt scaling.
 *
 * @param {number} smaAU - Semi-major axis in AU
 * @returns {number}
 */
function orbitRadius(smaAU) {
    return MAX_RADIUS * Math.sqrt(smaAU / MAX_SMA);
}

/**
 * Clamp a number between min and max (inclusive).
 *
 * @param {number} v
 * @param {number} min
 * @param {number} max
 * @returns {number}
 */
function clamp(v, min, max) {
    return Math.max(min, Math.min(max, v));
}

/**
 * Linear interpolation between a and b by factor t.
 *
 * @param {number} a
 * @param {number} b
 * @param {number} t  - 0..1
 * @returns {number}
 */
function lerp(a, b, t) {
    return a + (b - a) * t;
}

// ---------------------------------------------------------------------------
// Build helpers — return SVGElement, no side effects
// ---------------------------------------------------------------------------

/**
 * Build the Sun circle at the centre of the diagram.
 *
 * @param {number|null|undefined} distanceAU - Earth-Sun distance in AU (optional)
 * @returns {SVGCircleElement}
 */
function buildSun(distanceAU) {
    const tooltipText = (distanceAU != null && !isNaN(distanceAU))
        ? `Solen\nAvstånd från Jorden: ${distanceAU.toFixed(4)} AU`
        : 'Solen';

    const circle = svgEl('circle');
    setAttrs(circle, {
        cx: CENTER,
        cy: CENTER,
        r: 10,
        class: 'solar-system__sun info-icon',
        tabindex: '0',
        role: 'button',
        title: tooltipText,
    });

    const svgTitle = svgEl('title');
    svgTitle.textContent = tooltipText;
    svgTitle.style.pointerEvents = 'none';
    circle.appendChild(svgTitle);

    return circle;
}

/**
 * Build the orbit ring for a named body.
 *
 * The Earth orbit ring is styled differently (dashed reference line).
 *
 * @param {string} name  - Lowercase planet name key (e.g. 'mercury', 'earth')
 * @param {number} smaAU - Semi-major axis in AU
 * @returns {SVGCircleElement}
 */
function buildOrbitRing(name, smaAU) {
    const r = orbitRadius(smaAU);
    const circle = svgEl('circle');

    const cssClass = name === 'earth'
        ? 'solar-system__orbit solar-system__orbit--earth'
        : 'solar-system__orbit';

    setAttrs(circle, {
        cx: CENTER,
        cy: CENTER,
        r: r,
        class: cssClass,
    });

    return circle;
}

/**
 * Build the "1 AU" label placed to the right of the Earth orbit ring.
 *
 * @returns {SVGTextElement}
 */
function buildEarthOrbitLabel() {
    const r = orbitRadius(SEMI_MAJOR_AXES.earth);
    const label = svgEl('text');
    setAttrs(label, {
        x: CENTER + r + 4,
        y: CENTER,
        class: 'solar-system__orbit-label',
        'dominant-baseline': 'central',
    });
    label.textContent = '1 AU';
    return label;
}

/**
 * Build the planet dot and its label for one planet.
 *
 * Returns null if the heliocentric coordinates are missing or invalid.
 * Also returns the computed SVG coordinates via the out-param object when
 * coordinates are valid, so the caller can store them for zoom.
 *
 * @param {Object} planet
 * @param {string} planet.name      - English name (e.g. "Mercury")
 * @param {string} planet.name_sv   - Swedish name (e.g. "Merkurius")
 * @param {number|null|undefined} planet.heliocentric_x_au
 * @param {number|null|undefined} planet.heliocentric_y_au
 * @param {{ x: number, y: number }|null} [coordsOut] - If provided, will be
 *   mutated to contain the computed svgX/svgY on success.
 * @returns {{ group: SVGGElement, dot: SVGCircleElement }|null}
 */
function buildPlanetDot(planet, coordsOut) {
    const x = planet.heliocentric_x_au;
    const y = planet.heliocentric_y_au;

    if (x == null || y == null || isNaN(x) || isNaN(y)) {
        return null;
    }

    const dist = Math.sqrt(x * x + y * y);
    if (dist === 0) {
        return null;
    }

    // Apply sqrt scaling to radial distance; preserve the actual angle.
    const scaledDist = MAX_RADIUS * Math.sqrt(dist / MAX_SMA);
    const angle = Math.atan2(y, x);

    const svgX = CENTER + scaledDist * Math.cos(angle);
    const svgY = CENTER - scaledDist * Math.sin(angle); // Y flipped

    if (coordsOut) {
        coordsOut.x = svgX;
        coordsOut.y = svgY;
    }

    const nameLower = planet.name.toLowerCase();

    // NOTE: info-icon class intentionally omitted here — the click-to-detail
    // overlay replaces tooltip functionality for planet dots in this view.
    // The Sun retains info-icon since it has no detail overlay.
    const group = svgEl('g');

    const dot = svgEl('circle');
    setAttrs(dot, {
        cx: svgX,
        cy: svgY,
        r: 7,
        class: `solar-system__planet solar-system__planet--${nameLower}`,
        tabindex: '0',
        role: 'button',
        'aria-label': planet.name_sv,
    });

    // SVG accessibility: child <title> element.
    const svgTitle = svgEl('title');
    svgTitle.textContent = `${planet.name_sv} — klicka för information`;
    svgTitle.style.pointerEvents = 'none';
    dot.appendChild(svgTitle);

    group.appendChild(dot);

    // Text label offset slightly to the right and above the dot
    const label = svgEl('text');
    setAttrs(label, {
        x: svgX + 10,
        y: svgY - 10,
        class: 'solar-system__label',
    });
    label.textContent = planet.name_sv;
    group.appendChild(label);

    return { group, dot };
}

/**
 * Build the Earth dot showing the actual Earth position from the API.
 *
 * Returns null if the heliocentric coordinates are missing or invalid.
 *
 * @param {Object|null|undefined} earthHeliocentric - earth_heliocentric API object
 * @param {number|null|undefined} earthHeliocentric.heliocentric_x_au
 * @param {number|null|undefined} earthHeliocentric.heliocentric_y_au
 * @param {number|null|undefined} earthHeliocentric.distance_au
 * @param {{ x: number, y: number }|null} [coordsOut] - If provided, will be
 *   mutated to contain the computed svgX/svgY on success.
 * @returns {{ group: SVGGElement, dot: SVGCircleElement }|null}
 */
function buildEarthDot(earthHeliocentric, coordsOut) {
    if (!earthHeliocentric) {
        return null;
    }

    const x = earthHeliocentric.heliocentric_x_au;
    const y = earthHeliocentric.heliocentric_y_au;

    if (x == null || y == null || isNaN(x) || isNaN(y)) {
        return null;
    }

    const dist = Math.sqrt(x * x + y * y);
    if (dist === 0) {
        return null;
    }

    // Apply sqrt scaling to radial distance; preserve the actual angle.
    const scaledDist = MAX_RADIUS * Math.sqrt(dist / MAX_SMA);
    const angle = Math.atan2(y, x);

    const svgX = CENTER + scaledDist * Math.cos(angle);
    const svgY = CENTER - scaledDist * Math.sin(angle); // Y flipped

    if (coordsOut) {
        coordsOut.x = svgX;
        coordsOut.y = svgY;
    }

    // Prefer distance_au from API if available, otherwise fall back to computed dist.
    const distanceAU = (earthHeliocentric.distance_au != null && !isNaN(earthHeliocentric.distance_au))
        ? earthHeliocentric.distance_au
        : dist;

    const group = svgEl('g');

    // Earth dot — smaller than planet dots (r=5 vs r=7) since Earth is a
    // reference body, not a tracked planet.
    // NOTE: info-icon class intentionally omitted — detail overlay handles interaction.
    const dot = svgEl('circle');
    setAttrs(dot, {
        cx: svgX,
        cy: svgY,
        r: 5,
        class: 'solar-system__planet solar-system__planet--earth',
        tabindex: '0',
        role: 'button',
        'aria-label': 'Jorden',
    });

    // SVG accessibility: child <title> element.
    const svgTitle = svgEl('title');
    svgTitle.textContent = `Jorden — klicka för information\nAvstånd från Solen: ${distanceAU.toFixed(4)} AU`;
    svgTitle.style.pointerEvents = 'none';
    dot.appendChild(svgTitle);

    group.appendChild(dot);

    // Text label offset slightly to the right and above the dot
    const label = svgEl('text');
    setAttrs(label, {
        x: svgX + 10,
        y: svgY - 10,
        class: 'solar-system__label',
    });
    label.textContent = 'Jorden';
    group.appendChild(label);

    return { group, dot };
}

// ---------------------------------------------------------------------------
// Exported class
// ---------------------------------------------------------------------------

export class SolarSystemView {
    /**
     * @param {Element} containerEl - The DOM element to render the SVG into
     *   (i.e. #solarSystemContainer). The detail overlay is appended to the
     *   nearest `.solar-system-panel` ancestor.
     */
    constructor(containerEl) {
        // Guard against missing container; methods check this.containerEl before use.
        this.containerEl = containerEl || null;
        this._svg = null;

        // Map of lowercase planet key → { x, y } SVG coordinates.
        // Populated during render(); used by click handlers.
        this._planetPositions = new Map();

        // Map of lowercase planet key → full planet API data object (including moons).
        // Populated during render() alongside _planetPositions.
        this._planetData = new Map();

        // Zoom / overlay state
        this._zoomedPlanet = null;   // lowercase planet key currently zoomed, or null
        this._overlayEl = null;      // the detail overlay DOM element, or null
        this._isAnimating = false;   // true while a viewBox tween is running
        this._rafId = null;          // pending requestAnimationFrame handle, or null
    }

    /**
     * Render the solar system diagram.
     *
     * Replaces any existing SVG in the container. Orbit rings are always drawn;
     * planet dots are drawn only when heliocentric coordinates are available.
     *
     * @param {Array<Object>} planets - Array of planet objects from the API.
     *   Each object should have: name, name_sv, heliocentric_x_au, heliocentric_y_au.
     * @param {Object|null} [earthHeliocentric=null] - earth_heliocentric API object.
     */
    render(planets, earthHeliocentric = null, earthSystem = null) {
        if (!this.containerEl) {
            return;
        }

        this._earthSystem = earthSystem;

        // Instantly reset any active zoom before re-rendering — no animation.
        this._resetZoomInstant();

        // Remove any previously rendered SVG
        this._removeSvg();

        // Clear position and data caches — will be repopulated below
        this._planetPositions.clear();
        this._planetData.clear();

        const svg = svgEl('svg');
        setAttrs(svg, {
            viewBox: `0 0 ${VIEW_SIZE} ${VIEW_SIZE}`,
            class: 'solar-system-svg',
            width: '100%',
            role: 'group',
            'aria-label': 'Solsystemet \u2014 vy uppifrån',
        });

        // --- Orbit rings (drawn first so dots appear on top) ---
        for (const [name, smaAU] of Object.entries(SEMI_MAJOR_AXES)) {
            svg.appendChild(buildOrbitRing(name, smaAU));
        }

        // Earth orbit label
        svg.appendChild(buildEarthOrbitLabel());

        // --- Sun ---
        svg.appendChild(buildSun(earthHeliocentric?.distance_au ?? null));

        // --- Planet dots ---
        const planetList = Array.isArray(planets) ? planets : [];
        for (const planet of planetList) {
            const coords = { x: 0, y: 0 };
            const result = buildPlanetDot(planet, coords);
            if (result !== null) {
                const nameLower = planet.name.toLowerCase();
                this._planetPositions.set(nameLower, { x: coords.x, y: coords.y });
                this._planetData.set(nameLower, planet);
                this._attachDotClickHandler(result.dot, nameLower);
                svg.appendChild(result.group);
            }
        }

        // --- Earth dot ---
        const earthCoords = { x: 0, y: 0 };
        const earthResult = buildEarthDot(earthHeliocentric, earthCoords);
        if (earthResult !== null) {
            this._planetPositions.set('earth', { x: earthCoords.x, y: earthCoords.y });
            this._attachDotClickHandler(earthResult.dot, 'earth');
            svg.appendChild(earthResult.group);
        }

        this.containerEl.appendChild(svg);
        this._svg = svg;
    }

    /**
     * Remove the SVG from the container and reset internal state.
     * Instantly resets any active zoom without animation.
     */
    clear() {
        this._resetZoomInstant();
        this._removeSvg();
    }

    /**
     * Returns true when a planet is currently zoomed in.
     *
     * @returns {boolean}
     */
    isZoomed() {
        return !!this._zoomedPlanet;
    }

    /**
     * Zoom out from the current planet, removing the detail overlay and
     * animating the viewBox back to the default `0 0 500 500`.
     *
     * Safe to call even when not currently zoomed.
     */
    zoomOut() {
        if (this._isAnimating) {
            cancelAnimationFrame(this._rafId);
            this._rafId = null;
            this._isAnimating = false;
        }

        if (!this._zoomedPlanet && !this._overlayEl) {
            return;
        }

        // Remove overlay immediately
        this._removeOverlay();

        if (!this._svg) {
            this._zoomedPlanet = null;
            this._isAnimating = false;
            return;
        }

        this._isAnimating = true;

        // Parse current viewBox as the animation start point
        const startVB = this._parseViewBox();
        const endVB = [0, 0, VIEW_SIZE, VIEW_SIZE];
        const startTime = performance.now();

        const animate = (now) => {
            if (!this._svg) return;

            const t = Math.min((now - startTime) / ZOOM_DURATION_MS, 1);
            const vx = lerp(startVB[0], endVB[0], t);
            const vy = lerp(startVB[1], endVB[1], t);
            const vw = lerp(startVB[2], endVB[2], t);
            const vh = lerp(startVB[3], endVB[3], t);
            this._svg.setAttribute('viewBox', `${vx} ${vy} ${vw} ${vh}`);

            if (t < 1) {
                this._rafId = requestAnimationFrame(animate);
            } else {
                this._svg.setAttribute('viewBox', `0 0 ${VIEW_SIZE} ${VIEW_SIZE}`);
                this._svg.classList.remove('solar-system-svg--zoomed');
                this._zoomedPlanet = null;
                this._isAnimating = false;
                this._rafId = null;
            }
        };

        this._rafId = requestAnimationFrame(animate);
    }

    // ---------------------------------------------------------------------------
    // Private methods
    // ---------------------------------------------------------------------------

    /**
     * Attach click and keyboard handlers to a planet dot element.
     *
     * @param {SVGCircleElement} dot
     * @param {string} planetKey - Lowercase planet key (e.g. 'mars')
     */
    _attachDotClickHandler(dot, planetKey) {
        const handleActivate = () => {
            if (this._isAnimating) {
                return;
            }

            if (this._zoomedPlanet === planetKey) {
                // Already zoomed to this planet — no-op
                return;
            }

            const pos = this._planetPositions.get(planetKey);
            if (!pos) {
                return;
            }

            if (this._zoomedPlanet !== null) {
                // Instantly reset to a different planet's zoom
                this._resetZoomInstant();
            }

            this._zoomToPlanet(planetKey, pos.x, pos.y);
        };

        dot.addEventListener('click', handleActivate);

        dot.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault();
                handleActivate();
            }
        });
    }

    /**
     * Animate the SVG viewBox to zoom in on a planet, then show the detail overlay.
     *
     * @param {string} planetKey - Lowercase planet key
     * @param {number} svgX      - Planet's SVG x coordinate
     * @param {number} svgY      - Planet's SVG y coordinate
     */
    _zoomToPlanet(planetKey, svgX, svgY) {
        if (!this._svg) {
            return;
        }

        this._isAnimating = true;
        this._svg.classList.add('solar-system-svg--zoomed');

        // Compute target viewBox, clamped so it stays within SVG bounds 0–500
        const targetX = clamp(svgX - ZOOM_HALF, 0, VIEW_SIZE - ZOOM_HALF * 2);
        const targetY = clamp(svgY - ZOOM_HALF, 0, VIEW_SIZE - ZOOM_HALF * 2);
        const targetW = ZOOM_HALF * 2;
        const targetH = ZOOM_HALF * 2;

        const startVB = this._parseViewBox();
        const endVB = [targetX, targetY, targetW, targetH];
        const startTime = performance.now();

        const animate = (now) => {
            if (!this._svg) return;

            const t = Math.min((now - startTime) / ZOOM_DURATION_MS, 1);
            const vx = lerp(startVB[0], endVB[0], t);
            const vy = lerp(startVB[1], endVB[1], t);
            const vw = lerp(startVB[2], endVB[2], t);
            const vh = lerp(startVB[3], endVB[3], t);
            this._svg.setAttribute('viewBox', `${vx} ${vy} ${vw} ${vh}`);

            if (t < 1) {
                this._rafId = requestAnimationFrame(animate);
            } else {
                this._svg.setAttribute('viewBox', `${targetX} ${targetY} ${targetW} ${targetH}`);
                this._zoomedPlanet = planetKey;
                this._isAnimating = false;
                this._rafId = null;
                this._showDetailOverlay(planetKey);
            }
        };

        this._rafId = requestAnimationFrame(animate);
    }

    /**
     * Show the encyclopedic detail panel for the given planet.
     *
     * Replaces the old dark-backdrop overlay with a transparent two-column
     * layout so the zoomed SVG remains fully visible in the right column.
     *
     * DOM structure appended to .solar-system-panel:
     *   .solar-system__detail-layout
     *     ├── .solar-system__detail-info    (left column: title, facts, description, back btn)
     *     └── .solar-system__detail-svgarea (right column: moon/ring diagram sits here)
     *
     * @param {string} planetKey - Lowercase planet key (e.g. 'jupiter')
     */
    _showDetailOverlay(planetKey) {
        // Get the PLANET_INFO entry (keys are capitalised)
        const infoKey = planetKey.charAt(0).toUpperCase() + planetKey.slice(1);
        const info = PLANET_INFO[infoKey];
        if (!info) {
            return;
        }

        const swedishName = SWEDISH_NAMES[planetKey] || infoKey;
        const colorToken = PLANET_COLOR_TOKEN[planetKey] || 'var(--color-text-primary)';

        // --- Outer layout wrapper (transparent — no backdrop) ---
        const layout = document.createElement('div');
        layout.className = 'solar-system__detail-layout';

        // --- Left column: info panel ---
        const infoPanel = document.createElement('div');
        infoPanel.className = 'solar-system__detail-info';

        // Set the planet colour token so title and moon diagram planet circle
        // can reference it via CSS var(--detail-planet-color).
        layout.style.setProperty('--detail-planet-color', colorToken);

        // Title
        const title = document.createElement('h2');
        title.className = 'solar-system__detail-title';
        title.textContent = swedishName;
        infoPanel.appendChild(title);

        // Facts grid
        const grid = document.createElement('div');
        grid.className = 'solar-system__detail-grid';

        const facts = [
            ['Diameter',             `${info.diameter_km.toLocaleString('sv-SE')} km`],
            ['Omloppstid',           info.orbital_period_sv],
            ['Avstånd från solen',   `${info.distance_au} AU`],
            ['Kända månar',          String(info.known_moons)],
        ];

        for (const [label, value] of facts) {
            const labelEl = document.createElement('span');
            labelEl.className = 'solar-system__detail-label';
            labelEl.textContent = label;

            const valueEl = document.createElement('span');
            valueEl.className = 'solar-system__detail-value';
            valueEl.textContent = value;

            grid.appendChild(labelEl);
            grid.appendChild(valueEl);
        }
        infoPanel.appendChild(grid);

        // Description
        const desc = document.createElement('p');
        desc.className = 'solar-system__detail-description';
        desc.textContent = info.description_sv;
        infoPanel.appendChild(desc);

        // Back button
        const backBtn = document.createElement('button');
        backBtn.className = 'solar-system__detail-back-btn';
        backBtn.textContent = 'Tillbaka';
        backBtn.addEventListener('click', () => this.zoomOut());
        infoPanel.appendChild(backBtn);

        // --- Right column: SVG area (transparent overlay over the zoomed SVG) ---
        const svgArea = document.createElement('div');
        svgArea.className = 'solar-system__detail-svgarea';

        // Moon diagram — only rendered for planets that have moon data (Jupiter, Saturn)
        const planetData = this._planetData?.get(planetKey);
        if (planetData?.moons && planetData.moons.length > 0) {
            const moons = planetData.moons;

            const diagram = document.createElement('div');
            diagram.className = 'solar-system__moon-diagram';

            const moonHeading = document.createElement('h4');
            moonHeading.className = 'solar-system__moon-heading';
            moonHeading.textContent = 'Månar';
            diagram.appendChild(moonHeading);

            // Diagram dimensions — must match the CSS class dimensions
            const diagramWidth = 344;
            const diagramHeight = 246;
            const centerX = diagramWidth / 2;   // 172
            const centerY = diagramHeight / 2;  // 123
            const dotRadius = 4;
            const padding = 15;
            const maxScale = 10; // px per planet radius for near moons

            // Central planet circle
            const planetCircle = document.createElement('div');
            planetCircle.className = 'solar-system__moon-planet-circle';
            diagram.appendChild(planetCircle);

            // Outer moon threshold: moons beyond this offset in planet radii are
            // considered "outer" and excluded from the scale calculation (Fix 1).
            const OUTER_MOON_THRESHOLD = 30;

            // Fix 1: Two-tier scaling — compute scale based on inner moons only
            // (offset <= 30 radii) so that Iapetus (~60 radii) does not compress
            // the Galilean/inner-Saturn moons to overlap the planet circle.
            const allOffsets = moons.map((m) => Math.max(Math.abs(m.x_offset), Math.abs(m.y_offset)));
            const innerOffsets = allOffsets.filter((o) => o <= OUTER_MOON_THRESHOLD);
            const innerMaxOffset = innerOffsets.length > 0
                ? Math.max(...innerOffsets)
                : Math.max(...allOffsets);

            // Guard: avoid division by zero if all offsets are 0
            const scale = innerMaxOffset > 0
                ? Math.min((Math.min(centerX, centerY) - padding) / innerMaxOffset, maxScale)
                : maxScale;

            for (const moon of moons) {
                const moonOffset = Math.max(Math.abs(moon.x_offset), Math.abs(moon.y_offset));
                const isOuterMoon = moonOffset > OUTER_MOON_THRESHOLD;

                // Pixel position from centre; negate y because screen Y is inverted
                const rawLeft = centerX + moon.x_offset * scale - dotRadius;
                const rawTop  = centerY - moon.y_offset * scale - dotRadius;

                // Clamp so the dot stays within the diagram bounds
                const clampedLeft = Math.max(0, Math.min(diagramWidth  - dotRadius * 2, rawLeft));
                const clampedTop  = Math.max(0, Math.min(diagramHeight - dotRadius * 2, rawTop));

                // Fix 1 + 2: outer moons whose raw position differs from clamped
                // get the --clamped modifier class to indicate they are farther than shown.
                const wasClamped = isOuterMoon && (rawLeft !== clampedLeft || rawTop !== clampedTop);

                // Distance in planet radii for the tooltip (Pythagoras)
                const distRadii = Math.sqrt(moon.x_offset * moon.x_offset + moon.y_offset * moon.y_offset);

                const dot = document.createElement('div');
                // Fix 2: add --clamped class for visually distinct appearance
                dot.className = wasClamped
                    ? 'solar-system__moon-dot solar-system__moon-dot--clamped info-icon'
                    : 'solar-system__moon-dot info-icon';
                dot.setAttribute('title', `${moon.name_sv} — avstånd: ${distRadii.toFixed(1)} planetradier`);
                dot.style.left = `${Math.round(clampedLeft)}px`;
                dot.style.top  = `${Math.round(clampedTop)}px`;
                diagram.appendChild(dot);

                // Fix 3: Flip label to the LEFT when dot is in the right half,
                // and flip label UP when dot is near the bottom of the diagram.
                const label = document.createElement('span');
                label.className = 'solar-system__moon-label';
                label.textContent = moon.name_sv;

                if (clampedLeft > diagramWidth / 2) {
                    // Right half: anchor label to the right of the dot position
                    // and shift it left by its own width using translateX.
                    label.style.left = `${Math.round(clampedLeft - 2)}px`;
                    label.style.transform = 'translateX(-100%)';
                } else {
                    label.style.left = `${Math.round(clampedLeft + dotRadius * 2 + 2)}px`;
                }

                if (clampedTop > diagramHeight * 0.75) {
                    // Near the bottom: place label above the dot
                    label.style.top = `${Math.round(clampedTop - 12)}px`;
                } else {
                    label.style.top = `${Math.round(clampedTop - 2)}px`;
                }

                diagram.appendChild(label);
            }

            svgArea.appendChild(diagram);

            // Hide the zoomed SVG — the moon diagram is the primary planet visualization
            this._svg.classList.add('solar-system-svg--detail-hidden');

            // Scale the moon diagram to fill the svgarea
            requestAnimationFrame(() => {
                const areaW = svgArea.clientWidth;
                const areaH = svgArea.clientHeight;
                const DIAGRAM_W = 344; // must match diagramWidth constant
                const DIAGRAM_H = 246; // must match diagramHeight constant
                const PADDING = 32;
                const diagramScale = Math.max(0.8, Math.min(
                    (areaW - PADDING) / DIAGRAM_W,
                    (areaH - PADDING) / DIAGRAM_H
                ));
                diagram.style.setProperty('--moon-diagram-scale', diagramScale);
            });
        }

        // Earth Moon diagram — rendered only for the Earth detail view
        if (planetKey === 'earth') {
            this._buildEarthMoonDiagram(svgArea);
        }

        // Saturn ring diagram — rendered only when ring tilt data is available
        if (planetKey === 'saturn' && planetData?.ring_tilt_deg != null) {
            const ringTiltDeg = planetData.ring_tilt_deg;

            // Planet circle radius in the moon diagram (matches CSS: width/height 18px → r=9)
            const planetCircleRadius = 9;

            // Ring semi-major axis extends ~2.3 planetary radii
            const ringRx = planetCircleRadius * 2.3;

            // Semi-minor axis determined by the tilt angle; minimum 1px so the
            // ring remains visible during near-edge-on epochs (e.g. 2025-2026).
            const ringRy = Math.max(1, ringRx * Math.abs(Math.sin(ringTiltDeg * Math.PI / 180)));

            // Diagram dimensions and planet centre — kept in sync with the moon
            // diagram constants so the ring is centred on the planet circle.
            const ringDiagramWidth  = 344;
            const ringDiagramHeight = 246;
            const ringCenterX = ringDiagramWidth  / 2;  // 172
            const ringCenterY = ringDiagramHeight / 2;  // 123

            // Determine the container: reuse an existing moon diagram if present
            // (inside svgArea), otherwise create a standalone container.
            let ringContainer = svgArea.querySelector('.solar-system__moon-diagram');
            if (!ringContainer) {
                ringContainer = document.createElement('div');
                ringContainer.className = 'solar-system__moon-diagram';
                svgArea.appendChild(ringContainer);
                requestAnimationFrame(() => {
                    const areaW = svgArea.clientWidth;
                    const areaH = svgArea.clientHeight;
                    const DIAGRAM_W = 344;
                    const DIAGRAM_H = 246;
                    const PADDING = 32;
                    const diagramScale = Math.max(0.8, Math.min(
                        (areaW - PADDING) / DIAGRAM_W,
                        (areaH - PADDING) / DIAGRAM_H
                    ));
                    ringContainer.style.setProperty('--moon-diagram-scale', diagramScale);
                });
            }

            // Build the SVG overlay — use document.createElementNS for correct
            // SVG namespace; must match SVG_NS used throughout this file.
            const ringSvg = document.createElementNS(SVG_NS, 'svg');
            ringSvg.setAttribute('xmlns', SVG_NS);
            ringSvg.setAttribute('width',  String(ringDiagramWidth));
            ringSvg.setAttribute('height', String(ringDiagramHeight));
            ringSvg.setAttribute('viewBox', `0 0 ${ringDiagramWidth} ${ringDiagramHeight}`);
            ringSvg.style.position        = 'absolute';
            ringSvg.style.top             = '0';
            ringSvg.style.left            = '0';
            ringSvg.style.pointerEvents   = 'none';

            const ringEllipse = document.createElementNS(SVG_NS, 'ellipse');
            ringEllipse.setAttribute('cx', String(ringCenterX));
            ringEllipse.setAttribute('cy', String(ringCenterY));
            ringEllipse.setAttribute('rx', String(ringRx));
            ringEllipse.setAttribute('ry', String(ringRy));
            ringEllipse.setAttribute('class', 'solar-system__ring');

            ringSvg.appendChild(ringEllipse);

            // Insert the SVG as the FIRST child of the container so it renders
            // behind the planet circle div and all moon dot elements.
            ringContainer.insertBefore(ringSvg, ringContainer.firstChild);

            // Hide the zoomed SVG — the ring/moon diagram is the primary visualization.
            // Guard against double-add: the moon diagram path above may have already set it.
            if (this._svg) {
                this._svg.classList.add('solar-system-svg--detail-hidden');
            }
        }

        // Assemble layout: info panel on the left, SVG area on the right
        layout.appendChild(infoPanel);
        layout.appendChild(svgArea);

        // Append to .solar-system-panel (the panel wrapper that has position:relative)
        const panelEl = this._getPanelEl();
        const parentEl = panelEl || this.containerEl?.parentNode;
        if (!parentEl) {
            console.warn('SolarSystemView: could not find panel container for detail layout');
            return;
        }
        parentEl.appendChild(layout);

        this._overlayEl = layout;

        // Move focus to the back button after the layout is in the DOM
        requestAnimationFrame(() => {
            backBtn.focus();
        });
    }

    /**
     * Build the Earth Moon diagram and append it to the given container element.
     *
     * Renders a single Moon dot positioned relative to Earth using
     * x_offset_earth_radii / y_offset_earth_radii from the earth_system API data.
     * Also shows the Moon's illumination percentage.
     *
     * Falls back to a text message if this._earthSystem is null.
     *
     * @param {HTMLElement} container - The svgArea div to append the diagram into
     */
    _buildEarthMoonDiagram(container) {
        if (!this._earthSystem) {
            const fallback = document.createElement('p');
            fallback.className = 'solar-system__detail-fallback';
            fallback.textContent = 'Månens position kunde inte laddas just nu';
            container.appendChild(fallback);
            return;
        }

        const moon = this._earthSystem.moon;
        if (!moon) {
            const fallback = document.createElement('p');
            fallback.className = 'solar-system__detail-fallback';
            fallback.textContent = 'Månens position kunde inte laddas just nu';
            container.appendChild(fallback);
            return;
        }

        // Diagram dimensions — match the CSS class dimensions used by Jupiter/Saturn diagrams
        const diagramWidth  = 344;
        const diagramHeight = 246;
        const centerX = diagramWidth  / 2;  // 172
        const centerY = diagramHeight / 2;  // 123
        const dotRadius = 4;
        const padding   = 15;

        const diagram = document.createElement('div');
        diagram.className = 'solar-system__moon-diagram';

        const moonHeading = document.createElement('h4');
        moonHeading.className = 'solar-system__moon-heading';
        moonHeading.textContent = 'Månen';
        diagram.appendChild(moonHeading);

        // Central Earth circle
        const planetCircle = document.createElement('div');
        planetCircle.className = 'solar-system__moon-planet-circle';
        diagram.appendChild(planetCircle);

        // Guard: if offset values are NaN or null the diagram cannot be drawn
        if (!isFinite(moon.x_offset_earth_radii) || !isFinite(moon.y_offset_earth_radii)) {
            const fallback = document.createElement('p');
            fallback.className = 'solar-system__detail-fallback';
            fallback.textContent = 'Månens position kunde inte laddas just nu';
            container.appendChild(fallback);
            return;
        }

        // Scale: fit the Moon within the diagram with padding
        const maxOffset = Math.max(
            Math.abs(moon.x_offset_earth_radii),
            Math.abs(moon.y_offset_earth_radii)
        );

        const scale = maxOffset > 0
            ? (Math.min(centerX, centerY) - padding) / maxOffset
            : 1;

        // Pixel position from centre; negate y because screen Y axis is inverted
        const left = centerX + moon.x_offset_earth_radii * scale - dotRadius;
        const top  = centerY - moon.y_offset_earth_radii * scale - dotRadius;

        const dot = document.createElement('div');
        dot.className = 'solar-system__moon-dot';
        dot.style.left = `${Math.round(left)}px`;
        dot.style.top  = `${Math.round(top)}px`;
        diagram.appendChild(dot);

        const label = document.createElement('span');
        label.className = 'solar-system__moon-label';
        label.textContent = moon.name_sv ?? 'Månen';

        // Flip label to the left when dot is in the right half
        if (left > diagramWidth / 2) {
            label.style.left = `${Math.round(left - 2)}px`;
            label.style.transform = 'translateX(-100%)';
        } else {
            label.style.left = `${Math.round(left + dotRadius * 2 + 2)}px`;
        }
        label.style.top = `${Math.round(top - 2)}px`;
        diagram.appendChild(label);

        const illumination = document.createElement('span');
        illumination.className = 'solar-system__moon-illumination';
        illumination.textContent = `${Math.round(moon.illumination * 100)}% belyst`;
        // Position illumination label just below the name label (same left, 14px lower)
        illumination.style.left = label.style.left;
        if (label.style.transform) {
            illumination.style.transform = label.style.transform;
        }
        illumination.style.top = `${parseFloat(label.style.top) + 14}px`;
        diagram.appendChild(illumination);

        container.appendChild(diagram);

        // Hide the zoomed SVG — the Moon diagram is the primary visualization
        if (this._svg) {
            this._svg.classList.add('solar-system-svg--detail-hidden');
        }

        // Scale the diagram to fill the svgArea
        requestAnimationFrame(() => {
            const areaW = container.clientWidth;
            const areaH = container.clientHeight;
            const DIAGRAM_W = 344;
            const DIAGRAM_H = 246;
            const PADDING = 32;
            const diagramScale = Math.max(0.8, Math.min(
                (areaW - PADDING) / DIAGRAM_W,
                (areaH - PADDING) / DIAGRAM_H
            ));
            diagram.style.setProperty('--moon-diagram-scale', diagramScale);
        });
    }

    /**
     * Instantly reset zoom and remove overlay without animation.
     * Used at the start of render() and in clear().
     */
    _resetZoomInstant() {
        if (this._rafId) {
            cancelAnimationFrame(this._rafId);
            this._rafId = null;
        }

        this._removeOverlay();

        if (this._svg) {
            this._svg.setAttribute('viewBox', `0 0 ${VIEW_SIZE} ${VIEW_SIZE}`);
            this._svg.classList.remove('solar-system-svg--zoomed');
            this._svg.classList.remove('solar-system-svg--detail-hidden');
        }

        this._zoomedPlanet = null;
        this._isAnimating = false;
    }

    /**
     * Remove the detail overlay from the DOM and clear the reference.
     */
    _removeOverlay() {
        if (this._svg) {
            this._svg.classList.remove('solar-system-svg--detail-hidden');
        }
        if (this._overlayEl && this._overlayEl.parentNode) {
            this._overlayEl.parentNode.removeChild(this._overlayEl);
        }
        this._overlayEl = null;
    }

    /**
     * Parse the current SVG viewBox into an array [x, y, w, h].
     * Falls back to the default full view if parsing fails.
     *
     * @returns {[number, number, number, number]}
     */
    _parseViewBox() {
        if (!this._svg) {
            return [0, 0, VIEW_SIZE, VIEW_SIZE];
        }
        const vb = this._svg.getAttribute('viewBox') || '';
        const parts = vb.trim().split(/\s+/).map(Number);
        if (parts.length === 4 && parts.every((n) => !isNaN(n))) {
            return parts;
        }
        return [0, 0, VIEW_SIZE, VIEW_SIZE];
    }

    /**
     * Find the `.solar-system-panel` element that wraps this component.
     * Walks up from containerEl.
     *
     * @returns {Element|null}
     */
    _getPanelEl() {
        if (!this.containerEl) {
            return null;
        }
        let el = this.containerEl.parentNode;
        while (el && el !== document.body) {
            if (el.classList && el.classList.contains('solar-system-panel')) {
                return el;
            }
            el = el.parentNode;
        }
        return null;
    }

    /**
     * Remove the SVG from the container and reset the SVG reference.
     */
    _removeSvg() {
        if (this._svg && this._svg.parentNode) {
            this._svg.parentNode.removeChild(this._svg);
        }
        this._svg = null;
    }
}
