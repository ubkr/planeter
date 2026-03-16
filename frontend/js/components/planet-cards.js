/**
 * planet-cards.js - Renders planet visibility cards into a container element.
 *
 * Expects planet objects matching the PlanetsResponse schema from the backend.
 * Field names used: name, name_sv, visibility_score, is_visible, is_above_horizon,
 * altitude_deg, azimuth_deg, direction, magnitude, constellation, rise_time, transit_time, set_time.
 */

import { scoreToLevel, formatVisibilityReasons, getEquipmentRecommendation } from '../utils.js';
import PLANET_DESCRIPTIONS from '../data/planet-descriptions.js';

// Number of skeleton cards to show while loading.
const PLANET_COUNT = 5;

/**
 * Format an ISO 8601 UTC timestamp to HH:MM in Europe/Stockholm local time.
 *
 * @param {string|null|undefined} isoString - UTC ISO string, e.g. "2026-02-28T22:00:00Z".
 * @returns {string} "HH:MM" or "--" if isoString is absent.
 */
function formatTime(isoString) {
    if (!isoString) return '--';
    return new Intl.DateTimeFormat('sv-SE', {
        timeZone: 'Europe/Stockholm',
        hour: '2-digit',
        minute: '2-digit',
    }).format(new Date(isoString));
}

/**
 * Format an altitude in degrees to one decimal place with degree symbol.
 *
 * @param {number} deg - Altitude in degrees.
 * @returns {string} e.g. "25.3°"
 */
function formatAltitude(deg) {
    return `${deg.toFixed(1)}°`;
}

/**
 * Format an apparent magnitude to one decimal place with sign prefix.
 *
 * Negative magnitudes (brighter) are prefixed with "−"; positive with "+".
 *
 * @param {number} mag - Apparent magnitude.
 * @returns {string} e.g. "-4.2" → "−4.2", "1.0" → "+1.0"
 */
function formatMagnitude(mag) {
    const fixed = Math.abs(mag).toFixed(1);
    return mag >= 0 ? `+${fixed}` : `\u2212${fixed}`;
}

/**
 * Build the DOM element for one planet card.
 *
 * @param {Object} planet - Planet data object from the API.
 * @returns {HTMLElement}
 */
function buildCard(planet) {
    const score = planet.visibility_score ?? 0;
    const level = scoreToLevel(score);
    const isAbove = planet.is_above_horizon ?? false;
    const isVisible = planet.is_visible ?? false;

    const isCompact = !isVisible;

    const card = document.createElement('div');
    card.className = 'planet-card';
    card.dataset.planet = planet.name.toLowerCase();

    if (!isAbove) {
        card.classList.add('planet-card--below-horizon');
    } else if (!isVisible) {
        card.classList.add('planet-card--not-visible');
    }

    if (isCompact) {
        card.classList.add('planet-card--compact');
    }

    card.innerHTML = `
        <div class="planet-card__header">
            <div class="planet-card__name">${planet.name_sv ?? planet.name}</div>
            <div class="planet-card__score" data-score-level="${level}">${score}</div>
        </div>
        ${!isCompact ? `
        <div class="planet-card__score-bar"
             data-score-level="${level}"
             style="--score-percent: ${score}%"></div>
        <div class="planet-card__details">
            <span class="planet-card__detail-label">H\u00f6jd</span>
            <span class="planet-card__detail-value">${formatAltitude(planet.altitude_deg)}</span>
            <span class="planet-card__detail-label">Riktning</span>
            <span class="planet-card__detail-value">${planet.direction} (${Math.round(planet.azimuth_deg)}\u00b0)</span>
            <span class="planet-card__detail-label">Magnitud</span>
            <span class="planet-card__detail-value">${formatMagnitude(planet.magnitude)}</span>
            <span class="planet-card__detail-label">Stj\u00e4rnbild</span>
            <span class="planet-card__detail-value">${planet.constellation}</span>
        </div>
        <div class="planet-card__times">
            <span>
                <span class="planet-card__time-label">Uppg\u00e5ng</span>
                <span class="planet-card__time-value">${formatTime(planet.rise_time)}</span>
            </span>
            <span>
                <span class="planet-card__time-label">Transit</span>
                <span class="planet-card__time-value">${formatTime(planet.transit_time)}</span>
            </span>
            <span>
                <span class="planet-card__time-label">Nedg\u00e5ng</span>
                <span class="planet-card__time-value">${formatTime(planet.set_time)}</span>
            </span>
        </div>
        ` : ''}
    `;

    // Build the best-observation-time row imperatively so that formatTime() is
    // called at runtime rather than inlined into the template string above.
    // This keeps the logic readable and avoids a deeply nested ternary in HTML.
    const bestTimeEl = document.createElement('div');
    if (planet.dark_rise_time != null && planet.dark_set_time != null) {
        bestTimeEl.className = 'planet-card__best-time';

        const labelEl = document.createElement('span');
        labelEl.className = 'planet-card__best-time-label';
        labelEl.textContent = 'B\u00e4sta tid:';

        const windowEl = document.createElement('span');
        windowEl.className = 'planet-card__best-time-window';
        windowEl.textContent = `${formatTime(planet.dark_rise_time)}\u2013${formatTime(planet.dark_set_time)}`;

        bestTimeEl.appendChild(labelEl);
        bestTimeEl.appendChild(windowEl);

        if (planet.best_time != null) {
            const peakEl = document.createElement('span');
            peakEl.className = 'planet-card__best-time-peak';
            peakEl.textContent = `(topp ${formatTime(planet.best_time)})`;
            bestTimeEl.appendChild(peakEl);
        }
    } else {
        bestTimeEl.className = 'planet-card__best-time planet-card__best-time--none';
        bestTimeEl.textContent = 'Ej synlig ikv\u00e4ll';
    }
    card.appendChild(bestTimeEl);

    // Build the visibility pill imperatively to avoid XSS via attribute injection.
    // TooltipManager watches for .info-icon and reads the `title` property.
    //
    // "goda_förhållanden" is excluded from the tooltip-trigger decision: a planet
    // with no active penalties is clearly good, so the dashed-underline affordance
    // would be confusing rather than informative. The backend still reports the
    // reason for API consumers; we just don't surface it as a tooltip in the UI.
    const actionableReasons = (planet.visibility_reasons ?? []).filter(
        (r) => r !== 'goda_förhållanden'
    );
    const tooltipText = formatVisibilityReasons(actionableReasons);

    const visibilityEl = document.createElement('div');
    visibilityEl.className = tooltipText
        ? 'planet-card__visibility info-icon'
        : 'planet-card__visibility';
    visibilityEl.dataset.visible = isVisible;
    if (isVisible) {
        visibilityEl.textContent = 'Synlig';
    } else if (!isAbove) {
        visibilityEl.textContent = 'Under horisonten';
    } else {
        visibilityEl.textContent = 'Ej synlig';
    }
    if (tooltipText) {
        visibilityEl.tabIndex = 0;
        visibilityEl.title = tooltipText;
    }
    card.appendChild(visibilityEl);

    // Build the equipment recommendation badge if an equipment level applies.
    // Hidden in compact mode (non-visible planets).
    if (!isCompact) {
        const EQUIPMENT_LABELS = {
            naked_eye:  'Blotta ögat',
            binoculars: 'Kikare rekommenderas',
            telescope:  'Teleskop',
        };
        const equipment = getEquipmentRecommendation(planet);
        if (equipment !== null) {
            const equipmentEl = document.createElement('div');
            equipmentEl.className = 'planet-card__equipment';
            equipmentEl.textContent = EQUIPMENT_LABELS[equipment];
            card.appendChild(equipmentEl);
        }
    }

    // Build the collapsible "Vad ska man leta efter?" description section.
    // Skip entirely if no description data exists for this planet name, or in compact mode.
    const desc = !isCompact ? PLANET_DESCRIPTIONS[planet.name] : null;
    if (desc) {
        const toggleEl = document.createElement('button');
        toggleEl.className = 'planet-card__description-toggle';
        toggleEl.setAttribute('aria-expanded', 'false');

        const toggleTextNode = document.createTextNode('Vad ska man leta efter?\u00a0');
        const chevronEl = document.createElement('span');
        chevronEl.className = 'planet-card__description-chevron';
        chevronEl.textContent = '\u25b8';

        toggleEl.appendChild(toggleTextNode);
        toggleEl.appendChild(chevronEl);

        const contentEl = document.createElement('div');
        contentEl.className = 'planet-card__description';
        contentEl.setAttribute('aria-hidden', 'true');

        const colorEl = document.createElement('span');
        colorEl.className = 'planet-card__description-color';
        colorEl.textContent = desc.color_sv;

        const appearanceEl = document.createElement('p');
        appearanceEl.className = 'planet-card__description-text';
        appearanceEl.textContent = desc.appearance_sv;

        const tipEl = document.createElement('p');
        tipEl.className = 'planet-card__description-text';
        tipEl.textContent = desc.identification_tip_sv;

        contentEl.appendChild(colorEl);
        contentEl.appendChild(appearanceEl);
        contentEl.appendChild(tipEl);

        toggleEl.addEventListener('click', () => {
            if (!toggleEl.isConnected) return;
            const expanded = toggleEl.getAttribute('aria-expanded') === 'true';
            const nowExpanded = !expanded;
            toggleEl.setAttribute('aria-expanded', String(nowExpanded));
            contentEl.setAttribute('aria-hidden', String(!nowExpanded));
            contentEl.classList.toggle('planet-card__description--expanded', nowExpanded);
            chevronEl.textContent = nowExpanded ? '\u25be' : '\u25b8';
        });

        card.appendChild(toggleEl);
        card.appendChild(contentEl);
    }

    return card;
}

/**
 * Build a skeleton placeholder card for the loading state.
 *
 * @returns {HTMLElement}
 */
function buildSkeletonCard() {
    const card = document.createElement('div');
    card.className = 'planet-card planet-card--skeleton';
    card.innerHTML = `
        <div class="planet-card__header">
            <div class="planet-card__name">&nbsp;</div>
            <div class="planet-card__score">&nbsp;</div>
        </div>
        <div class="planet-card__score-bar"></div>
        <div class="planet-card__details">
            <span class="planet-card__detail-label">&nbsp;</span>
            <span class="planet-card__detail-value">&nbsp;</span>
            <span class="planet-card__detail-label">&nbsp;</span>
            <span class="planet-card__detail-value">&nbsp;</span>
            <span class="planet-card__detail-label">&nbsp;</span>
            <span class="planet-card__detail-value">&nbsp;</span>
            <span class="planet-card__detail-label">&nbsp;</span>
            <span class="planet-card__detail-value">&nbsp;</span>
        </div>
        <div class="planet-card__times">&nbsp;</div>
        <div class="planet-card__best-time planet-card__best-time--skeleton">&nbsp;</div>
        <div class="planet-card__visibility">&nbsp;</div>
        <div class="planet-card__equipment">&nbsp;</div>
    `;
    return card;
}

/**
 * PlanetCards renders a grid of planet visibility cards.
 *
 * Usage:
 *   const cards = new PlanetCards(document.getElementById('planetCards'));
 *   cards.showLoading();
 *   cards.render(data.planets);
 */
export class PlanetCards {
    /**
     * @param {HTMLElement} containerEl - The element that will hold the card grid.
     */
    constructor(containerEl) {
        this.container = containerEl;

        // Create and append the inner grid wrapper once.
        this.grid = document.createElement('div');
        this.grid.className = 'planet-cards-grid';
        this.container.appendChild(this.grid);
    }

    /**
     * Render planet cards from an array of planet API objects.
     *
     * Visible planets (is_above_horizon true) are sorted by visibility_score
     * descending and shown first; below-horizon planets follow, also sorted
     * by visibility_score descending.
     *
     * @param {Object[]} planets - Array of planet objects from the API.
     */
    render(planets) {
        this.grid.innerHTML = '';

        const aboveHorizon = planets
            .filter(p => p.is_above_horizon)
            .sort((a, b) => b.visibility_score - a.visibility_score);

        const belowHorizon = planets
            .filter(p => !p.is_above_horizon)
            .sort((a, b) => b.visibility_score - a.visibility_score);

        for (const planet of [...aboveHorizon, ...belowHorizon]) {
            this.grid.appendChild(buildCard(planet));
        }
    }

    /**
     * Show skeleton placeholder cards while data is loading.
     */
    showLoading() {
        this.grid.innerHTML = '';
        for (let i = 0; i < PLANET_COUNT; i++) {
            this.grid.appendChild(buildSkeletonCard());
        }
    }

    /**
     * Remove all cards from the container.
     */
    clear() {
        this.grid.innerHTML = '';
    }
}
