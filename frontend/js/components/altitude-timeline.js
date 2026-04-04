/**
 * altitude-timeline.js - Renders a 24-hour SVG altitude timeline chart
 * for the five naked-eye planets, the Sun, and the Moon.
 *
 * Expects the full response from GET /api/v1/planets/timeline, which includes:
 *   - timestamp (UTC ISO 8601)
 *   - location { lat, lon, name }
 *   - sample_interval_minutes (15)
 *   - series[] — 7 objects with { name, samples[{ time_offset_minutes, altitude_deg }] }
 */

const SVG_NS = 'http://www.w3.org/2000/svg';

/** ViewBox dimensions */
const VB_W = 800;
const VB_H = 360;

/** Margins inside the viewBox */
const MARGIN = { top: 10, right: 10, bottom: 35, left: 55 };

/** Derived chart area */
const CHART_W = VB_W - MARGIN.left - MARGIN.right;   // 735
const CHART_H = VB_H - MARGIN.top - MARGIN.bottom;    // 315

/** X-axis minute range */
const X_MIN = 0;
const X_MAX = 1440;

/** CSS variable names mapped to series name */
const COLOR_TOKENS = {
    Mercury: '--color-planet-mercury',
    Venus:   '--color-planet-venus',
    Mars:    '--color-planet-mars',
    Jupiter: '--color-planet-jupiter',
    Saturn:  '--color-planet-saturn',
    Sun:     '--color-sun-penalty',
    Moon:    '--color-moon-penalty',
};

/** Swedish display names */
const SWEDISH_NAMES = {
    Mercury: 'Merkurius',
    Venus:   'Venus',
    Mars:    'Mars',
    Jupiter: 'Jupiter',
    Saturn:  'Saturnus',
    Sun:     'Solen',
    Moon:    'Månen',
};

/** X-axis tick positions and labels */
const X_TICKS = [
    { minutes: 0,    label: 'Nu' },
    { minutes: 360,  label: '+6h' },
    { minutes: 720,  label: '+12h' },
    { minutes: 1080, label: '+18h' },
    { minutes: 1440, label: '+24h' },
];

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/**
 * Read a CSS custom property from :root.
 * @param {string} name - Variable name including the leading --.
 * @returns {string}
 */
function cssVar(name) {
    return getComputedStyle(document.documentElement).getPropertyValue(name).trim();
}

/**
 * Create an SVG element with optional attributes.
 * @param {string} tag
 * @param {Record<string, string|number>} [attrs]
 * @returns {SVGElement}
 */
function svgEl(tag, attrs) {
    const el = document.createElementNS(SVG_NS, tag);
    if (attrs) {
        for (const [k, v] of Object.entries(attrs)) {
            el.setAttribute(k, String(v));
        }
    }
    return el;
}

/**
 * Map a value from a domain to the chart pixel range.
 * @param {number} value
 * @param {number} domainMin
 * @param {number} domainMax
 * @param {number} rangeMin
 * @param {number} rangeMax
 * @returns {number}
 */
function scale(value, domainMin, domainMax, rangeMin, rangeMax) {
    const t = (value - domainMin) / (domainMax - domainMin);
    return rangeMin + t * (rangeMax - rangeMin);
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export class AltitudeTimeline {
    /**
     * @param {HTMLElement} containerEl - The element that will receive the chart.
     */
    constructor(containerEl) {
        this.container = containerEl;
    }

    /**
     * Render the altitude timeline chart from a full timeline API response.
     *
     * @param {Object} data - Full /api/v1/planets/timeline response.
     * @param {Object[]} data.series - Array of 7 series objects.
     */
    render(data) {
        this.container.innerHTML = '';

        const series = data.series;
        if (!series || !series.length) {
            this.showEmpty();
            return;
        }

        // --- Compute Y-axis range from data ---
        let minAlt = Infinity;
        let maxAlt = -Infinity;

        for (const s of series) {
            for (const sample of s.samples) {
                if (sample.altitude_deg != null) {
                    if (sample.altitude_deg < minAlt) minAlt = sample.altitude_deg;
                    if (sample.altitude_deg > maxAlt) maxAlt = sample.altitude_deg;
                }
            }
        }

        // Clamp to safe defaults if no valid data
        if (!isFinite(minAlt)) minAlt = -15;
        if (!isFinite(maxAlt)) maxAlt = 90;

        const yMin = Math.max(Math.floor(minAlt / 15) * 15, -90);
        const yMax = Math.min(Math.ceil(maxAlt / 15) * 15, 90);

        // Read colour tokens
        const colors = {};
        for (const [name, token] of Object.entries(COLOR_TOKENS)) {
            colors[name] = cssVar(token) || '#888';
        }

        // --- Build wrapper ---
        const wrapper = document.createElement('div');
        wrapper.className = 'altitude-timeline';

        // --- Build SVG ---
        const svg = svgEl('svg', {
            viewBox: `0 0 ${VB_W} ${VB_H}`,
            width: '100%',
            height: 'auto',
            preserveAspectRatio: 'xMidYMid meet',
            role: 'img',
            'aria-label': 'Höjdkurva för planeter, solen och månen de kommande 24 timmarna',
        });

        // Accessible title
        const titleEl = svgEl('title');
        titleEl.textContent = 'Höjdkurva — 24 timmar';
        svg.appendChild(titleEl);

        // --- Gridlines & axes ---
        const gridColor = cssVar('--color-chart-grid');
        const horizonColor = cssVar('--color-chart-horizon');
        const labelColor = cssVar('--color-text-secondary') || '#8e9bb3';

        // Y-axis gridlines and labels (regular grid only — horizon handled separately below)
        for (let deg = yMin; deg <= yMax; deg += 15) {
            if (deg === 0) continue; // rendered separately so it always appears when in range

            const y = scale(deg, yMin, yMax, MARGIN.top + CHART_H, MARGIN.top);

            const line = svgEl('line', {
                x1: MARGIN.left,
                y1: y,
                x2: MARGIN.left + CHART_W,
                y2: y,
                stroke: gridColor,
                'stroke-width': 1,
                'stroke-dasharray': 'none',
            });
            svg.appendChild(line);

            const label = svgEl('text', {
                x: MARGIN.left - 5,
                y: y,
                'text-anchor': 'end',
                'dominant-baseline': 'central',
                fill: labelColor,
                'font-size': 11,
                'font-family': cssVar('--font-family-base') || 'Inter, sans-serif',
            });
            label.textContent = `${deg}\u00b0`;
            svg.appendChild(label);
        }

        // Horizon line at 0° — always drawn when 0° is within the Y-axis domain
        if (0 >= yMin && 0 <= yMax) {
            const hy = scale(0, yMin, yMax, MARGIN.top + CHART_H, MARGIN.top);

            const horizonLine = svgEl('line', {
                x1: MARGIN.left,
                y1: hy,
                x2: MARGIN.left + CHART_W,
                y2: hy,
                stroke: horizonColor,
                'stroke-width': 1.5,
                'stroke-dasharray': '6 4',
            });
            svg.appendChild(horizonLine);

            const horizonLabel = svgEl('text', {
                x: MARGIN.left - 5,
                y: hy,
                'text-anchor': 'end',
                'dominant-baseline': 'central',
                fill: cssVar('--color-text-primary') || '#fff',
                'font-size': 11,
                'font-family': cssVar('--font-family-base') || 'Inter, sans-serif',
            });
            horizonLabel.textContent = '0\u00b0';
            svg.appendChild(horizonLabel);
        }

        // X-axis gridlines and labels
        for (const tick of X_TICKS) {
            const x = scale(tick.minutes, X_MIN, X_MAX, MARGIN.left, MARGIN.left + CHART_W);

            const line = svgEl('line', {
                x1: x,
                y1: MARGIN.top,
                x2: x,
                y2: MARGIN.top + CHART_H,
                stroke: gridColor,
                'stroke-width': 1,
            });
            svg.appendChild(line);

            const label = svgEl('text', {
                x: x,
                y: MARGIN.top + CHART_H + 20,
                'text-anchor': 'middle',
                fill: labelColor,
                'font-size': 11,
                'font-family': cssVar('--font-family-base') || 'Inter, sans-serif',
            });
            label.textContent = tick.label;
            svg.appendChild(label);
        }

        // --- Plot series ---
        for (const s of series) {
            const color = colors[s.name] || '#888';
            const segments = this._buildSegments(s.samples, yMin, yMax);

            for (const seg of segments) {
                const polyline = svgEl('polyline', {
                    points: seg,
                    stroke: color,
                    'stroke-width': 2,
                    fill: 'none',
                    'stroke-linecap': 'round',
                    'stroke-linejoin': 'round',
                });
                svg.appendChild(polyline);
            }
        }

        wrapper.appendChild(svg);

        // --- Legend (HTML) ---
        const legend = document.createElement('div');
        legend.className = 'altitude-timeline__legend';

        for (const s of series) {
            const color = colors[s.name] || '#888';
            const swedishName = SWEDISH_NAMES[s.name] || s.name;

            const item = document.createElement('span');
            item.className = 'altitude-timeline__legend-item';

            const swatch = document.createElement('span');
            swatch.className = 'altitude-timeline__legend-swatch';
            swatch.style.background = color;

            item.appendChild(swatch);
            item.appendChild(document.createTextNode(` ${swedishName}`));
            legend.appendChild(item);
        }

        wrapper.appendChild(legend);
        this.container.appendChild(wrapper);
    }

    /**
     * Show a loading skeleton placeholder.
     */
    showLoading() {
        this.container.innerHTML = `
            <div class="altitude-timeline altitude-timeline--loading">
                <div class="altitude-timeline__skeleton" aria-busy="true" aria-label="Laddar höjdkurva">
                    <div class="altitude-timeline__skeleton-chart"></div>
                </div>
            </div>
        `;
    }

    /**
     * Show an error/empty state message.
     */
    showEmpty() {
        this.container.innerHTML = `
            <div class="altitude-timeline altitude-timeline--empty">
                <p class="altitude-timeline__empty-msg">Kunde inte ladda höjdkurva. Försök igen senare.</p>
            </div>
        `;
    }

    /**
     * Remove all content from the container.
     */
    clear() {
        this.container.innerHTML = '';
    }

    // -----------------------------------------------------------------------
    // Private helpers
    // -----------------------------------------------------------------------

    /**
     * Break a samples array into continuous polyline segments, skipping nulls.
     *
     * Each segment is a string of "x,y" pairs suitable for a <polyline> points
     * attribute.
     *
     * @param {Object[]} samples - Array of { time_offset_minutes, altitude_deg }.
     * @param {number} yMin - Y-axis domain minimum (degrees).
     * @param {number} yMax - Y-axis domain maximum (degrees).
     * @returns {string[]} Array of "x1,y1 x2,y2 ..." point strings.
     * @private
     */
    _buildSegments(samples, yMin, yMax) {
        const segments = [];
        let current = [];

        for (const sample of samples) {
            if (sample.altitude_deg == null) {
                // Null value: close current segment if any
                if (current.length) {
                    segments.push(current.join(' '));
                    current = [];
                }
                continue;
            }

            const x = scale(sample.time_offset_minutes, X_MIN, X_MAX, MARGIN.left, MARGIN.left + CHART_W);
            const y = scale(sample.altitude_deg, yMin, yMax, MARGIN.top + CHART_H, MARGIN.top);

            current.push(`${x.toFixed(1)},${y.toFixed(1)}`);
        }

        if (current.length) {
            segments.push(current.join(' '));
        }

        return segments;
    }
}
