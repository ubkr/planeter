/**
 * main.js - Application entry point.
 *
 * Wires together LocationManager, SettingsModal, PlanetCards, and SkySummary.
 * Fetches planet visibility data on load, on location change, and every 5 minutes.
 */

import { LocationManager } from './location-manager.js';
import { SettingsModal } from './components/settings-modal.js';
import { PlanetCards } from './components/planet-cards.js';
import { SkySummary } from './components/sky-summary.js';
import { TabNav } from './components/tab-nav.js';
import { SkyMap } from './components/sky-map.js';
import { fetchVisiblePlanets } from './api.js';
import { formatLocation } from './utils.js';

/** Auto-refresh interval in milliseconds. */
const REFRESH_INTERVAL_MS = 5 * 60 * 1000;

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

    // --- SkyMap tab-switch listener ---
    window.addEventListener('tabChanged', (event) => {
        if (event.detail.tabId === 'skymap') {
            skyMap.render();
        }
    });

    // --- Interval tracking ---
    /** @type {number|null} */
    let refreshIntervalId = null;

    /** Most recently used location, kept in sync for the auto-refresh closure. */
    let currentLocation = null;

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

            skySummary.render(data);
            planetCards.render(data.planets);

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
            showError(error.message);
        }
    }

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
        loadData(currentLocation);
    });

    // --- Initial load ---
    currentLocation = locationManager.getCurrentLocation();
    locationDisplayEl.textContent = formatLocation(currentLocation);
    loadData(currentLocation);
});
