/**
 * MapSelector - Interactive map component for location selection using Leaflet
 */

const SWEDEN_CENTER = { lat: 62.0, lon: 15.0 };
const DEFAULT_ZOOM = 5;
const GEOCODE_API = '/api/v1/geocode/reverse';

export class MapSelector {
    constructor() {
        this.map = null;
        this.marker = null;
        this.geocodeTimeout = null;
    }

    /**
     * Initialize map with OpenStreetMap tiles
     */
    initialize(containerId, initialLocation) {
        if (this.map) {
            this.destroy();
        }

        const container = document.getElementById(containerId);
        if (!container) {
            throw new Error(`Container ${containerId} not found`);
        }

        // Create Leaflet map
        this.map = L.map(containerId).setView(
            [initialLocation.lat, initialLocation.lon],
            DEFAULT_ZOOM
        );

        // Add OpenStreetMap tiles
        L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
            attribution: '© OpenStreetMap contributors',
            maxZoom: 19
        }).addTo(this.map);

        // Create draggable marker
        this.marker = L.marker([initialLocation.lat, initialLocation.lon], {
            draggable: true
        }).addTo(this.map);

        // Handle marker drag
        this.marker.on('dragend', () => {
            const pos = this.marker.getLatLng();
            this.onLocationSelected(pos.lat, pos.lng);
        });

        // Handle map clicks
        this.map.on('click', (e) => {
            this.setLocation(e.latlng.lat, e.latlng.lng);
            this.onLocationSelected(e.latlng.lat, e.latlng.lng);
        });
    }

    /**
     * Set marker location
     */
    setLocation(lat, lon) {
        if (!this.marker) return;
        this.marker.setLatLng([lat, lon]);
        this.map.panTo([lat, lon]);
    }

    /**
     * Refresh map size after container visibility changes
     */
    invalidateSize() {
        if (!this.map) return;
        this.map.invalidateSize({ pan: false });
    }

    /**
     * Handle location selection with debounced geocoding
     */
    onLocationSelected(lat, lon) {
        // Emit immediate event with coordinates
        window.dispatchEvent(new CustomEvent('mapLocationSelected', {
            detail: { lat, lon, name: null }
        }));

        // Debounce geocoding requests
        clearTimeout(this.geocodeTimeout);
        this.geocodeTimeout = setTimeout(() => {
            this.reverseGeocode(lat, lon);
        }, 500);
    }

    /**
     * Reverse geocode coordinates to location name
     */
    async reverseGeocode(lat, lon) {
        try {
            const url = `${GEOCODE_API}?lat=${lat}&lon=${lon}`;

            const response = await fetch(url);

            if (!response.ok) {
                throw new Error(`Geocoding failed: ${response.status}`);
            }

            const data = await response.json();

            // Extract location name
            let name = 'Unknown Location';
            if (data.address) {
                const parts = [];
                if (data.address.city) parts.push(data.address.city);
                else if (data.address.town) parts.push(data.address.town);
                else if (data.address.village) parts.push(data.address.village);
                else if (data.address.municipality) parts.push(data.address.municipality);

                if (data.address.country) parts.push(data.address.country);

                if (parts.length > 0) {
                    name = parts.join(', ');
                }
            }

            // Emit event with geocoded name
            window.dispatchEvent(new CustomEvent('geocodingComplete', {
                detail: { lat, lon, name }
            }));

        } catch (error) {
            console.error('Geocoding failed:', error);
            // Emit event with fallback name
            window.dispatchEvent(new CustomEvent('geocodingComplete', {
                detail: {
                    lat,
                    lon,
                    name: `Location (${lat.toFixed(2)}°, ${lon.toFixed(2)}°)`
                }
            }));
        }
    }

    /**
     * Clean up map instance
     */
    destroy() {
        if (this.geocodeTimeout) {
            clearTimeout(this.geocodeTimeout);
        }
        if (this.map) {
            this.map.remove();
            this.map = null;
            this.marker = null;
        }
    }
}
