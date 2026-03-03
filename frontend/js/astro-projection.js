/**
 * astro-projection.js - Pure coordinate-conversion utilities for celestial mechanics.
 *
 * Converts equatorial coordinates (Right Ascension, Declination) to horizontal
 * coordinates (Altitude, Azimuth) for a given observer location and time.
 *
 * No DOM access. No external imports. Safe to use in any JS environment.
 *
 * Reference: Jean Meeus, "Astronomical Algorithms", 2nd ed., Ch. 12–13.
 */

// ---------------------------------------------------------------------------
// Internal helpers
// ---------------------------------------------------------------------------

/**
 * Convert degrees to radians.
 *
 * @param {number} deg
 * @returns {number}
 */
function toRad(deg) {
    return deg * Math.PI / 180;
}

/**
 * Convert radians to degrees.
 *
 * @param {number} rad
 * @returns {number}
 */
function toDeg(rad) {
    return rad * 180 / Math.PI;
}

/**
 * Normalise an angle in degrees to the range [0, 360).
 *
 * @param {number} deg
 * @returns {number}
 */
function normDeg(deg) {
    return ((deg % 360) + 360) % 360;
}

/**
 * Compute the Julian Date from a JS Date object.
 *
 * The formula converts the proleptic Gregorian calendar date and time to the
 * Julian Day Number (Meeus, Ch. 7).
 *
 * @param {Date} date - A JS Date object representing a UTC instant.
 * @returns {number} Julian Date (continuous day count from noon 1 Jan 4713 BC).
 */
function julianDate(date) {
    // Extract UTC components.
    const year  = date.getUTCFullYear();
    const month = date.getUTCMonth() + 1; // getUTCMonth is 0-based
    const day   = date.getUTCDate()
        + date.getUTCHours()   / 24
        + date.getUTCMinutes() / 1440
        + date.getUTCSeconds() / 86400
        + date.getUTCMilliseconds() / 86400000;

    // Meeus Eq. 7.1: for January and February treat them as months 13/14 of the
    // preceding year.
    let Y = year;
    let M = month;
    if (M <= 2) {
        Y -= 1;
        M += 12;
    }

    const A = Math.floor(Y / 100);
    // Gregorian calendar correction (not applied for Julian calendar dates).
    const B = 2 - A + Math.floor(A / 4);

    return Math.floor(365.25 * (Y + 4716))
         + Math.floor(30.6001 * (M + 1))
         + day
         + B
         - 1524.5;
}

/**
 * Compute Greenwich Mean Sidereal Time (GMST) in degrees for a given Julian Date.
 *
 * Uses the Meeus polynomial (Ch. 12, Eq. 12.4):
 *   GMST = 280.46061837
 *        + 360.98564736629 * (JD - 2451545.0)
 *        + 0.000387933 * T²
 *        - T³ / 38710000
 * where T = Julian centuries from J2000.0.
 *
 * @param {number} jd - Julian Date.
 * @returns {number} GMST in degrees, normalised to [0, 360).
 */
function gmstDeg(jd) {
    // Julian centuries from J2000.0 (noon 1 Jan 2000 UTC = JD 2451545.0).
    const T  = (jd - 2451545.0) / 36525;
    const T2 = T * T;
    const T3 = T2 * T;

    const gmst = 280.46061837
               + 360.98564736629 * (jd - 2451545.0)
               + 0.000387933 * T2
               - T3 / 38710000;

    return normDeg(gmst);
}

// ---------------------------------------------------------------------------
// Public API
// ---------------------------------------------------------------------------

/**
 * Convert equatorial coordinates to horizontal (Alt/Az) coordinates.
 *
 * Implements the standard spherical-trigonometry conversion:
 *
 *   sin(alt) = sin(dec)·sin(lat) + cos(dec)·cos(lat)·cos(HA)
 *
 *   az = atan2(sin(HA),  cos(lat)·tan(dec) − sin(lat)·cos(HA)) + 180°
 *
 * Azimuth is measured from North (0°) clockwise through East (90°), matching
 * the compass convention used throughout this project.
 *
 * @param {number}      ra_deg        - Right Ascension in degrees (0–360).
 * @param {number}      dec_deg       - Declination in degrees (−90 to +90).
 * @param {number}      lat           - Observer latitude in degrees (positive North).
 * @param {number}      lon           - Observer longitude in degrees (positive East).
 * @param {Date|number} utc_timestamp - UTC instant as a JS Date object or a Unix
 *                                      timestamp in milliseconds.
 * @returns {{ altitude_deg: number, azimuth_deg: number }}
 *   altitude_deg in [−90, 90]; azimuth_deg in [0, 360).
 */
export function raDecToAltAz(ra_deg, dec_deg, lat, lon, utc_timestamp) {
    // Accept either a Date object or a millisecond Unix timestamp.
    const date = (utc_timestamp instanceof Date)
        ? utc_timestamp
        : new Date(utc_timestamp);

    // Step 1: Julian Date for this UTC instant.
    const jd = julianDate(date);

    // Step 2: Greenwich Mean Sidereal Time in degrees.
    const gmst = gmstDeg(jd);

    // Step 3: Local Sidereal Time = GMST + observer longitude (east positive).
    const lst = normDeg(gmst + lon);

    // Step 4: Hour Angle = LST − RA, normalised to [0, 360).
    const ha_deg = normDeg(lst - ra_deg);

    // Step 5: Convert (HA, Dec, lat) to (altitude, azimuth) using spherical trig.
    const ha  = toRad(ha_deg);
    const dec = toRad(dec_deg);
    const phi = toRad(lat);  // observer latitude

    // Altitude.
    const sinAlt = Math.sin(dec) * Math.sin(phi)
                 + Math.cos(dec) * Math.cos(phi) * Math.cos(ha);
    const altitude_deg = toDeg(Math.asin(sinAlt));

    // Azimuth — use atan2 for correct quadrant resolution (Meeus Eq. 13.5).
    // Numerator:   sin(HA)
    // Denominator: cos(lat)·tan(dec) − sin(lat)·cos(HA)
    // Adding 180° converts the astronomical azimuth (South=0°) to the compass
    // azimuth convention (North=0°, East=90°, clockwise).
    const az_num = Math.sin(ha);
    const az_den = Math.cos(phi) * Math.tan(dec) - Math.sin(phi) * Math.cos(ha);
    const azimuth_deg = normDeg(toDeg(Math.atan2(az_num, az_den)) + 180);

    return { altitude_deg, azimuth_deg };
}
