/**
 * sky-summary.js - Renders the sky summary banner for the current observation window.
 *
 * Expects the full PlanetsResponse object from GET /api/v1/planets/visible.
 * Relevant top-level fields: planets, sun, moon, weather, location, tonight_score, timestamp.
 */

import { scoreToLevel, formatLocation, formatTime } from '../utils.js';

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
 * Build the sun rise/set time strings based on whether today's events have passed.
 *
 * - Sunrise: if today's rise is still in the future (or null), show today's value.
 *   If it has passed, show next rise with "nästa" prefix.
 * - Sunset: if today's set is still in the future (or null), show today's value.
 *   If it has passed, show next set (no "nästa" prefix).
 *
 * @param {Object} sun - Sun object from API response.
 * @param {string} timestamp - Response "now" timestamp (UTC ISO 8601).
 * @returns {{ riseText: string, setText: string }}
 */
function buildSunTimeParts(sun, timestamp) {
    const now = new Date(timestamp);

    const todayRise = sun.today_rise_time ? new Date(sun.today_rise_time) : null;
    const todaySet  = sun.today_set_time  ? new Date(sun.today_set_time)  : null;

    let riseText;
    if (todayRise === null || todayRise > now) {
        riseText = formatTime(sun.today_rise_time);
    } else {
        riseText = `<span class="next-prefix">n\u00e4sta</span> ${formatTime(sun.next_rise_time)}`;
    }

    let setTextValue;
    if (todaySet === null || todaySet > now) {
        setTextValue = formatTime(sun.today_set_time);
    } else {
        setTextValue = formatTime(sun.next_set_time);
    }

    return { riseText, setText: setTextValue };
}

/**
 * Build the moon rise/set time strings based on whether today's events have passed.
 *
 * - If both today's rise and set are still in the future, use today's values, no prefix.
 * - If today's moonrise has passed, show next rise with "nästa" prefix.
 * - If today's moonset has passed, show next set (no "nästa" prefix).
 *
 * @param {Object} moon - Moon object from API response.
 * @param {string} timestamp - Response "now" timestamp (UTC ISO 8601).
 * @returns {{ riseText: string, setText: string }}
 */
function buildMoonTimeParts(moon, timestamp) {
    const now = new Date(timestamp);

    const todayRise = moon.today_rise_time ? new Date(moon.today_rise_time) : null;
    const todaySet  = moon.today_set_time  ? new Date(moon.today_set_time)  : null;

    const riseInFuture = todayRise !== null && todayRise > now;
    const setInFuture  = todaySet  !== null && todaySet  > now;

    // Use today's rise if it is still in the future; otherwise point to next rise.
    const riseText = riseInFuture
        ? formatTime(moon.today_rise_time)
        : `<span class="next-prefix">n\u00e4sta</span> ${formatTime(moon.next_rise_time)}`;

    // Use today's set if it is still in the future; otherwise point to next set.
    const setTextValue = setInFuture
        ? formatTime(moon.today_set_time)
        : formatTime(moon.next_set_time);

    return { riseText, setText: setTextValue };
}

/**
 * Build the HTML string for the sun/moon times block.
 *
 * Returns an empty string if neither sun nor moon data is present.
 *
 * @param {Object|null|undefined} sun - Sun object from API response.
 * @param {Object|null|undefined} moon - Moon object from API response.
 * @param {string} timestamp - Response "now" timestamp (UTC ISO 8601).
 * @returns {string} HTML string for `.sky-summary__times`, or "".
 */
function buildTimesHTML(sun, moon, timestamp) {
    if (!sun && !moon) return '';

    let sunBlockHTML = '';
    if (sun) {
        const { riseText, setText } = buildSunTimeParts(sun, timestamp);
        sunBlockHTML = `
            <div class="sky-summary__sun-block">
                <div class="sky-summary__times-heading">\u2600\ufe0f Solen</div>
                <div class="sky-summary__time-row">Upp: ${riseText}</div>
                <div class="sky-summary__time-row">Ned: ${setText}</div>
            </div>`;
    }

    let moonBlockHTML = '';
    if (moon) {
        const { riseText, setText } = buildMoonTimeParts(moon, timestamp);
        moonBlockHTML = `
            <div class="sky-summary__moon-block">
                <div class="sky-summary__times-heading">\ud83c\udf19 M\u00e5nen</div>
                <div class="sky-summary__time-row">Upp: ${riseText}</div>
                <div class="sky-summary__time-row">Ned: ${setText}</div>
            </div>`;
    }

    return `
        <div class="sky-summary__times">
            ${sunBlockHTML}
            ${moonBlockHTML}
        </div>`;
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
     * @param {Object} [data.moon]
     * @param {Object} data.weather
     * @param {Object} data.location
     * @param {number} [data.tonight_score] - Optional pre-computed overall score.
     * @param {string} [data.timestamp] - UTC ISO 8601 "now" timestamp.
     */
    render(data) {
        const { planets, sun, moon, weather, location } = data;
        const timestamp = data.timestamp ?? new Date().toISOString();

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

        const timesHTML = buildTimesHTML(sun ?? null, moon ?? null, timestamp);

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
                ${timesHTML}
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
                <div class="sky-summary__times sky-summary__times--skeleton">
                    <div class="sky-summary__sun-block">
                        <div class="sky-summary__times-heading">&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;</div>
                        <div class="sky-summary__time-row">&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;</div>
                        <div class="sky-summary__time-row">&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;</div>
                    </div>
                    <div class="sky-summary__moon-block">
                        <div class="sky-summary__times-heading">&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;</div>
                        <div class="sky-summary__time-row">&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;</div>
                        <div class="sky-summary__time-row">&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;</div>
                    </div>
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
