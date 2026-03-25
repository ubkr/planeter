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

import { raDecToAltAz } from '../astro-projection.js';
import { azimuthToCompass } from '../utils.js';

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
        this._pendingPlanets = null;
        this._pendingConstellations = null;
        this._pendingStars = null;

        // Zoom state. The SVG coordinate space is always 500×500; the viewBox
        // shrinks or grows around the centre to implement zoom. Min 200, max 500.
        this._viewBoxSize = 500;
        // Guard so the wheel listener is only attached once per instance.
        this._wheelListenerAttached = false;
        // Touch pinch-zoom state. _pinchStartDistance holds the pixel distance
        // between the two touch points at the start of a pinch gesture.
        this._pinchStartDistance = null;
        // Guard so the touch listeners are only attached once per instance.
        this._touchListenerAttached = false;
    }

    // -------------------------------------------------------------------------
    // Zoom controls
    // -------------------------------------------------------------------------

    /**
     * Zoom in by reducing the viewBox size. The viewBox origin is recomputed so
     * the zoom is always centred on the chart centre (250, 250).
     *
     * Safe to call before render() — if the SVG does not exist yet the method
     * updates _viewBoxSize so the correct viewBox is applied when render() runs.
     *
     * @param {number} [step=50] - Number of SVG units to reduce the viewBox by.
     */
    zoomIn(step = 50) {
        this._viewBoxSize = Math.max(200, this._viewBoxSize - step);
        this._applyViewBox();
    }

    /**
     * Zoom out by increasing the viewBox size. The viewBox origin is recomputed
     * so the zoom is always centred on the chart centre (250, 250).
     *
     * @param {number} [step=50] - Number of SVG units to increase the viewBox by.
     */
    zoomOut(step = 50) {
        this._viewBoxSize = Math.min(500, this._viewBoxSize + step);
        this._applyViewBox();
    }

    /**
     * Reset zoom to the default 1:1 viewBox (0 0 500 500).
     */
    resetZoom() {
        this._viewBoxSize = 500;
        this._applyViewBox();
    }

    // -------------------------------------------------------------------------
    // Constellation controls
    // -------------------------------------------------------------------------

    /**
     * Show or hide the constellation layer.
     *
     * Safe to call before render() or before plotConstellations() has been
     * called — the method guards against a null constellation group.
     *
     * @param {boolean} enabled - If true, show constellations; if false, hide them.
     */
    setConstellationsVisible(enabled) {
        const svg = this.container.querySelector('svg');
        if (!svg) return;

        const consGroup = svg.querySelector('.sky-map-constellations');
        if (!consGroup) return;

        consGroup.style.display = enabled ? '' : 'none';
    }

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

    /**
     * Apply the current _viewBoxSize to the SVG element's viewBox attribute.
     *
     * The origin is computed so that the zoom is centred: when _viewBoxSize is
     * less than 500 the origin is positive, shifting the visible window inward
     * symmetrically on both axes.
     *
     * Formula:  origin = 250 - _viewBoxSize / 2
     *
     * This is a no-op if the SVG has not been rendered yet; render() sets the
     * initial viewBox from _viewBoxSize so the state is not lost.
     */
    _applyViewBox() {
        const svg = this.container.querySelector('svg');
        if (!svg) return;
        const origin = 250 - this._viewBoxSize / 2;
        svg.setAttribute('viewBox', `${origin} ${origin} ${this._viewBoxSize} ${this._viewBoxSize}`);
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
            overflow: 'visible',
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

        // Apply the viewBox from _viewBoxSize. This is normally "0 0 500 500"
        // but may differ if zoomIn/zoomOut was called before render().
        this._applyViewBox();

        // Attach the wheel-to-zoom listener once per instance. Wheel events on
        // the SVG itself zoom in/out; preventDefault stops the page from scrolling.
        if (!this._wheelListenerAttached) {
            svg.addEventListener('wheel', (event) => {
                event.preventDefault();
                if (event.deltaY < 0) {
                    this.zoomIn();
                } else if (event.deltaY > 0) {
                    this.zoomOut();
                }
            }, { passive: false });
            this._wheelListenerAttached = true;
        }

        // Attach touch pinch-zoom listeners once per instance. Two-finger
        // pinch gestures zoom in/out; { passive: false } is required so
        // preventDefault() can suppress native scroll and browser zoom.
        if (!this._touchListenerAttached) {
            svg.addEventListener('touchstart', (event) => {
                if (event.touches.length === 2) {
                    this._pinchStartDistance = this._getTouchDistance(event.touches);
                    event.preventDefault();
                }
            }, { passive: false });

            svg.addEventListener('touchmove', (event) => {
                if (event.touches.length === 2 && this._pinchStartDistance !== null) {
                    const currentDistance = this._getTouchDistance(event.touches);
                    const delta = currentDistance - this._pinchStartDistance;
                    // Only trigger zoom when the finger movement exceeds 5 px to
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
            svg.addEventListener('touchend',    resetPinch);
            svg.addEventListener('touchcancel', resetPinch);

            this._touchListenerAttached = true;
        }

        this._rendered = true;

        // If plotConstellations() was called before render() completed, replay it now.
        // Constellations are replayed before bodies so layering is correct.
        if (this._pendingConstellations !== null) {
            const { constellationData, lat, lon, utcTimestamp, opacity } = this._pendingConstellations;
            this.plotConstellations(constellationData, lat, lon, utcTimestamp, opacity);
        }

        // If plotStars() was called before render() completed, replay it now.
        // Stars are replayed after constellations and before bodies so they
        // render behind planets.
        if (this._pendingStars !== null) {
            const { stars, limitingMagnitude, lat, lon, utcTimestamp } = this._pendingStars;
            this.plotStars(stars, limitingMagnitude, lat, lon, utcTimestamp);
        }

        // If plotBodies() was called before render() completed, replay it now.
        if (this._pendingPlanets !== null) {
            this.plotBodies(this._pendingPlanets, this._pendingSun, this._pendingMoon, this._pendingEvents || []);
        }
    }

    /**
     * Plot constellations onto the sky map as line segments with IAU labels.
     *
     * Safe to call before render() — arguments are stored and replayed once
     * the SVG grid is ready. Safe to call multiple times — the constellation
     * layer is fully rebuilt on every call.
     *
     * Constellations whose every vertex lies below the horizon (altitude < 0)
     * are skipped entirely and not rendered.
     *
     * The constellation group is inserted before the bodies group (.sky-map-bodies)
     * so constellations render behind planets, the Sun, and the Moon.
     *
     * @param {Object[]} constellationData - Parsed JSON array from constellations.json.
     *   Each entry has:
     *     iau   {string}    - IAU three-letter abbreviation (e.g. 'UMa').
     *     name  {string}    - Full Latin name.
     *     lines {number[][]} - Array of [ra1, dec1, ra2, dec2] segments in degrees.
     * @param {number} lat          - Observer latitude in degrees (positive North).
     * @param {number} lon          - Observer longitude in degrees (positive East).
     * @param {Date|number} utcTimestamp - UTC instant as a JS Date or Unix ms.
     * @param {number} [opacity=0.25] - Opacity for the entire constellation layer (0–1).
     */
    plotConstellations(constellationData, lat, lon, utcTimestamp, opacity = 0.25) {
        // Defer if the SVG grid has not been rendered yet.
        if (!this._rendered || !this.container.querySelector('svg')) {
            this._pendingConstellations = { constellationData, lat, lon, utcTimestamp, opacity };
            return;
        }

        if (!Array.isArray(constellationData)) return;

        // Clear pending state — we are rendering now.
        this._pendingConstellations = null;

        const svg = this.container.querySelector('svg');

        // Reuse or create the constellation layer group. Clear it so each call
        // is idempotent: old lines and labels are removed before rebuilding.
        let consGroup = svg.querySelector('.sky-map-constellations');
        if (!consGroup) {
            consGroup = document.createElementNS(SVG_NS, 'g');
            consGroup.setAttribute('class', 'sky-map-constellations');

            // Insert before .sky-map-bodies if it already exists, otherwise
            // append. This guarantees constellations paint behind the bodies.
            const bodiesGroup = svg.querySelector('.sky-map-bodies');
            if (bodiesGroup) {
                svg.insertBefore(consGroup, bodiesGroup);
            } else {
                svg.appendChild(consGroup);
            }
        } else {
            while (consGroup.firstChild) {
                consGroup.removeChild(consGroup.firstChild);
            }
        }

        // Apply opacity to the entire constellation layer. This cascades to
        // all child lines and labels, so we don't need to set opacity on
        // individual elements.
        consGroup.setAttribute('opacity', opacity);

        for (const constellation of constellationData) {
            const { iau, lines } = constellation;

            if (!Array.isArray(lines) || lines.length === 0) continue;

            // Convert every unique vertex (RA/Dec pair) to alt/az. A vertex
            // appears twice in different segments so we process per-segment.
            // Collect projected endpoints for all segments; track which are
            // above the horizon for the visibility test and label placement.
            const segments = [];
            let allBelowHorizon = true;

            for (const segment of lines) {
                const [ra1, dec1, ra2, dec2] = segment;

                const { altitude_deg: alt1, azimuth_deg: az1 } =
                    raDecToAltAz(ra1, dec1, lat, lon, utcTimestamp);
                const { altitude_deg: alt2, azimuth_deg: az2 } =
                    raDecToAltAz(ra2, dec2, lat, lon, utcTimestamp);

                const xy1 = altAzToXY(alt1, az1, CENTER_X, CENTER_Y, HORIZON_RADIUS);
                const xy2 = altAzToXY(alt2, az2, CENTER_X, CENTER_Y, HORIZON_RADIUS);

                segments.push({ xy1, xy2, alt1, alt2 });

                // If at least one endpoint is above the horizon, the
                // constellation is considered partially visible.
                if (alt1 >= 0 || alt2 >= 0) {
                    allBelowHorizon = false;
                }
            }

            // Skip constellations that are entirely below the horizon.
            if (allBelowHorizon) continue;

            // Draw each line segment.
            for (const { xy1, xy2 } of segments) {
                const line = document.createElementNS(SVG_NS, 'line');
                setAttrs(line, {
                    x1: xy1.x,
                    y1: xy1.y,
                    x2: xy2.x,
                    y2: xy2.y,
                    class: 'sky-map-constellation-line',
                });
                consGroup.appendChild(line);
            }

            // Compute the geometric centre from endpoints that are above the
            // horizon. This keeps the label inside the visible sky dome.
            let sumX = 0;
            let sumY = 0;
            let count = 0;

            for (const { xy1, xy2, alt1, alt2 } of segments) {
                if (alt1 >= 0) { sumX += xy1.x; sumY += xy1.y; count++; }
                if (alt2 >= 0) { sumX += xy2.x; sumY += xy2.y; count++; }
            }

            // count is guaranteed > 0 because allBelowHorizon is false.
            const labelX = sumX / count;
            const labelY = sumY / count;

            const label = document.createElementNS(SVG_NS, 'text');
            setAttrs(label, {
                x: labelX,
                y: labelY,
                class: 'sky-map-constellation-label',
            });
            label.textContent = iau;
            consGroup.appendChild(label);
        }
    }

    /**
     * Plot background stars onto the sky map as small filled circles.
     *
     * Stars are decorative — they have no labels or tooltips. They are rendered
     * in a dedicated layer behind planets, the Sun, and the Moon, but in front
     * of constellation lines.
     *
     * Safe to call before render() — arguments are stored and replayed once
     * the SVG grid is ready. Safe to call multiple times — the star layer is
     * fully rebuilt on every call.
     *
     * @param {Object[]} stars           - Array of star objects. Each must have:
     *   ra_deg {number}, dec_deg {number}, magnitude {number}.
     * @param {number} limitingMagnitude - Stars fainter than this value are skipped.
     * @param {number} lat               - Observer latitude in degrees (positive North).
     * @param {number} lon               - Observer longitude in degrees (positive East).
     * @param {Date|number} utcTimestamp - UTC instant as a JS Date or Unix ms.
     */
    plotStars(stars, limitingMagnitude, lat, lon, utcTimestamp) {
        // Defer if the SVG grid has not been rendered yet.
        if (!this._rendered) {
            this._pendingStars = { stars, limitingMagnitude, lat, lon, utcTimestamp };
            return;
        }

        if (!Array.isArray(stars)) return;

        // Clear pending state — we are rendering now.
        this._pendingStars = null;

        const svg = this.container.querySelector('svg');

        // Reuse or create the star layer group. Clear it so each call is
        // idempotent: old circles are removed before rebuilding.
        let starsGroup = svg.querySelector('.sky-map-stars');
        if (!starsGroup) {
            starsGroup = document.createElementNS(SVG_NS, 'g');
            starsGroup.setAttribute('class', 'sky-map-stars');

            // Insert after .sky-map-constellations (stars in front of
            // constellation lines) and before .sky-map-bodies (stars behind
            // planets). Handle the case where either layer may not exist yet.
            const consGroup = svg.querySelector('.sky-map-constellations');
            const bodiesGroup = svg.querySelector('.sky-map-bodies');

            if (consGroup) {
                // Insert immediately after the constellation group. SVG has no
                // insertAfter, so we use the next sibling as the reference node.
                const nextSibling = consGroup.nextSibling;
                if (nextSibling) {
                    svg.insertBefore(starsGroup, nextSibling);
                } else {
                    svg.appendChild(starsGroup);
                }
            } else if (bodiesGroup) {
                svg.insertBefore(starsGroup, bodiesGroup);
            } else {
                svg.appendChild(starsGroup);
            }
        } else {
            while (starsGroup.firstChild) {
                starsGroup.removeChild(starsGroup.firstChild);
            }
        }

        for (const star of stars) {
            // Skip stars that are too faint for the current sky brightness.
            if (star.magnitude > limitingMagnitude) continue;

            const { altitude_deg, azimuth_deg } = raDecToAltAz(
                star.ra_deg,
                star.dec_deg,
                lat,
                lon,
                utcTimestamp,
            );

            // Guard against bad coordinate data and skip stars below the horizon.
            if (isNaN(altitude_deg) || isNaN(azimuth_deg) || altitude_deg <= 0) continue;

            const { x, y } = altAzToXY(altitude_deg, azimuth_deg, CENTER_X, CENTER_Y, HORIZON_RADIUS);

            // Radius scales inversely with magnitude: brighter (lower) → larger.
            // Clamped to [1, 4] so faint stars are still visible as single pixels.
            const radius = Math.max(1, Math.min(4, 3 - star.magnitude * 0.7));

            const compassDirection = azimuthToCompass(azimuth_deg);
            const tooltipText =
                `${star.name}\n` +
                `Höjd: ${altitude_deg.toFixed(1)}°\n` +
                `Riktning: ${compassDirection}\n` +
                `Magnitud: ${star.magnitude.toFixed(2)}`;

            const circle = document.createElementNS(SVG_NS, 'circle');
            circle.setAttribute('class', 'sky-map-star info-icon');
            circle.setAttribute('cx', x);
            circle.setAttribute('cy', y);
            circle.setAttribute('r', radius);
            circle.setAttribute('tabindex', '0');
            circle.setAttribute('role', 'img');
            circle.setAttribute('aria-label', star.name);
            circle.dataset.tooltipTitle = tooltipText;
            starsGroup.appendChild(circle);
        }
    }

    /**
     * Plot celestial bodies (planets, Sun, Moon) onto the sky map, and
     * optionally overlay event indicators for conjunctions, moon occultations,
     * and oppositions.
     *
     * Safe to call before render() — the data is stored and replayed once the
     * SVG grid is ready. Safe to call multiple times — the body layer is fully
     * rebuilt on every call so stale dots are never left behind.
     *
     * @param {Object[]} planets - Array of planet objects from the API.
     *   Each object must have: name, name_sv, altitude_deg, azimuth_deg,
     *   direction, magnitude.
     * @param {Object} sun - Sun object with elevation_deg and azimuth_deg.
     * @param {Object} moon - Moon object with elevation_deg, azimuth_deg,
     *   and illumination (0–1 float).
     * @param {Object[]} [events=[]] - Array of AstronomicalEvent objects from the API.
     *   Used to draw conjunction lines and opposition glows on the chart.
     */
    plotBodies(planets, sun, moon, events = []) {
        // Defer if the SVG grid has not been rendered yet.
        if (!this._rendered || !this.container.querySelector('svg')) {
            this._pendingPlanets = planets;
            this._pendingSun = sun;
            this._pendingMoon = moon;
            this._pendingEvents = events;
            return;
        }

        if (!Array.isArray(planets)) return;

        // Clear pending state — we are rendering now.
        this._pendingPlanets = null;
        this._pendingSun = undefined;
        this._pendingMoon = undefined;
        this._pendingEvents = undefined;

        const svg = this.container.querySelector('svg');

        // Reuse or create the body layer group. Clear it so each call is
        // idempotent: old dots and labels are removed before rebuilding.
        let bodiesGroup = svg.querySelector('.sky-map-bodies');
        if (!bodiesGroup) {
            bodiesGroup = svgEl('g');
            bodiesGroup.setAttribute('class', 'sky-map-bodies');
            svg.appendChild(bodiesGroup);
        } else {
            while (bodiesGroup.firstChild) {
                bodiesGroup.removeChild(bodiesGroup.firstChild);
            }
        }

        // --- Planets ---
        for (const planet of planets) {
            const { x, y } = altAzToXY(
                planet.altitude_deg,
                planet.azimuth_deg,
                CENTER_X,
                CENTER_Y,
                HORIZON_RADIUS,
            );

            // Radius scales inversely with magnitude: brighter (lower mag) → larger dot.
            const radius = Math.max(4, Math.min(12, 8 - planet.magnitude));

            const belowHorizon = planet.altitude_deg < 0;
            const opacityAttr = belowHorizon ? '0.3' : '1';

            const tooltipText =
                `${planet.name_sv}\n` +
                `Höjd: ${planet.altitude_deg.toFixed(1)}°\n` +
                `Riktning: ${planet.direction}\n` +
                `Magnitud: ${planet.magnitude.toFixed(1)}`;

            const dot = svgEl('circle');
            setAttrs(dot, {
                cx: x,
                cy: y,
                r: radius,
                class: `sky-map-body sky-map-body--${planet.name.toLowerCase()} info-icon`,
                opacity: opacityAttr,
                'aria-label': planet.name_sv,
                tabindex: '0',
                role: 'img',
            });
            dot.dataset.tooltipTitle = tooltipText;
            bodiesGroup.appendChild(dot);

            const label = svgEl('text');
            setAttrs(label, {
                x: x + radius + 3,
                y: y - radius,
                class: 'sky-map-body-label',
                opacity: opacityAttr,
                'pointer-events': 'none',
            });
            label.textContent = planet.name_sv;
            bodiesGroup.appendChild(label);
        }

        // --- Sun ---
        if (sun) {
            const { x, y } = altAzToXY(
                sun.elevation_deg,
                sun.azimuth_deg,
                CENTER_X,
                CENTER_Y,
                HORIZON_RADIUS,
            );

            const belowHorizon = sun.elevation_deg < 0;
            const opacityAttr = belowHorizon ? '0.3' : '1';
            const sunRadius = 10;

            const tooltipText =
                `Solen\n` +
                `Höjd: ${sun.elevation_deg.toFixed(1)}°`;

            const dot = svgEl('circle');
            setAttrs(dot, {
                cx: x,
                cy: y,
                r: sunRadius,
                class: 'sky-map-body sky-map-body--sun info-icon',
                opacity: opacityAttr,
                'aria-label': 'Solen',
                tabindex: '0',
                role: 'img',
            });
            dot.dataset.tooltipTitle = tooltipText;
            bodiesGroup.appendChild(dot);

            const label = svgEl('text');
            setAttrs(label, {
                x: x + sunRadius + 3,
                y: y - sunRadius,
                class: 'sky-map-body-label',
                opacity: opacityAttr,
                'pointer-events': 'none',
            });
            label.textContent = 'Solen';
            bodiesGroup.appendChild(label);
        }

        // --- Moon ---
        if (moon) {
            const { x, y } = altAzToXY(
                moon.elevation_deg,
                moon.azimuth_deg,
                CENTER_X,
                CENTER_Y,
                HORIZON_RADIUS,
            );

            const belowHorizon = moon.elevation_deg < 0;
            const opacityAttr = belowHorizon ? '0.3' : '1';
            const moonRadius = 8;

            const tooltipText =
                `Månen\n` +
                `Höjd: ${moon.elevation_deg.toFixed(1)}°\n` +
                `Belysning: ${Math.round(moon.illumination * 100)}%`;

            const dot = svgEl('circle');
            setAttrs(dot, {
                cx: x,
                cy: y,
                r: moonRadius,
                class: 'sky-map-body sky-map-body--moon info-icon',
                opacity: opacityAttr,
                'aria-label': 'Månen',
                tabindex: '0',
                role: 'img',
            });
            dot.dataset.tooltipTitle = tooltipText;
            bodiesGroup.appendChild(dot);

            const label = svgEl('text');
            setAttrs(label, {
                x: x + moonRadius + 3,
                y: y - moonRadius,
                class: 'sky-map-body-label',
                opacity: opacityAttr,
                'pointer-events': 'none',
            });
            label.textContent = 'Månen';
            bodiesGroup.appendChild(label);
        }

        // --- Event indicators ---
        // Build a lookup table from lowercase body name to its plotted {x, y} position
        // and the circle element (for opposition glow). Only bodies plotted above the
        // horizon are included so indicators only appear for visible bodies.
        if (Array.isArray(events) && events.length > 0) {
            // Map: body name (lowercase) → { x, y, el }
            const bodyPositions = new Map();

            for (const planet of planets) {
                if (planet.altitude_deg >= 0) {
                    const pos = altAzToXY(planet.altitude_deg, planet.azimuth_deg, CENTER_X, CENTER_Y, HORIZON_RADIUS);
                    // The circle element is the last child added for this planet.
                    // We need to find it by class to attach the opposition modifier.
                    const circleEl = bodiesGroup.querySelector(`.sky-map-body--${planet.name.toLowerCase()}`);
                    bodyPositions.set(planet.name.toLowerCase(), { ...pos, el: circleEl });
                }
            }

            // Also include Sun and Moon so conjunction lines can connect them.
            if (sun && sun.elevation_deg >= 0) {
                const pos = altAzToXY(sun.elevation_deg, sun.azimuth_deg, CENTER_X, CENTER_Y, HORIZON_RADIUS);
                const circleEl = bodiesGroup.querySelector('.sky-map-body--sun');
                bodyPositions.set('sun', { ...pos, el: circleEl });
            }
            if (moon && moon.elevation_deg >= 0) {
                const pos = altAzToXY(moon.elevation_deg, moon.azimuth_deg, CENTER_X, CENTER_Y, HORIZON_RADIUS);
                const circleEl = bodiesGroup.querySelector('.sky-map-body--moon');
                bodyPositions.set('moon', { ...pos, el: circleEl });
            }

            for (const event of events) {
                const type = event.event_type;

                if (type === 'conjunction' || type === 'moon_occultation') {
                    // Conjunction / occultation: draw a dashed line between the two
                    // bodies involved. The API encodes bodies in the description but
                    // also provides a `bodies` array when available. Fall back to
                    // checking known planet names present in bodyPositions.
                    const involved = Array.isArray(event.bodies)
                        ? event.bodies.map((b) => b.toLowerCase())
                        : [];

                    if (involved.length >= 2) {
                        const posA = bodyPositions.get(involved[0]);
                        const posB = bodyPositions.get(involved[1]);

                        if (posA && posB) {
                            const line = svgEl('line');
                            setAttrs(line, {
                                x1: posA.x,
                                y1: posA.y,
                                x2: posB.x,
                                y2: posB.y,
                                class: 'sky-map-conjunction-line',
                                'pointer-events': 'none',
                            });
                            // Insert the line before the bodies group so it renders behind dots.
                            svg.insertBefore(line, bodiesGroup);
                        }
                    }
                }

                if (type === 'opposition') {
                    // Opposition: add a glow modifier class to the planet's circle.
                    const bodyName = Array.isArray(event.bodies) && event.bodies.length > 0
                        ? event.bodies[0].toLowerCase()
                        : null;

                    if (bodyName) {
                        const info = bodyPositions.get(bodyName);
                        if (info && info.el) {
                            info.el.classList.add('sky-map-body--opposition');
                        }
                    }
                }
            }
        }
    }
}
