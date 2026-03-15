/**
 * main.js - Application entry point.
 *
 * Wires together LocationManager, SettingsModal, PlanetCards, SkySummary,
 * SkyMap, EventAlerts, and EventsTimeline.
 * Fetches planet visibility data on load, on location change, and every 5 minutes.
 * Fetches events lazily when the "Kommande" tab is first opened for a location.
 */

import { LocationManager } from './location-manager.js';
import { SettingsModal } from './components/settings-modal.js';
import { PlanetCards } from './components/planet-cards.js';
import { SkySummary } from './components/sky-summary.js';
import { TabNav } from './components/tab-nav.js';
import { SkyMap } from './components/sky-map.js';
import { EventAlerts } from './components/event-alerts.js';
import { EventsTimeline } from './components/events-timeline.js';
import { fetchVisiblePlanets, fetchEvents } from './api.js';
import { formatLocation } from './utils.js';

/** Auto-refresh interval in milliseconds. */
const REFRESH_INTERVAL_MS = 5 * 60 * 1000;

/**
 * Constellation line data loaded once at startup from data/constellations.json.
 * Null if the fetch failed or has not completed yet.
 *
 * @type {Object[]|null}
 */
let constellationData = null;

/**
 * Most recent successful API response. Retained so the constellation fetch
 * callback can immediately paint constellations when constellations.json
 * arrives after the planet data (resolving the parallel-fetch race condition).
 *
 * @type {Object|null}
 */
let lastApiData = null;

document.addEventListener('DOMContentLoaded', () => {
    // --- DOM references ---
    const planetCardsEl = document.getElementById('planetCards');
    const skySummaryEl = document.getElementById('skySummary');
    const settingsTriggerEl = document.getElementById('settingsTrigger');
    const locationDisplayEl = document.getElementById('locationDisplay');
    const lastUpdateEl = document.getElementById('lastUpdate');
    const errorBannerEl = document.getElementById('errorBanner');
    const errorMessageEl = document.getElementById('errorMessage');
    const errorDismissEl = document.getElementById('errorDismiss');

    // --- Component instantiation ---
    const locationManager = new LocationManager();

    // SettingsModal locates #settingsModalContainer itself via getElementById.
    const settingsModal = new SettingsModal(locationManager);

    const planetCards = new PlanetCards(planetCardsEl);
    const skySummary = new SkySummary(skySummaryEl);
    const tabNav = new TabNav();
    const skyMap = new SkyMap(document.getElementById('skyMapContainer'));
    const eventAlerts = new EventAlerts(document.getElementById('eventAlerts'));
    const eventsTimeline = new EventsTimeline(document.getElementById('eventsTimelineContainer'));

    // --- Interval tracking ---
    /** @type {number|null} */
    let refreshIntervalId = null;

    /** Most recently used location, kept in sync for the auto-refresh closure. */
    let currentLocation = null;

    /**
     * Whether events have been loaded for the current location.
     * Resets to false whenever the location changes so that switching back to
     * the "Kommande" tab after a location change triggers a fresh fetch.
     *
     * @type {boolean}
     */
    let eventsLoaded = false;

    // --- Helper: hide error banner ---
    function hideError() {
        errorBannerEl.classList.add('hidden');
    }

    // --- Helper: show error banner ---
    function showError(message) {
        errorMessageEl.textContent = message;
        errorBannerEl.classList.remove('hidden');
    }

    // --- Helper: start (or restart) the auto-refresh interval ---
    function startRefreshInterval() {
        if (refreshIntervalId !== null) {
            clearInterval(refreshIntervalId);
        }
        refreshIntervalId = setInterval(() => {
            // Mark the existing timestamp as stale before fetching.
            lastUpdateEl.dataset.stale = 'true';
            loadData(currentLocation);
        }, REFRESH_INTERVAL_MS);
    }

    /**
     * Fetch planet data for a location and update the UI.
     *
     * Errors are shown in the error banner and do not crash the app.
     *
     * @param {Object} location - Location object with lat and lon.
     */
    async function loadData(location) {
        hideError();
        planetCards.showLoading();
        skySummary.showLoading();

        try {
            const data = await fetchVisiblePlanets(location.lat, location.lon);

            lastApiData = data;

            skySummary.render(data);
            planetCards.render(data.planets);
            eventAlerts.render(data.events || []);
            skyMap.plotBodies(data.planets, data.sun, data.moon, data.events || []);

            if (constellationData !== null) {
                skyMap.plotConstellations(constellationData, location.lat, location.lon, new Date(data.timestamp));
            }

            const timeString = new Intl.DateTimeFormat('sv-SE', {
                hour: '2-digit',
                minute: '2-digit',
                second: '2-digit',
            }).format(new Date());
            lastUpdateEl.textContent = `Uppdaterad ${timeString}`;
            delete lastUpdateEl.dataset.stale;
            startRefreshInterval();
        } catch (error) {
            planetCards.clear();
            skySummary.clear();
            eventAlerts.clear();
            showError(error.message);
        }
    }

    /**
     * Fetch events for a location and render the timeline.
     *
     * Only called when the "Kommande" tab is activated and events have not
     * yet been loaded for the current location.
     *
     * @param {Object} location - Location object with lat and lon.
     */
    async function loadEvents(location) {
        eventsTimeline.showLoading();
        try {
            const data = await fetchEvents(location.lat, location.lon);
            eventsTimeline.render(data.events || []);
            eventsLoaded = true;
        } catch (err) {
            console.warn('Events: failed to load events', err);
            eventsTimeline.showEmpty();
        }
    }

    // --- Tab change listener ---
    // Handles both skymap rendering and events lazy loading.
    window.addEventListener('tabChanged', (event) => {
        const { tabId } = event.detail;

        if (tabId === 'skymap') {
            skyMap.render();
        }

        if (tabId === 'events' && !eventsLoaded) {
            loadEvents(currentLocation);
        }
    });

    // --- Settings trigger ---
    settingsTriggerEl.addEventListener('click', () => {
        settingsModal.open();
    });

    // --- Error dismiss ---
    errorDismissEl.addEventListener('click', hideError);

    // --- Location change listener ---
    // LocationManager dispatches 'locationChanged' on window with detail = location object.
    window.addEventListener('locationChanged', (event) => {
        currentLocation = event.detail;
        locationDisplayEl.textContent = formatLocation(currentLocation);
        // Reset events loaded flag so the timeline refreshes for the new location.
        eventsLoaded = false;
        loadData(currentLocation);
    });

    // --- Initial load ---
    currentLocation = locationManager.getCurrentLocation();
    locationDisplayEl.textContent = formatLocation(currentLocation);

    // Fetch constellation data and the initial planet data in parallel.
    // The constellation fetch is fire-and-forget: failures are logged and
    // the app continues normally without constellation lines.
    fetch('data/constellations.json')
        .then((response) => response.json())
        .then((parsed) => {
            constellationData = parsed;
            if (lastApiData !== null) {
                skyMap.plotConstellations(constellationData, currentLocation.lat, currentLocation.lon, new Date(lastApiData.timestamp));
            }
        })
        .catch((err) => {
            console.warn('Sky map: failed to load constellation data, running without constellation lines', err);
        });

    loadData(currentLocation);
});
