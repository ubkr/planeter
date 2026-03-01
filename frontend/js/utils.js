/**
 * utils.js - Shared utility functions for the Planeter frontend.
 */

/**
 * Formats a location object for display.
 * @param {{ lat: number, lon: number, name?: string }} location
 * @returns {string}
 */
export function formatLocation(location) {
  if (location.name) {
    return location.name;
  }
  return `${location.lat.toFixed(2)}\u00b0N, ${location.lon.toFixed(2)}\u00b0\u00d6`;
}

/**
 * Map a visibility score (0–100) to a display level string.
 *
 * Tiers:
 *   0–30   → "poor"
 *   31–60  → "fair"
 *   61–79  → "good"
 *   80–100 → "excellent"
 *
 * @param {number} score - Integer 0–100.
 * @returns {"poor"|"fair"|"good"|"excellent"}
 */
export function scoreToLevel(score) {
    if (score <= 30) return 'poor';
    if (score <= 60) return 'fair';
    if (score <= 79) return 'good';
    return 'excellent';
}
