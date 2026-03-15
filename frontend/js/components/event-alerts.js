/**
 * event-alerts.js - Renders real-time astronomical event alert banners.
 *
 * Expects event objects matching the AstronomicalEvent schema from the backend.
 * Field names used: event_type, description_sv, date, days_away.
 */

// Map event_type values to display icons.
const EVENT_ICONS = {
    conjunction:  '\uD83D\uDD17', // 🔗
    opposition:   '\uD83D\uDD34', // 🔴
    mercury_elongation: '\u263F', // ☿
    alignment:    '\u2728',       // ✨
    venus_brilliancy: '\u2B50',   // ⭐
    occultation:  '\uD83C\uDF19', // 🌙
};

const DEFAULT_ICON = '\uD83C\uDF1F'; // 🌟

// Swedish month abbreviations for date formatting.
const MONTHS_SV = [
    'jan', 'feb', 'mar', 'apr', 'maj', 'jun',
    'jul', 'aug', 'sep', 'okt', 'nov', 'dec',
];

/**
 * Format an event date string to Swedish short form.
 *
 * Returns "idag" or "imorgon" based on days_away when applicable,
 * otherwise formats the date field as "D mon" (e.g. "15 mar").
 *
 * @param {string|null|undefined} dateStr - ISO date string (e.g. "2026-03-15").
 * @param {number|null|undefined} daysAway - Days until the event.
 * @returns {string}
 */
function formatEventDate(dateStr, daysAway) {
    if (daysAway === 0 || daysAway === null || daysAway === undefined) {
        return 'idag';
    }
    if (daysAway === 1) {
        return 'imorgon';
    }
    if (dateStr) {
        // Parse YYYY-MM-DD without timezone conversion.
        const parts = dateStr.split('-');
        const day = parseInt(parts[2], 10);
        const monthIndex = parseInt(parts[1], 10) - 1;
        return `${day}\u00a0${MONTHS_SV[monthIndex]}`;
    }
    return '';
}

/**
 * Build the DOM element for one event alert banner card.
 *
 * @param {Object} event - AstronomicalEvent object from the API.
 * @returns {HTMLElement}
 */
function buildAlertCard(event) {
    const daysAway = event.days_away;
    const isActive = daysAway === 0 || daysAway === null || daysAway === undefined;

    const card = document.createElement('div');
    card.className = isActive
        ? 'event-alert event-alert--active'
        : 'event-alert event-alert--upcoming';

    const iconEl = document.createElement('span');
    iconEl.className = 'event-alert__icon';
    iconEl.textContent = EVENT_ICONS[event.event_type] ?? DEFAULT_ICON;
    iconEl.setAttribute('aria-hidden', 'true');

    const descriptionEl = document.createElement('span');
    descriptionEl.className = 'event-alert__description';
    descriptionEl.textContent = event.description_sv ?? '';

    const dateEl = document.createElement('span');
    dateEl.className = 'event-alert__date';
    dateEl.textContent = formatEventDate(event.date, daysAway);

    card.appendChild(iconEl);
    card.appendChild(descriptionEl);
    card.appendChild(dateEl);

    return card;
}

/**
 * Build a skeleton placeholder card for the loading state.
 *
 * @returns {HTMLElement}
 */
function buildSkeletonCard() {
    const card = document.createElement('div');
    card.className = 'event-alert event-alert--skeleton';

    const iconEl = document.createElement('span');
    iconEl.className = 'event-alert__icon';
    iconEl.textContent = '\u00a0';

    const descriptionEl = document.createElement('span');
    descriptionEl.className = 'event-alert__description';
    descriptionEl.textContent = '\u00a0';

    const dateEl = document.createElement('span');
    dateEl.className = 'event-alert__date';
    dateEl.textContent = '\u00a0';

    card.appendChild(iconEl);
    card.appendChild(descriptionEl);
    card.appendChild(dateEl);

    return card;
}

/**
 * EventAlerts renders a list of astronomical event alert banners.
 *
 * Usage:
 *   const alerts = new EventAlerts(document.getElementById('eventAlerts'));
 *   alerts.showLoading();
 *   alerts.render(data.events);
 */
export class EventAlerts {
    /**
     * @param {HTMLElement} containerEl - The element that will hold the alert banners.
     */
    constructor(containerEl) {
        this.container = containerEl;
    }

    /**
     * Render event alert banners from an array of AstronomicalEvent API objects.
     *
     * Hides the container when events is empty or null. Otherwise clears any
     * existing content and appends one banner card per event.
     *
     * @param {Object[]|null|undefined} events - Array of event objects from the API.
     */
    render(events) {
        if (!events || events.length === 0) {
            this.container.classList.add('hidden');
            return;
        }

        this.container.classList.remove('hidden');
        this.container.innerHTML = '';

        for (const event of events) {
            this.container.appendChild(buildAlertCard(event));
        }
    }

    /**
     * Show skeleton placeholder banners while data is loading.
     *
     * Displays two skeleton cards as a loading hint.
     */
    showLoading() {
        this.container.classList.remove('hidden');
        this.container.innerHTML = '';
        this.container.appendChild(buildSkeletonCard());
        this.container.appendChild(buildSkeletonCard());
    }

    /**
     * Remove all alert banners and hide the container.
     */
    clear() {
        this.container.innerHTML = '';
        this.container.classList.add('hidden');
    }
}
