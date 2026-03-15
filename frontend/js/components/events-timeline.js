/**
 * events-timeline.js - Renders a chronological timeline of upcoming astronomical events.
 *
 * Expects event objects matching the AstronomicalEvent schema from the backend.
 * Field names used: event_type, description_sv, date, days_away.
 */

// Number of skeleton rows to show while loading.
const SKELETON_COUNT = 5;

const MONTH_NAMES_SV = [
    'januari', 'februari', 'mars', 'april', 'maj', 'juni',
    'juli', 'augusti', 'september', 'oktober', 'november', 'december',
];

const WEEKDAY_ABBR_SV = ['sön', 'mån', 'tis', 'ons', 'tor', 'fre', 'lör'];

const EVENT_TYPE_ICONS = {
    conjunction: '🔗',
    opposition:  '🔴',
    mercury_elongation: '☿',
    alignment:   '✨',
    venus_brilliancy: '⭐',
    occultation: '🌙',
};

/**
 * Return the emoji icon for a given event type string.
 *
 * @param {string} eventType
 * @returns {string}
 */
function iconForEventType(eventType) {
    return EVENT_TYPE_ICONS[eventType] ?? '🌟';
}

/**
 * Parse an event_date string into a UTC Date object.
 *
 * If dateStr is already a full ISO timestamp (contains "T"), use it directly.
 * If dateStr is a bare "YYYY-MM-DD" string, append T12:00:00Z so that noon UTC
 * is used, avoiding date-boundary issues from timezone offsets.
 *
 * @param {string} dateStr - "YYYY-MM-DD" or full ISO 8601 timestamp
 * @returns {Date}
 */
function parseDateStr(dateStr) {
    if (dateStr.includes('T')) {
        return new Date(dateStr);
    }
    return new Date(`${dateStr}T12:00:00Z`);
}

/**
 * Return a "YYYY-MM" key for grouping events by calendar month.
 *
 * @param {string} dateStr - "YYYY-MM-DD"
 * @returns {string} e.g. "2026-03"
 */
function monthKey(dateStr) {
    return dateStr.slice(0, 7);
}

/**
 * Format a "YYYY-MM" key into a Swedish month+year heading string.
 *
 * @param {string} key - "YYYY-MM"
 * @returns {string} e.g. "mars 2026"
 */
function formatMonthHeading(key) {
    const [year, month] = key.split('-');
    return `${MONTH_NAMES_SV[parseInt(month, 10) - 1]} ${year}`;
}

/**
 * Build the DOM element for the days-away badge.
 *
 * @param {number} daysAway
 * @returns {HTMLElement}
 */
function buildDaysBadge(daysAway) {
    const badge = document.createElement('span');
    badge.className = 'events-timeline__days-badge';

    if (daysAway === 0) {
        badge.textContent = 'idag';
        badge.classList.add('events-timeline__days-badge--today');
    } else if (daysAway === 1) {
        badge.textContent = 'imorgon';
        badge.classList.add('events-timeline__days-badge--soon');
    } else if (daysAway <= 7) {
        badge.textContent = `om ${daysAway} dagar`;
        badge.classList.add('events-timeline__days-badge--soon');
    } else {
        badge.textContent = `om ${daysAway} dagar`;
    }

    return badge;
}

/**
 * Build the DOM element for one event row.
 *
 * @param {Object} event - AstronomicalEvent object from the API.
 * @returns {HTMLElement}
 */
function buildEventRow(event) {
    const date = parseDateStr(event.date);
    const dayNum = date.getUTCDate();
    const weekdayAbbr = WEEKDAY_ABBR_SV[date.getUTCDay()];

    const row = document.createElement('div');
    row.className = 'events-timeline__event';

    const dateEl = document.createElement('span');
    dateEl.className = 'events-timeline__date';
    dateEl.textContent = `${dayNum} ${weekdayAbbr}`;

    const iconEl = document.createElement('span');
    iconEl.className = 'events-timeline__icon';
    iconEl.textContent = iconForEventType(event.event_type);
    // Prevent emoji from being announced verbatim by screen readers.
    iconEl.setAttribute('aria-hidden', 'true');

    const descEl = document.createElement('span');
    descEl.className = 'events-timeline__description';
    descEl.textContent = event.description_sv;

    const badge = buildDaysBadge(event.days_away);

    row.appendChild(dateEl);
    row.appendChild(iconEl);
    row.appendChild(descEl);
    row.appendChild(badge);

    return row;
}

/**
 * Build a month header element.
 *
 * @param {string} key - "YYYY-MM" month key.
 * @returns {HTMLElement}
 */
function buildMonthHeader(key) {
    const header = document.createElement('div');
    header.className = 'events-timeline__month-header';
    header.textContent = formatMonthHeading(key);
    return header;
}

/**
 * Build a skeleton placeholder row for the loading state.
 *
 * @returns {HTMLElement}
 */
function buildSkeletonRow() {
    const row = document.createElement('div');
    row.className = 'events-timeline__event events-timeline__event--skeleton';

    const dateEl = document.createElement('span');
    dateEl.className = 'events-timeline__date events-timeline__skeleton-block';
    dateEl.innerHTML = '&nbsp;';

    const iconEl = document.createElement('span');
    iconEl.className = 'events-timeline__icon events-timeline__skeleton-block';
    iconEl.innerHTML = '&nbsp;';

    const descEl = document.createElement('span');
    descEl.className = 'events-timeline__description events-timeline__skeleton-block';
    descEl.innerHTML = '&nbsp;';

    const badge = document.createElement('span');
    badge.className = 'events-timeline__days-badge events-timeline__skeleton-block';
    badge.innerHTML = '&nbsp;';

    row.appendChild(dateEl);
    row.appendChild(iconEl);
    row.appendChild(descEl);
    row.appendChild(badge);

    return row;
}

/**
 * EventsTimeline renders a month-grouped list of upcoming astronomical events.
 *
 * Usage:
 *   const timeline = new EventsTimeline(document.getElementById('eventsTimeline'));
 *   timeline.showLoading();
 *   timeline.render(data.events);
 */
export class EventsTimeline {
    /**
     * @param {HTMLElement} containerEl - The element that will hold the timeline.
     */
    constructor(containerEl) {
        this.container = containerEl;

        // Create and append the inner list wrapper once.
        this.list = document.createElement('div');
        this.list.className = 'events-timeline';
        this.container.appendChild(this.list);
    }

    /**
     * Render a sorted array of AstronomicalEvent objects grouped by calendar month.
     *
     * If the array is empty, falls back to showEmpty().
     *
     * @param {Object[]} events - Sorted array of AstronomicalEvent objects from the API.
     */
    render(events) {
        this.list.innerHTML = '';

        if (!events || events.length === 0) {
            this.showEmpty();
            return;
        }

        // Group events by "YYYY-MM" key while preserving the sorted order.
        const groups = new Map();
        for (const event of events) {
            const key = monthKey(event.date);
            if (!groups.has(key)) {
                groups.set(key, []);
            }
            groups.get(key).push(event);
        }

        for (const [key, groupEvents] of groups) {
            this.list.appendChild(buildMonthHeader(key));
            for (const event of groupEvents) {
                this.list.appendChild(buildEventRow(event));
            }
        }
    }

    /**
     * Show skeleton placeholder rows while data is loading.
     */
    showLoading() {
        this.list.innerHTML = '';
        for (let i = 0; i < SKELETON_COUNT; i++) {
            this.list.appendChild(buildSkeletonRow());
        }
    }

    /**
     * Show a friendly message when no events are available.
     */
    showEmpty() {
        this.list.innerHTML = '';
        const msg = document.createElement('p');
        msg.className = 'events-timeline__empty';
        msg.textContent = 'Inga speciella h\u00e4ndelser de n\u00e4rmaste 60 dagarna \uD83C\uDF19';
        this.list.appendChild(msg);
    }

    /**
     * Remove all content from the timeline.
     */
    clear() {
        this.list.innerHTML = '';
    }
}
