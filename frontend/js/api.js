/**
 * api.js - Fetch wrappers for the Planeter backend API
 *
 * All functions throw descriptive Swedish-language errors on failure.
 */

// Allow same-origin production use by default; override via a global or build injection.
const BASE_URL = (typeof window !== 'undefined' && window.PLANETER_API_BASE_URL) || '';

const TIMEOUT_MS = 10_000;

/**
 * Race a fetch call against a 10-second AbortController timeout.
 *
 * @param {string} url - Full URL to fetch.
 * @returns {Promise<Response>} Resolved fetch Response.
 * @throws {Error} Swedish-language error on network failure or timeout.
 */
async function fetchWithTimeout(url) {
    const controller = new AbortController();
    const timerId = setTimeout(() => controller.abort(), TIMEOUT_MS);

    try {
        const response = await fetch(url, { signal: controller.signal });
        return response;
    } catch (error) {
        if (error.name === 'AbortError') {
            throw new Error('Tidsgräns: Servern svarade inte i tid.');
        }
        throw new Error('Nätverksfel: Kunde inte nå servern.');
    } finally {
        clearTimeout(timerId);
    }
}

/**
 * Parse JSON from a Response and throw a Swedish error on failure.
 *
 * @param {Response} response
 * @returns {Promise<any>}
 * @throws {Error} Swedish-language error if JSON parsing fails.
 */
async function parseJson(response) {
    try {
        return await response.json();
    } catch {
        throw new Error('Ogiltigt svar från servern.');
    }
}

/**
 * Fetch the planets currently visible from the given coordinates.
 *
 * @param {number} lat - Latitude in decimal degrees.
 * @param {number} lon - Longitude in decimal degrees.
 * @returns {Promise<Object>} Full PlanetsResponse JSON object.
 * @throws {Error} Swedish-language error on network, HTTP, or parse failure.
 */
export async function fetchVisiblePlanets(lat, lon) {
    const url = `${BASE_URL}/api/v1/planets/visible?lat=${lat}&lon=${lon}`;
    const response = await fetchWithTimeout(url);

    if (!response.ok) {
        throw new Error(`Serverfel (${response.status}): Kunde inte hämta planetdata.`);
    }

    return parseJson(response);
}

/**
 * Fetch planet visibility data for tonight from the given coordinates.
 *
 * NOTE: This function is NOT currently called by the UI. The backend
 * `/tonight` endpoint performs sophisticated night-window sampling —
 * it steps through the astronomical night in discrete intervals and
 * scores each planet across the full window rather than at a single
 * instant. The current UI only consumes the simpler `/visible`
 * (real-time) endpoint via fetchVisiblePlanets(). fetchTonightPlanets
 * is retained here for the planned future "tonight view" feature, which
 * will display per-planet visibility forecasts across the entire night.
 *
 * @param {number} lat - Latitude in decimal degrees.
 * @param {number} lon - Longitude in decimal degrees.
 * @returns {Promise<Object>} Full PlanetsResponse JSON object.
 * @throws {Error} Swedish-language error on network, HTTP, or parse failure.
 */
export async function fetchTonightPlanets(lat, lon) {
    const url = `${BASE_URL}/api/v1/planets/tonight?lat=${lat}&lon=${lon}`;
    const response = await fetchWithTimeout(url);

    if (!response.ok) {
        throw new Error(`Serverfel (${response.status}): Kunde inte hämta planetdata.`);
    }

    return parseJson(response);
}

/**
 * Fetch data for a single planet by its lowercase English name.
 *
 * @param {string} name - Planet name: mercury, venus, mars, jupiter, or saturn.
 * @param {number} lat - Latitude in decimal degrees.
 * @param {number} lon - Longitude in decimal degrees.
 * @returns {Promise<Object>} Single planet data object.
 * @throws {Error} Swedish-language error on network, HTTP, or parse failure.
 *   404 yields "Okänd planet: {name}".
 */
export async function fetchPlanet(name, lat, lon) {
    const url = `${BASE_URL}/api/v1/planets/${name}?lat=${lat}&lon=${lon}`;
    const response = await fetchWithTimeout(url);

    if (response.status === 404) {
        throw new Error(`Okänd planet: ${name}`);
    }

    if (!response.ok) {
        throw new Error(`Serverfel (${response.status}): Kunde inte hämta planetdata.`);
    }

    return parseJson(response);
}
