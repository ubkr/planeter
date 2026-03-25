/**
 * test-astro-projection.mjs
 *
 * Standalone Node.js test script for raDecToAltAz in astro-projection.js.
 *
 * Run with:   node frontend/tests/test-astro-projection.mjs
 *
 * Exits 0 if all tests pass, 1 if any fail.
 */

import { raDecToAltAz } from '../js/astro-projection.js';

// ---------------------------------------------------------------------------
// Minimal assertion helpers — no test framework needed.
// ---------------------------------------------------------------------------

let failures = 0;

/**
 * Check that `value` is within `tolerance` of `expected`.
 * Handles azimuth wrap-around by trying both the raw difference and the
 * shortest arc across the 0/360 boundary.
 *
 * @param {number} value
 * @param {number} expected
 * @param {number} tolerance
 * @returns {boolean}
 */
function withinTolerance(value, expected, tolerance) {
    const diff = Math.abs(value - expected);
    // Shortest arc for angles (handles the 0/360 wrap).
    const diffWrapped = Math.abs(diff - 360);
    return Math.min(diff, diffWrapped) <= tolerance;
}

/**
 * Run a single Alt/Az test case.
 *
 * @param {string} name          - Human-readable test name.
 * @param {object} input         - { ra_deg, dec_deg, lat, lon, utc_iso }
 * @param {object} expected      - { altitude_deg, azimuth_deg }
 * @param {object} tolerances    - { altitude_tol, azimuth_tol }
 */
function testAltAz(name, input, expected, tolerances) {
    const date = new Date(input.utc_iso);
    const result = raDecToAltAz(
        input.ra_deg,
        input.dec_deg,
        input.lat,
        input.lon,
        date
    );

    const altOk = withinTolerance(
        result.altitude_deg,
        expected.altitude_deg,
        tolerances.altitude_tol
    );

    const azOk = withinTolerance(
        result.azimuth_deg,
        expected.azimuth_deg,
        tolerances.azimuth_tol
    );

    if (altOk && azOk) {
        console.log(`PASS: ${name}`);
    } else {
        const gotAlt = result.altitude_deg.toFixed(2);
        const gotAz  = result.azimuth_deg.toFixed(2);
        const expAlt = expected.altitude_deg.toFixed(2);
        const expAz  = expected.azimuth_deg.toFixed(2);
        console.log(
            `FAIL: ${name} — ` +
            `got altitude=${gotAlt} az=${gotAz}, ` +
            `expected altitude≈${expAlt} az≈${expAz}`
        );
        failures += 1;
    }
}

// ---------------------------------------------------------------------------
// Test: azimuth range check (valid range helper used by both main tests)
// ---------------------------------------------------------------------------

function testAzimuthInRange(name, input, minAz, maxAz, altMin, altMax) {
    const date = new Date(input.utc_iso);
    const result = raDecToAltAz(
        input.ra_deg,
        input.dec_deg,
        input.lat,
        input.lon,
        date
    );

    const altOk = result.altitude_deg >= altMin && result.altitude_deg <= altMax;
    const azOk  = result.azimuth_deg  >= minAz  && result.azimuth_deg  <= maxAz;

    if (altOk && azOk) {
        console.log(`PASS: ${name}`);
    } else {
        const gotAlt = result.altitude_deg.toFixed(2);
        const gotAz  = result.azimuth_deg.toFixed(2);
        console.log(
            `FAIL: ${name} — ` +
            `got altitude=${gotAlt} az=${gotAz}, ` +
            `expected altitude in [${altMin},${altMax}] az in [${minAz},${maxAz}]`
        );
        failures += 1;
    }
}

// ---------------------------------------------------------------------------
// Test cases
// ---------------------------------------------------------------------------

// Test 1 — Polaris
// RA 37.9542°, Dec 89.2642° from lat=59°N lon=18°E on 2024-03-20 00:00:00 UTC.
// Polaris sits almost at the celestial north pole, so altitude ≈ observer
// latitude (59°) and azimuth ≈ 0° (due North), regardless of time.
testAltAz(
    'Polaris: altitude ≈ 59°, azimuth ≈ 0° (North)',
    {
        ra_deg  : 37.9542,
        dec_deg : 89.2642,
        lat     : 59,
        lon     : 18,
        utc_iso : '2024-03-20T00:00:00.000Z',
    },
    {
        altitude_deg : 59,
        azimuth_deg  : 0,
    },
    {
        altitude_tol : 2,
        azimuth_tol  : 5,
    }
);

// Test 2 — Sirius
// RA 101.2917°, Dec -16.7161° from lat=59°N lon=18°E on 2024-01-15 20:00:00 UTC.
// At this instant Sirius is low in the south-southeast from Stockholm-latitude
// observers. Cross-checks against the backend ephem library place it near
// altitude 10.8°, azimuth 152°.
testAzimuthInRange(
    'Sirius: altitude in [10°, 25°], azimuth in [140°, 165°] (south-southeast)',
    {
        ra_deg  : 101.2917,
        dec_deg : -16.7161,
        lat     : 59,
        lon     : 18,
        utc_iso : '2024-01-15T20:00:00.000Z',
    },
    /* minAz */ 140,
    /* maxAz */ 165,
    /* altMin */ 10,
    /* altMax */ 25
);

// Test 3 — Vega (East quadrant — azimuth discriminator)
// RA 279.2342°, Dec 38.7837° from lat=59°N lon=18°E on 2024-06-21 19:00:00 UTC.
//
// At this instant:
//   GMST ≈ 195.46°  →  LST ≈ 213.46°
//   HA = (LST − RA) % 360 = (213.46 − 279.23) % 360 ≈ 294.23°
//
// HA > 180° means the star is East of the meridian (still rising).  With the
// atan2 azimuth formula used by raDecToAltAz the expected azimuth is ≈ 94°
// (firmly East, slightly south of due East).  Altitude is ≈ 45°.
//
// This test distinguishes a correct implementation from one with a mirrored
// azimuth formula: a mirrored formula would place Vega in the West quadrant
// (~266°) rather than the East (~94°).
testAzimuthInRange(
    'Vega: altitude in [20°, 70°], azimuth in [40°, 120°] (East quadrant)',
    {
        ra_deg  : 279.2342,
        dec_deg : 38.7837,
        lat     : 59,
        lon     : 18,
        utc_iso : '2024-06-21T19:00:00.000Z',
    },
    /* minAz */ 40,
    /* maxAz */ 120,
    /* altMin */ 20,
    /* altMax */ 70
);

// ---------------------------------------------------------------------------
// Summary
// ---------------------------------------------------------------------------

if (failures === 0) {
    console.log('\nAll tests passed.');
    process.exit(0);
} else {
    console.log(`\n${failures} test(s) failed.`);
    process.exit(1);
}
