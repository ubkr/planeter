/**
 * event-alerts.js - Renders real-time astronomical event alert banners.
 *
 * Expects event objects matching the AstronomicalEvent schema from the backend.
 * Field names used: event_type, description_sv, date, days_away,
 *   best_time_start, best_time_end, altitude_deg, compass_direction_sv,
 *   observation_tip_sv.
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
    if (daysAway === 0) {
        return 'idag';
    }
    if (daysAway === 1) {
        return 'imorgon';
    }
    if (dateStr) {
        // Take only the first 10 characters ("YYYY-MM-DD") before splitting, so
        // that full ISO timestamps ("YYYY-MM-DDTHH:MM:SSZ") are handled correctly.
        const parts = dateStr.slice(0, 10).split('-');
        const day = parseInt(parts[2], 10);
        const monthIndex = parseInt(parts[1], 10) - 1;
        return `${day}\u00a0${MONTHS_SV[monthIndex]}`;
    }
    return '';
}

/**
 * Format a UTC ISO 8601 string to HH:MM in Europe/Stockholm timezone.
 *
 * @param {string} isoStr - UTC ISO string (e.g. "2026-03-15T21:30:00Z").
 * @returns {string} Time string like "22:30".
 */
function formatTimeStockholm(isoStr) {
    return new Intl.DateTimeFormat('sv-SE', {
        timeZone: 'Europe/Stockholm',
        hour: '2-digit',
        minute: '2-digit',
        hour12: false,
    }).format(new Date(isoStr));
}

/**
 * Return true if the event carries any observation guidance fields.
 *
 * @param {Object} event - AstronomicalEvent object from the API.
 * @returns {boolean}
 */
function hasGuidance(event) {
    return (
        event.observation_tip_sv != null ||
        event.altitude_deg != null ||
        event.compass_direction_sv != null
    );
}

/**
 * Build the detail panel element containing observation guidance.
 *
 * @param {Object} event - AstronomicalEvent object from the API.
 * @returns {HTMLElement}
 */
function buildDetailPanel(event) {
    const panel = document.createElement('div');
    panel.className = 'event-alert__detail';

    if (event.best_time_start != null && event.best_time_end != null) {
        const timeStart = formatTimeStockholm(event.best_time_start);
        const timeEnd = formatTimeStockholm(event.best_time_end);
        const timeP = document.createElement('p');
        timeP.className = 'event-alert__detail-line';
        timeP.textContent = `B\u00e4sta tid: ${timeStart}\u2013${timeEnd}`;
        panel.appendChild(timeP);
    }

    if (event.compass_direction_sv != null && event.altitude_deg != null) {
        const dirP = document.createElement('p');
        dirP.className = 'event-alert__detail-line';
        const altRounded = Math.round(event.altitude_deg);
        dirP.textContent = `Riktning: ${event.compass_direction_sv}, h\u00f6jd: ${altRounded}\u00b0`;
        panel.appendChild(dirP);
    }

    if (event.observation_tip_sv != null) {
        const tipP = document.createElement('p');
        tipP.className = 'event-alert__detail-tip';
        tipP.textContent = event.observation_tip_sv;
        panel.appendChild(tipP);
    }

    return panel;
}

/**
 * Toggle the expanded state of a card's detail panel.
 *
 * Reads aria-expanded at call time so rapid clicks remain idempotent.
 *
 * @param {HTMLElement} card - The card root element.
 * @param {HTMLElement} panel - The detail panel element.
 * @param {HTMLElement} chevron - The chevron span element.
 */
function toggleCardExpanded(card, panel, chevron) {
    const isExpanded = card.getAttribute('aria-expanded') === 'true';
    if (isExpanded) {
        card.setAttribute('aria-expanded', 'false');
        panel.classList.remove('event-alert__detail--expanded');
        chevron.classList.remove('event-alert__chevron--expanded');
    } else {
        card.setAttribute('aria-expanded', 'true');
        panel.classList.add('event-alert__detail--expanded');
        chevron.classList.add('event-alert__chevron--expanded');
    }
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

    if (hasGuidance(event)) {
        card.classList.add('event-alert--expandable');
        card.setAttribute('role', 'button');
        card.setAttribute('tabindex', '0');
        card.setAttribute('aria-expanded', 'false');

        const chevron = document.createElement('span');
        chevron.className = 'event-alert__chevron';
        chevron.setAttribute('aria-hidden', 'true');
        chevron.textContent = '\u25be'; // ▾
        card.appendChild(chevron);

        const panel = buildDetailPanel(event);
        card.appendChild(panel);

        card.addEventListener('click', function () {
            toggleCardExpanded(card, panel, chevron);
        });

        card.addEventListener('keydown', function (e) {
            if (e.key === 'Enter' || e.key === ' ') {
                if (e.key === ' ') {
                    // Prevent page scroll on Space.
                    e.preventDefault();
                }
                toggleCardExpanded(card, panel, chevron);
            }
        });
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
