/**
 * sky-summary.js - Renders the sky summary banner for the current observation window.
 *
 * Expects the full PlanetsResponse object from GET /api/v1/planets/visible.
 * Relevant top-level fields: planets, sun, weather, location, tonight_score.
 */

import { scoreToLevel, formatLocation } from '../utils.js';

// Swedish translations for twilight phase identifiers.
const TWILIGHT_LABELS = {
    daylight: 'Dagsljus',
    civil_twilight: 'Civil skymning',
    nautical_twilight: 'Nautisk skymning',
    astronomical_twilight: 'Astronomisk skymning',
    darkness: 'M\u00f6rker',
};

/**
 * Translate a twilight phase key to Swedish.
 *
 * @param {string} phase - API twilight_phase value.
 * @returns {string} Swedish label.
 */
function translateTwilight(phase) {
    return TWILIGHT_LABELS[phase] ?? 'Ok\u00e4nd';
}

/**
 * Compute the overall visibility score from a planets array.
 *
 * Returns the average visibility_score across all planets, rounded to the
 * nearest integer. Falls back to 0 if the array is empty.
 *
 * @param {Object[]} planets - Array of planet objects.
 * @returns {number}
 */
function computeOverallScore(planets) {
    if (!planets.length) return 0;
    const sum = planets.reduce((acc, p) => acc + p.visibility_score, 0);
    return Math.round(sum / planets.length);
}

/**
 * Build the cloud cover display string, appending "(uppskattad)" for fallback sources.
 *
 * @param {Object} weather - Weather object with cloud_cover and source fields.
 * @returns {string}
 */
function formatCloudCover(weather) {
    const isFallback =
        weather.source === 'fallback' || weather.source === 'open-meteo-fallback';
    const base = `${Math.round(weather.cloud_cover)}%`;
    return isFallback ? `${base} (uppskattad)` : base;
}

/**
 * Determine whether midnight sun conditions apply.
 *
 * True when every planet has visibility_score === 0 and the sun's twilight
 * phase is "daylight".
 *
 * @param {Object[]} planets
 * @param {Object} sun
 * @returns {boolean}
 */
function isMidnightSun(planets, sun) {
    return (
        sun.twilight_phase === 'daylight' &&
        planets.every(p => p.visibility_score === 0)
    );
}

/**
 * SkySummary renders an overview banner with the current sky conditions.
 *
 * Usage:
 *   const summary = new SkySummary(document.getElementById('skySummary'));
 *   summary.showLoading();
 *   summary.render(apiResponse);
 */
export class SkySummary {
    /**
     * @param {HTMLElement} containerEl - The element that will receive the banner.
     */
    constructor(containerEl) {
        this.container = containerEl;
    }

    /**
     * Render the sky summary from a full PlanetsResponse object.
     *
     * @param {Object} data - Full API response object.
     * @param {Object[]} data.planets
     * @param {Object} data.sun
     * @param {Object} data.weather
     * @param {Object} data.location
     * @param {number} [data.tonight_score] - Optional pre-computed overall score.
     */
    render(data) {
        const { planets, sun, weather, location } = data;

        const overallScore =
            typeof data.tonight_score === 'number'
                ? data.tonight_score
                : computeOverallScore(planets);

        const level = scoreToLevel(overallScore);
        const visibleCount = planets.filter(p => p.visibility_score > 50).length;
        const midnightSun = isMidnightSun(planets, sun);

        const summaryLabel = midnightSun
            ? 'Midnattssol \u2013 inga planeter synliga ikv\u00e4ll'
            : 'Synlighet just nu';

        const infoHTML = midnightSun
            ? ''
            : `
            <div class="sky-summary__info-item">
                <strong>Skymning</strong>
                <span class="sky-summary__value">${translateTwilight(sun.twilight_phase)}</span>
            </div>
            <div class="sky-summary__info-item">
                <strong>Molnighet</strong>
                <span class="sky-summary__value">${formatCloudCover(weather)}</span>
            </div>
            <div class="sky-summary__info-item">
                <strong>Plats</strong>
                <span class="sky-summary__value">${formatLocation(location)}</span>
            </div>
        `;

        this.container.innerHTML = `
            <div class="sky-summary" data-score-level="${level}">
                <div class="sky-summary__score-block">
                    <div class="sky-summary__score" data-score-level="${level}">${overallScore}</div>
                    <div class="sky-summary__label">${summaryLabel}</div>
                </div>
                <div class="sky-summary__info">
                    <div class="sky-summary__planet-count">${visibleCount} av 5 planeter synliga</div>
                    ${infoHTML}
                </div>
            </div>
        `;
    }

    /**
     * Show a loading skeleton while data is being fetched.
     */
    showLoading() {
        this.container.innerHTML = `
            <div class="sky-summary sky-summary--loading">
                <div class="sky-summary__score-block">
                    <div class="sky-summary__score">&nbsp;&nbsp;</div>
                    <div class="sky-summary__label">&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;</div>
                </div>
                <div class="sky-summary__info">
                    <div class="sky-summary__planet-count">&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;</div>
                    <div class="sky-summary__info-item">&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;</div>
                    <div class="sky-summary__info-item">&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;</div>
                    <div class="sky-summary__info-item">&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;</div>
                </div>
            </div>
        `;
    }

    /**
     * Remove all content from the container.
     */
    clear() {
        this.container.innerHTML = '';
    }
}
