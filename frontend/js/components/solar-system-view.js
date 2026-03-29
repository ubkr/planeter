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
 * Orbit ring radii use sqrt scaling for visual readability:
 *   radius_px = MAX_RADIUS * sqrt(sma / MAX_SMA)
 *
 * Planet dot positions also use sqrt scaling (preserving angle, compressing
 * radial distance) so dots land on their correct orbit rings:
 *   scaledDist = MAX_RADIUS * sqrt(actualAU / MAX_SMA)
 *   svgX = 250 + scaledDist * cos(angle)
 *   svgY = 250 - scaledDist * sin(angle)   (Y flipped for SVG coordinate system)
 */

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
 *
 * @param {Object} planet
 * @param {string} planet.name      - English name (e.g. "Mercury")
 * @param {string} planet.name_sv   - Swedish name (e.g. "Merkurius")
 * @param {number|null|undefined} planet.heliocentric_x_au
 * @param {number|null|undefined} planet.heliocentric_y_au
 * @returns {SVGGElement|null}
 */
function buildPlanetDot(planet) {
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

    const nameLower = planet.name.toLowerCase();
    const tooltipText = `${planet.name_sv}\nAvstånd från Solen: ${dist.toFixed(2)} AU`;

    const group = svgEl('g');

    // Planet dot — also carries class="info-icon" so TooltipManager picks it up.
    // TooltipManager reads getAttribute('title') to get tooltip text, then removes
    // it and stores it in data-tooltip-title. We keep the title attribute for that
    // purpose AND add a child SVG <title> element for SVG accessibility standards.
    const dot = svgEl('circle');
    setAttrs(dot, {
        cx: svgX,
        cy: svgY,
        r: 7,
        class: `solar-system__planet solar-system__planet--${nameLower} info-icon`,
        tabindex: '0',
        role: 'button',
        title: tooltipText,
    });

    // SVG accessibility: child <title> element (the SVG-standard approach).
    // The title attribute above is kept in parallel for TooltipManager compatibility.
    const svgTitle = svgEl('title');
    svgTitle.textContent = tooltipText;
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

    return group;
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
 * @returns {SVGGElement|null}
 */
function buildEarthDot(earthHeliocentric) {
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

    // Prefer distance_au from API if available, otherwise fall back to computed dist.
    const distanceAU = (earthHeliocentric.distance_au != null && !isNaN(earthHeliocentric.distance_au))
        ? earthHeliocentric.distance_au
        : dist;

    const tooltipText = `Jorden\nAvstånd från Solen: ${distanceAU.toFixed(4)} AU`;

    const group = svgEl('g');

    // Earth dot — smaller than planet dots (r=5 vs r=7) since Earth is a
    // reference body, not a tracked planet. Uses info-icon for TooltipManager.
    const dot = svgEl('circle');
    setAttrs(dot, {
        cx: svgX,
        cy: svgY,
        r: 5,
        class: 'solar-system__planet solar-system__planet--earth info-icon',
        tabindex: '0',
        role: 'button',
        title: tooltipText,
    });

    // SVG accessibility: child <title> element.
    const svgTitle = svgEl('title');
    svgTitle.textContent = tooltipText;
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

    return group;
}

// ---------------------------------------------------------------------------
// Exported class
// ---------------------------------------------------------------------------

export class SolarSystemView {
    /**
     * @param {Element} containerEl - The DOM element to render the SVG into.
     */
    constructor(containerEl) {
        // Guard against missing container; methods check this.containerEl before use.
        this.containerEl = containerEl || null;
        this._svg = null;
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
    render(planets, earthHeliocentric = null) {
        if (!this.containerEl) {
            return;
        }

        // Remove any previously rendered SVG
        this._removeSvg();

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
            const dotGroup = buildPlanetDot(planet);
            if (dotGroup !== null) {
                svg.appendChild(dotGroup);
            }
        }

        // --- Earth dot ---
        const earthDotGroup = buildEarthDot(earthHeliocentric);
        if (earthDotGroup !== null) {
            svg.appendChild(earthDotGroup);
        }

        this.containerEl.appendChild(svg);
        this._svg = svg;
    }

    /**
     * Remove the SVG from the container and reset internal state.
     */
    clear() {
        this._removeSvg();
    }

    // --- Private ---

    _removeSvg() {
        if (this._svg && this._svg.parentNode) {
            this._svg.parentNode.removeChild(this._svg);
        }
        this._svg = null;
    }
}
