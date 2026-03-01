/**
 * LocationManager - Manages user location preferences with localStorage persistence
 */

const DEFAULT_LOCATION = {
    lat: 55.7,
    lon: 13.4,
    name: "Södra Sandby, Sweden"
};

const SWEDEN_BOUNDS = {
    minLat: 55.0,
    maxLat: 69.5,
    minLon: 10.5,
    maxLon: 24.5
};

const STORAGE_KEY = 'planet_location';
const MAX_LOCATION_AGE_DAYS = 30;
const MAX_LOCATION_AGE_MS = MAX_LOCATION_AGE_DAYS * 24 * 60 * 60 * 1000;
const ISO_8601_TIMESTAMP_REGEX = /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?(Z|[+-]\d{2}:\d{2})$/;

export class LocationManager {
    constructor() {
        this.storageAvailable = this.isStorageAvailable();
        this.currentLocation = this.loadLocation();
    }

    /**
     * Get current location (from storage or in-memory fallback)
     */
    getCurrentLocation() {
        const loadedLocation = this.loadLocation();
        this.currentLocation = loadedLocation;
        return { ...loadedLocation };
    }

    /**
     * Get current location (backward-compatible alias)
     */
    getLocation() {
        return this.getCurrentLocation();
    }

    /**
     * Check localStorage availability
     */
    isStorageAvailable() {
        try {
            const testKey = '__planet_storage_test__';
            localStorage.setItem(testKey, testKey);
            localStorage.removeItem(testKey);
            return true;
        } catch (error) {
            console.warn('localStorage is unavailable, using in-memory location only:', error);
            return false;
        }
    }

    /**
     * Read raw location payload from localStorage safely
     */
    readStoredLocation() {
        if (!this.storageAvailable) {
            return null;
        }

        try {
            return localStorage.getItem(STORAGE_KEY);
        } catch (error) {
            console.error('Failed to read location from localStorage:', error);
            return null;
        }
    }

    /**
     * Write location payload to localStorage safely
     */
    writeStoredLocation(location) {
        if (!this.storageAvailable) {
            return false;
        }

        try {
            localStorage.setItem(STORAGE_KEY, JSON.stringify(location));
            return true;
        } catch (error) {
            console.error('Failed to save location to localStorage:', error);
            return false;
        }
    }

    /**
     * Remove location payload from localStorage safely
     */
    removeStoredLocation() {
        if (!this.storageAvailable) {
            return true;
        }

        try {
            localStorage.removeItem(STORAGE_KEY);
            return true;
        } catch (error) {
            console.error('Failed to clear location from localStorage:', error);
            return false;
        }
    }

    /**
     * Build default location payload
     */
    createDefaultLocation() {
        return { ...DEFAULT_LOCATION };
    }

    /**
     * Save location to localStorage and emit change event
     */
    saveLocation(lat, lon, name) {
        // Validate coordinates
        if (lat < -90 || lat > 90 || lon < -180 || lon > 180) {
            throw new Error('Invalid coordinates');
        }

        const location = {
            lat,
            lon,
            name: name || `Custom Location (${lat.toFixed(2)}°, ${lon.toFixed(2)}°)`,
            timestamp: new Date().toISOString()
        };

        const saved = this.writeStoredLocation(location);
        this.currentLocation = location;

        // Emit custom event for location change
        window.dispatchEvent(new CustomEvent('locationChanged', {
            detail: location
        }));

        return saved;
    }

    /**
     * Clear saved location and revert to default
     */
    clearLocation() {
        const cleared = this.removeStoredLocation();
        this.currentLocation = { ...DEFAULT_LOCATION };

        window.dispatchEvent(new CustomEvent('locationChanged', {
            detail: this.currentLocation
        }));

        return cleared;
    }

    /**
     * Load location from localStorage or return default
     */
    loadLocation() {
        if (!this.storageAvailable) {
            return this.currentLocation ? { ...this.currentLocation } : this.createDefaultLocation();
        }

        const stored = this.readStoredLocation();
        if (!stored) {
            return this.createDefaultLocation();
        }

        try {
            const location = JSON.parse(stored);

            // Validate structure
            if (!this.isValidLocation(location)) {
                console.warn('Invalid location data in localStorage, using default');
                this.removeStoredLocation();
                return this.createDefaultLocation();
            }

            if (this.isLocationStale(location.timestamp)) {
                console.warn(`Stored location is older than ${MAX_LOCATION_AGE_DAYS} days, using default`);
                this.removeStoredLocation();
                return this.createDefaultLocation();
            }

            return location;
        } catch (error) {
            console.error('Failed to load location from localStorage:', error);
            this.removeStoredLocation();
            return this.createDefaultLocation();
        }
    }

    /**
     * Check if location data has valid structure
     */
    isValidLocation(location) {
        const timestampValid =
            typeof location.timestamp === 'string' &&
            ISO_8601_TIMESTAMP_REGEX.test(location.timestamp) &&
            Number.isFinite(new Date(location.timestamp).getTime());

        return location &&
               typeof location.lat === 'number' &&
               typeof location.lon === 'number' &&
               typeof location.name === 'string' &&
               timestampValid &&
               location.lat >= -90 && location.lat <= 90 &&
               location.lon >= -180 && location.lon <= 180;
    }

    /**
     * Check if stored location timestamp is older than max allowed age
     */
    isLocationStale(timestamp) {
        const timestampMs = new Date(timestamp).getTime();

        if (!Number.isFinite(timestampMs)) {
            return true;
        }

        return (Date.now() - timestampMs) > MAX_LOCATION_AGE_MS;
    }

    /**
     * Check if coordinates are outside Sweden
     */
    isOutsideSweden(lat, lon) {
        return lat < SWEDEN_BOUNDS.minLat ||
               lat > SWEDEN_BOUNDS.maxLat ||
               lon < SWEDEN_BOUNDS.minLon ||
               lon > SWEDEN_BOUNDS.maxLon;
    }

    /**
     * Get default location
     */
    static getDefaultLocation() {
        return { ...DEFAULT_LOCATION };
    }
}
