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

/** localStorage key for the user's preferred sky-map view mode. */
const VIEW_MODE_KEY = 'planet_view_mode';

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

    // --- 3D sky map state ---

    /**
     * Cached SkyMap3D instance — created once on first activation.
     * @type {import('./components/sky-map-3d.js').default|null}
     */
    let skyMap3d = null;

    /**
     * True when the stored preference is '3d' but the skymap tab has not yet
     * become visible.  Activation is deferred so that the WebGL renderer
     * receives non-zero container dimensions.  Consumed (set to false) by the
     * tabChanged handler the first time the skymap tab is shown.
     *
     * @type {boolean}
     */
    let pendingView3d = (localStorage.getItem(VIEW_MODE_KEY) || '2d') === '3d';

    /** DOM elements for the 2D/3D toggle. */
    const skyMap3dContainerEl = document.getElementById('skyMap3dContainer');
    const toggleBtns = Array.from(document.querySelectorAll('.skymap-view-toggle__btn'));
    const errorEl = skyMap3dContainerEl
        ? skyMap3dContainerEl.querySelector('.skymap-3d-error')
        : null;

    /**
     * Show the in-container 3D error message and switch back to 2D.
     *
     * @param {string} message - Swedish-language error text.
     */
    function show3dError(message) {
        if (errorEl) {
            errorEl.textContent = message;
            errorEl.removeAttribute('hidden');
        }
        activateView('2d');
    }

    /**
     * Apply all DOM mutations needed to switch between 2D and 3D views.
     * Does NOT start/stop the render loop — callers do that around this.
     *
     * @param {'2d'|'3d'} mode
     */
    function applyViewMode(mode) {
        const skyMapContainerEl = document.getElementById('skyMapContainer');
        const is3d = mode === '3d';

        // Container visibility
        if (skyMapContainerEl) {
            skyMapContainerEl.style.display = is3d ? 'none' : '';
        }
        if (skyMap3dContainerEl) {
            skyMap3dContainerEl.classList.toggle('active', is3d);
            skyMap3dContainerEl.setAttribute('aria-hidden', is3d ? 'false' : 'true');
        }

        // Toggle button states
        for (const btn of toggleBtns) {
            const isThisActive = btn.dataset.view === mode;
            btn.classList.toggle('active', isThisActive);
            btn.setAttribute('aria-pressed', isThisActive ? 'true' : 'false');
        }
    }

    /**
     * Switch the sky map view mode and persist the preference.
     *
     * Handles all async loading, error cases, and render-loop management.
     *
     * @param {'2d'|'3d'} mode
     */
    async function activateView(mode) {
        if (mode === '3d') {
            // Reset any stale error overlay from a prior failed attempt.
            if (errorEl) errorEl.setAttribute('hidden', '');

            // Guard: import maps not supported
            if (window._noImportMap) {
                alert('3D-vyn är inte tillgänglig i den här webbläsaren (saknar stöd för import maps).');
                return;
            }

            // Guard: WebGL not supported
            if (!window.WebGLRenderingContext) {
                show3dError('Din webbläsare stöder inte 3D-vy (WebGL saknas).');
                const btn3d = toggleBtns.find((b) => b.dataset.view === '3d');
                if (btn3d) btn3d.disabled = true;
                return;
            }

            try {
                // Lazy-load and instantiate SkyMap3D only once.
                if (skyMap3d === null) {
                    const mod = await import('./components/sky-map-3d.js');
                    skyMap3d = new mod.default(skyMap3dContainerEl);
                }

                // applyViewMode must run first so the container has layout
                // dimensions (clientWidth/clientHeight > 0) before activate()
                // calls _handleResize() to size the WebGL canvas.
                applyViewMode('3d');
                skyMap3d.activate();
                if (lastApiData !== null) {
                    skyMap3d.plotBodies(lastApiData.planets, lastApiData.sun, lastApiData.moon, lastApiData.events || []);
                }
                if (constellationData !== null && lastApiData !== null) {
                    skyMap3d.plotConstellations(constellationData, currentLocation.lat, currentLocation.lon, new Date(lastApiData.timestamp));
                }
                localStorage.setItem(VIEW_MODE_KEY, '3d');
            } catch (err) {
                console.error('Sky map 3D: failed to load or initialise', err);
                show3dError('3D-vyn kunde inte laddas. Försök igen senare.');
                localStorage.setItem(VIEW_MODE_KEY, '2d');
            }
        } else {
            // Switch to 2D
            if (skyMap3d) {
                skyMap3d.deactivate();
            }
            applyViewMode('2d');
            localStorage.setItem(VIEW_MODE_KEY, '2d');
        }
    }

    // Wire the toggle buttons.
    for (const btn of toggleBtns) {
        btn.addEventListener('click', () => activateView(btn.dataset.view));
    }

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

            if (skyMap3d !== null) {
                skyMap3d.plotBodies(data.planets, data.sun, data.moon, data.events || []);
            }

            if (constellationData !== null) {
                skyMap.plotConstellations(constellationData, location.lat, location.lon, new Date(data.timestamp));
                if (skyMap3d !== null) {
                    skyMap3d.plotConstellations(constellationData, location.lat, location.lon, new Date(data.timestamp));
                }
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
    // Handles skymap rendering, 3D pause/resume, and events lazy loading.
    window.addEventListener('tabChanged', (event) => {
        const { tabId } = event.detail;

        if (tabId === 'skymap') {
            skyMap.render();

            // First-load case: the user's stored preference was '3d' but we
            // deferred activation until the tab is visible so the container
            // has non-zero dimensions.  Consume the flag and activate now.
            if (pendingView3d) {
                pendingView3d = false;
                activateView('3d');
            } else if (skyMap3d !== null) {
                // Subsequent tab switches: resume the already-created 3D instance.
                const storedMode = localStorage.getItem(VIEW_MODE_KEY) || '2d';
                if (storedMode === '3d') {
                    skyMap3d.activate();
                }
            }
        } else {
            // Leaving the sky map tab — pause the 3D render loop to save GPU.
            if (skyMap3d !== null) {
                skyMap3d.deactivate();
            }
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
                if (skyMap3d !== null) {
                    skyMap3d.plotConstellations(constellationData, currentLocation.lat, currentLocation.lon, new Date(lastApiData.timestamp));
                }
            }
        })
        .catch((err) => {
            console.warn('Sky map: failed to load constellation data, running without constellation lines', err);
        });

    loadData(currentLocation);

});
