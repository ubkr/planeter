/**
 * SettingsModal - Modal dialog for location selection
 */

import { MapSelector } from './map-selector.js';

export class SettingsModal {
    constructor(locationManager) {
        this.modalTransitionDelay = 300;
        this.locationManager = locationManager;
        this.mapSelector = new MapSelector();
        this.isOpen = false;
        this.selectedLocation = null;

        this.createModal();
        this.attachEventListeners();
    }

    /**
     * Create modal DOM structure
     */
    createModal() {
        const modalHTML = `
            <div id="settingsModal" class="modal-overlay" style="display: none;">
                <div class="modal-content">
                    <button class="modal-close" aria-label="Close">&times;</button>
                    <h2>Inställningar</h2>
                    <div id="mapContainer" style="height: 400px; border-radius: 8px; overflow: hidden;"></div>
                    <div class="location-info">
                        <p class="location-name">Klicka på kartan för att välja plats</p>
                        <p class="coordinates">Lat: --, Lon: --</p>
                        <p class="warning" style="display: none;">Utanför Sverige – data kan vara mindre noggrann</p>
                    </div>
                    <div class="modal-actions">
                        <button class="btn-cancel">Avbryt</button>
                        <button class="btn-save" disabled>Spara plats</button>
                    </div>
                </div>
            </div>
        `;

        // Insert modal into container
        const container = document.getElementById('settingsModalContainer');
        if (container) {
            container.innerHTML = modalHTML;
        } else {
            document.body.insertAdjacentHTML('beforeend', modalHTML);
        }

        // Store references
        this.modal = document.getElementById('settingsModal');
        this.closeBtn = this.modal.querySelector('.modal-close');
        this.cancelBtn = this.modal.querySelector('.btn-cancel');
        this.saveBtn = this.modal.querySelector('.btn-save');
        this.locationName = this.modal.querySelector('.location-name');
        this.coordinates = this.modal.querySelector('.coordinates');
        this.warning = this.modal.querySelector('.warning');
    }

    /**
     * Attach event listeners
     */
    attachEventListeners() {
        // Close button
        this.closeBtn.addEventListener('click', () => this.close());

        // Cancel button
        this.cancelBtn.addEventListener('click', () => this.close());

        // Save button
        this.saveBtn.addEventListener('click', () => this.save());

        // Click outside to close
        this.modal.addEventListener('click', (e) => {
            if (e.target === this.modal) {
                this.close();
            }
        });

        // ESC key to close
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape' && this.isOpen) {
                this.close();
            }
        });

        // Listen for map location selection
        window.addEventListener('mapLocationSelected', (e) => {
            this.onLocationSelected(e.detail);
        });

        // Listen for geocoding completion
        window.addEventListener('geocodingComplete', (e) => {
            this.onGeocodingComplete(e.detail);
        });
    }

    /**
     * Open modal
     */
    open() {
        this.isOpen = true;
        this.modal.style.display = 'flex';

        // Slight delay to allow display:flex to take effect before animation
        setTimeout(() => {
            this.modal.classList.add('modal-visible');

            // Initialize map with current location
            const currentLocation = this.locationManager.getLocation();
            this.selectedLocation = currentLocation;
            this.updateLocationDisplay(currentLocation);

            this.mapSelector.initialize('mapContainer', currentLocation);

            setTimeout(() => {
                this.mapSelector.invalidateSize();
            }, this.modalTransitionDelay);
        }, 10);
    }

    /**
     * Close modal
     */
    close() {
        this.modal.classList.remove('modal-visible');

        // Wait for fade animation before hiding
        setTimeout(() => {
            this.isOpen = false;
            this.modal.style.display = 'none';
            this.mapSelector.destroy();
            this.resetForm();
        }, this.modalTransitionDelay);
    }

    /**
     * Reset form state
     */
    resetForm() {
        this.selectedLocation = null;
        this.saveBtn.disabled = true;
        this.locationName.textContent = 'Klicka på kartan för att välja plats';
        this.coordinates.textContent = 'Lat: --, Lon: --';
        this.warning.style.display = 'none';
    }

    /**
     * Handle location selection from map
     */
    onLocationSelected(location) {
        this.selectedLocation = location;
        this.updateLocationDisplay(location);
        this.saveBtn.disabled = false;

        // Show loading state for location name
        if (!location.name) {
            this.locationName.textContent = 'Hämtar platsnamn...';
        }
    }

    /**
     * Handle geocoding completion
     */
    onGeocodingComplete(location) {
        if (this.selectedLocation &&
            this.selectedLocation.lat === location.lat &&
            this.selectedLocation.lon === location.lon) {
            this.selectedLocation.name = location.name;
            this.updateLocationDisplay(this.selectedLocation);
        }
    }

    /**
     * Update location display in modal
     */
    updateLocationDisplay(location) {
        // Update location name
        if (location.name) {
            this.locationName.textContent = location.name;
        }

        // Update coordinates
        this.coordinates.textContent = `Lat: ${location.lat.toFixed(4)}°, Lon: ${location.lon.toFixed(4)}°`;

        // Show warning if outside Sweden
        const outsideSweden = this.locationManager.isOutsideSweden(location.lat, location.lon);
        this.warning.style.display = outsideSweden ? 'block' : 'none';
    }

    /**
     * Save selected location
     */
    save() {
        if (!this.selectedLocation) return;

        const success = this.locationManager.saveLocation(
            this.selectedLocation.lat,
            this.selectedLocation.lon,
            this.selectedLocation.name
        );

        if (success) {
            this.close();
        } else {
            alert('Kunde inte spara plats. Försök igen.');
        }
    }
}
