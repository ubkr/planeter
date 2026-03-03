/**
 * sky-map.js - SVG polar projection grid for the sky map tab.
 *
 * Renders a circular sky-dome chart where:
 *   - The zenith is at the centre of the SVG.
 *   - The horizon is the outer ring.
 *   - North (azimuth 0°) is at the top; East (azimuth 90°) is to the right.
 *
 * This is a compass-view (as if looking up from below with a compass overlaid),
 * NOT the mirror-reversed overhead star-chart convention. East is on the RIGHT,
 * matching what an observer sees when they hold a compass and look up.
 *
 * The module exports two names:
 *   altAzToXY  - pure coordinate-projection function (no DOM access)
 *   SkyMap     - class that renders the SVG grid into a container element
 */

const SVG_NS = 'http://www.w3.org/2000/svg';

// Fixed SVG coordinate space. All grid math works in these units; CSS scales
// the SVG to its container via the viewBox attribute.
const VIEW_SIZE = 500;
const CENTER_X = 250;
const CENTER_Y = 250;
// Horizon ring radius (leaves ~30 px of margin inside the 500×500 viewBox for
// cardinal labels that are placed slightly outside the ring).
const HORIZON_RADIUS = 220;

/**
 * Project an altitude/azimuth pair to an SVG {x, y} coordinate.
 *
 * Convention: North (az=0°) maps to the top of the chart; East (az=90°) maps
 * to the RIGHT of the chart. This is the compass-view convention — the same
 * direction an observer faces when looking toward the horizon with a compass.
 * It is NOT the mirror-reversed convention used in traditional printed star
 * charts (which flip East/West so the chart matches the sky when held overhead).
 *
 * Projection formula:
 *   r       = (90 - altitude_deg) / 90 * radius   (zenith → r=0; horizon → r=radius)
 *   az_rad  = azimuth_deg * Math.PI / 180
 *   x       = cx + r * sin(az_rad)
 *   y       = cy - r * cos(az_rad)
 *
 * @param {number} altitude_deg - Altitude above horizon in degrees (0 = horizon, 90 = zenith).
 * @param {number} azimuth_deg  - Azimuth in degrees, clockwise from North (0 = N, 90 = E, 180 = S, 270 = W).
 * @param {number} cx           - SVG x-coordinate of the zenith centre.
 * @param {number} cy           - SVG y-coordinate of the zenith centre.
 * @param {number} radius       - SVG radius of the horizon ring (altitude = 0°).
 * @returns {{ x: number, y: number }}
 */
export function altAzToXY(altitude_deg, azimuth_deg, cx, cy, radius) {
    const r = (90 - altitude_deg) / 90 * radius;
    const az_rad = azimuth_deg * Math.PI / 180;
    return {
        x: cx + r * Math.sin(az_rad),
        y: cy - r * Math.cos(az_rad),
    };
}

// ---------------------------------------------------------------------------
// Internal SVG creation helpers
// ---------------------------------------------------------------------------

/**
 * Create an SVG element in the SVG namespace.
 *
 * @param {string} tag - SVG element tag name (e.g. 'circle', 'text').
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

// ---------------------------------------------------------------------------
// Grid-building helpers (all return SVGElement, no side effects)
// ---------------------------------------------------------------------------

/**
 * Build the filled background circle that represents the sky dome.
 *
 * @returns {SVGCircleElement}
 */
function buildBackground() {
    const circle = svgEl('circle');
    setAttrs(circle, {
        cx: CENTER_X,
        cy: CENTER_Y,
        r: HORIZON_RADIUS,
        class: 'sky-map-bg',
    });
    return circle;
}

/**
 * Build one altitude ring and its label.
 *
 * The ring is placed at the radial distance that corresponds to the given
 * altitude. A text label showing the degree value is placed slightly inside
 * the ring at azimuth 135° (SE), chosen to avoid overlapping cardinal labels.
 *
 * @param {number} altitude_deg - Altitude in degrees (0, 30, or 60).
 * @returns {SVGGElement} A <g> containing the <circle> and <text>.
 */
function buildAltitudeRing(altitude_deg) {
    const r = (90 - altitude_deg) / 90 * HORIZON_RADIUS;
    const group = svgEl('g');

    // Ring circle.
    const circle = svgEl('circle');
    setAttrs(circle, {
        cx: CENTER_X,
        cy: CENTER_Y,
        r: r,
        class: 'sky-map-ring',
    });
    group.appendChild(circle);

    // Label — placed slightly inside the ring at az=135° (SE quadrant).
    // Using altitude slightly above the ring altitude keeps the label inside.
    const labelR = r - 6;
    const az_rad = 135 * Math.PI / 180;
    const lx = CENTER_X + labelR * Math.sin(az_rad);
    const ly = CENTER_Y - labelR * Math.cos(az_rad);

    const label = svgEl('text');
    setAttrs(label, {
        x: lx,
        y: ly,
        class: 'sky-map-label--muted',
        'text-anchor': 'middle',
        'dominant-baseline': 'central',
    });
    label.textContent = `${altitude_deg}\u00b0`;
    group.appendChild(label);

    return group;
}

/**
 * Build one cardinal direction label (N, O, S, or V) placed just outside the
 * horizon ring.
 *
 * Positioning uses altitude=-8° so the label sits slightly beyond the horizon
 * ring edge, clear of the ring stroke.
 *
 * @param {string} text        - Label text (e.g. 'N', 'O', 'S', 'V').
 * @param {number} azimuth_deg - Azimuth of the cardinal direction in degrees.
 * @param {string} textAnchor  - SVG text-anchor value ('start'|'middle'|'end').
 * @returns {SVGTextElement}
 */
function buildCardinalLabel(text, azimuth_deg, textAnchor) {
    const { x, y } = altAzToXY(-8, azimuth_deg, CENTER_X, CENTER_Y, HORIZON_RADIUS);

    const label = svgEl('text');
    setAttrs(label, {
        x: x,
        y: y,
        class: 'sky-map-label',
        'text-anchor': textAnchor,
    });
    label.textContent = text;
    return label;
}

/**
 * Build one intermediate tick label (NO, SO, SV, or NV) placed just outside
 * the horizon ring.
 *
 * @param {string} text        - Label text (e.g. 'NO').
 * @param {number} azimuth_deg - Azimuth in degrees (45, 135, 225, or 315).
 * @returns {SVGTextElement}
 */
function buildIntermediateLabel(text, azimuth_deg) {
    const { x, y } = altAzToXY(-8, azimuth_deg, CENTER_X, CENTER_Y, HORIZON_RADIUS);

    // Derive text-anchor and dominant-baseline from the azimuth quadrant so
    // labels are pushed away from the ring edge rather than centred on it.
    let textAnchor = 'middle';
    let dominantBaseline = 'central';

    if (azimuth_deg > 0 && azimuth_deg < 180) {
        textAnchor = 'start';    // right half → anchor at label start
    } else if (azimuth_deg > 180 && azimuth_deg < 360) {
        textAnchor = 'end';      // left half → anchor at label end
    }

    const label = svgEl('text');
    setAttrs(label, {
        x: x,
        y: y,
        class: 'sky-map-label sky-map-label--muted',
        'text-anchor': textAnchor,
        'dominant-baseline': dominantBaseline,
    });
    label.textContent = text;
    return label;
}

/**
 * Build the small filled circle marking the zenith at the chart centre.
 *
 * @returns {SVGCircleElement}
 */
function buildZenithDot() {
    const dot = svgEl('circle');
    setAttrs(dot, {
        cx: CENTER_X,
        cy: CENTER_Y,
        r: 3,
        class: 'sky-map-zenith',
    });
    return dot;
}

// ---------------------------------------------------------------------------
// SkyMap class
// ---------------------------------------------------------------------------

/**
 * SkyMap renders the SVG polar-projection sky-dome grid into a container
 * element and provides the coordinate system for Phase A3 planet plotting.
 *
 * Usage:
 *   const map = new SkyMap(document.getElementById('skyMapContainer'));
 *   map.render();
 */
export class SkyMap {
    /**
     * @param {HTMLElement} containerEl - The DOM element that will hold the SVG
     *   (expected to be `#skyMapContainer`).
     */
    constructor(containerEl) {
        this.container = containerEl;
        // Idempotency flag: set to true after the first successful render.
        this._rendered = false;
    }

    /**
     * Render the SVG polar-projection grid into the container.
     *
     * Idempotent — calling render() more than once does nothing after the
     * first call succeeds. This matches the tab-switch pattern where the
     * sky map tab may be shown repeatedly without triggering re-draws.
     */
    render() {
        if (this._rendered) return;

        // Remove any placeholder content (e.g. the <p> stub from index.html).
        this.container.innerHTML = '';

        // --- Root SVG element ---
        const svg = svgEl('svg');
        setAttrs(svg, {
            viewBox: `0 0 ${VIEW_SIZE} ${VIEW_SIZE}`,
            role: 'img',
            'aria-label': 'Stjärnkarta – polär projektion med horisontringar och väderstrecksmarkeringar',
        });
        // No explicit width/height — CSS controls sizing via .sky-map-container > svg.

        // 1. Sky dome background.
        svg.appendChild(buildBackground());

        // 2. Altitude rings at 0° (horizon), 30°, and 60°.
        //    Build from outermost inward so inner rings paint over outer ones
        //    where they share the same stroke position.
        for (const alt of [0, 30, 60]) {
            svg.appendChild(buildAltitudeRing(alt));
        }

        // 3. Cardinal direction labels just outside the horizon ring.
        //    Swedish compass convention: N=North, O=Öst (East), S=South, V=Väst (West).
        //
        //    text-anchor is set explicitly on each label; dominant-baseline is
        //    left to the CSS rule `.sky-map-label { dominant-baseline: central; }`
        //    so positioning is uniform across browsers.
        svg.appendChild(buildCardinalLabel('N',  0,   'middle'));
        svg.appendChild(buildCardinalLabel('O',  90,  'start'));
        svg.appendChild(buildCardinalLabel('S',  180, 'middle'));
        svg.appendChild(buildCardinalLabel('V',  270, 'end'));

        // 4. Intermediate tick labels at 45° intervals.
        svg.appendChild(buildIntermediateLabel('NO', 45));
        svg.appendChild(buildIntermediateLabel('SO', 135));
        svg.appendChild(buildIntermediateLabel('SV', 225));
        svg.appendChild(buildIntermediateLabel('NV', 315));

        // 5. Zenith dot at the chart centre.
        svg.appendChild(buildZenithDot());

        this.container.appendChild(svg);
        this._rendered = true;
    }
}
