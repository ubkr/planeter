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
  const absLat = Math.abs(location.lat);
  const absLon = Math.abs(location.lon);
  const latHemi = location.lat >= 0 ? 'N' : 'S';
  // Swedish convention: Ö = Öster (East), V = Väster (West)
  const lonHemi = location.lon >= 0 ? '\u00d6' : 'V';
  return `${absLat.toFixed(2)}\u00b0${latHemi}, ${absLon.toFixed(2)}\u00b0${lonHemi}`;
}

/**
 * Maps backend visibility reason keys to Swedish display strings.
 * Keys that are not present here are considered unknown and silently ignored
 * by formatVisibilityReasons.
 */
export const VISIBILITY_REASON_LABELS = {
  below_horizon:           'Planeten är under horisonten',
  dagsljus:                'För ljust – solen är uppe',
  molnighet:               'Molnen blockerar sikten',
  månljus:                 'Månens sken stör observationen',
  atmosfärisk_dämpning:    'Atmosfärisk dämpning vid låg höjd',
  goda_förhållanden:       'Goda observationsförhållanden',
};

/**
 * Converts an array of backend reason keys into a newline-separated string of
 * Swedish labels. Unknown keys are skipped with a console.warn.
 *
 * @param {string[]|null|undefined} reasons - Array of reason key strings.
 * @returns {string} Swedish labels joined by '\n', or '' for empty/null input.
 */
export function formatVisibilityReasons(reasons) {
  if (!reasons || reasons.length === 0) return '';

  const lines = reasons
    .map((key) => {
      const label = VISIBILITY_REASON_LABELS[key];
      if (label === undefined) {
        console.warn('[planeter] Unknown visibility reason key:', key);
      }
      return label;
    })
    .filter((label) => label !== undefined);

  return lines.join('\n');
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

/**
 * Returns an equipment recommendation for observing a planet.
 *
 * Possible return values:
 *   null          – planet is not observable (below horizon, zero score, or missing altitude)
 *   "naked_eye"   – planet is comfortably visible without aid
 *   "binoculars"  – binoculars recommended (low altitude or faint Mercury)
 *   "telescope"   – telescope recommended (valid value, not currently triggered by any rule)
 *
 * @param {{ is_above_horizon: boolean, visibility_score: number, altitude_deg: number, name: string, magnitude: number }} planet
 * @returns {null|"naked_eye"|"binoculars"|"telescope"}
 */
export function getEquipmentRecommendation(planet) {
  if (!planet.is_above_horizon || planet.visibility_score == null || planet.visibility_score === 0 || planet.altitude_deg == null) {
    return null;
  }

  if (planet.altitude_deg >= 5 && planet.altitude_deg <= 10) {
    return 'binoculars';
  }

  if (planet.name === 'Mercury' && planet.magnitude > 1.5) {
    return 'binoculars';
  }

  return 'naked_eye';
}
