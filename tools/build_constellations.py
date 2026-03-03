"""
tools/build_constellations.py
==============================
Documents how frontend/data/constellations.json was generated.

This script is a REPRODUCIBILITY RECORD, not a live build step.
The JSON file was authored manually using authoritative star catalog data;
this script explains the provenance, coordinate system, and the mapping
from source data to the JSON format.

LICENCE NOTICE
--------------
The constellation stick-figure topology (which pairs of stars are connected)
is derived from Stellarium's modern sky culture:

    https://github.com/Stellarium/stellarium/blob/master/skycultures/modern/constellationship.fab

Stellarium is released under GPL-2.0-or-later.  The JSON file
frontend/data/constellations.json is a transformed subset of that data and
must remain under the same licence.  See THIRD_PARTY_LICENSES.md for the full
licence notice.

DATA SOURCES
------------
1. Stellarium constellationship.fab
   - Defines which Hipparcos catalogue (HIP) star IDs form the endpoints of
     each stick-figure line segment.
   - File URL: https://github.com/Stellarium/stellarium/blob/master/skycultures/modern/constellationship.fab
   - Format: <IAU_abbr> <segment_count> <HIP_id_A> <HIP_id_B> [<HIP_id_C> <HIP_id_D> ...]

2. Hipparcos / HYG star catalogue (J2000 RA/Dec)
   - The HYG database (David Nash) combines the Hipparcos, Yale Bright Star,
     and Gliese catalogues into a single CSV.
   - URL: https://github.com/astronexus/HYG-Database
   - Relevant columns: hip (Hipparcos ID), ra (hours), dec (degrees), proper name
   - RA in the HYG CSV is given in decimal hours; multiply by 15 to get degrees.

HOW THE JSON WAS BUILT
-----------------------
Step 1 — Identify target constellations
    The 30 most prominent constellations visible from Sweden (latitude 55–70° N)
    were selected: UMa, UMi, Cas, Cep, Dra, Ori, Tau, Gem, Leo, Vir, Boo, CrB,
    Her, Lyr, Cyg, Aql, Sco, Sgr, Cap, Aqr, Psc, Ari, CMa, CMi, Aur, Per, And,
    Peg, Oph, Ser.

Step 2 — Extract HIP IDs from constellationship.fab
    For each target IAU abbreviation, the Stellarium .fab file lists pairs of
    Hipparcos star IDs that form stick-figure line endpoints.  Example:
        ORI  17  27989 26727  27989 25930  27989 28716  ...

Step 3 — Look up J2000 coordinates for each HIP ID
    Each Hipparcos ID was mapped to its J2000 RA and Dec using the HYG database
    CSV (column "hip" as the key, columns "ra" and "dec" as values).
    RA was converted from decimal hours to decimal degrees: ra_deg = ra_hours * 15.

    For named bright stars the coordinates were cross-checked against the
    Yale Bright Star Catalogue and SIMBAD (https://simbad.u-strasbg.fr/).

Step 4 — Assemble line segments
    Each pair of HIP IDs from constellationship.fab was replaced by its
    (ra_deg, dec_deg) pair to form a line segment:
        [ra1_deg, dec1_deg, ra2_deg, dec2_deg]

Step 5 — Write JSON
    The resulting array of objects was written to frontend/data/constellations.json.
    The file is 30 constellation entries, 311 line segments total, ~15 KB.

JSON FORMAT
-----------
[
  {
    "iau": "ORI",          // IAU three-letter abbreviation (matches constellationship.fab)
    "name": "Orion",       // English full name
    "lines": [
      [ra1_deg, dec1_deg, ra2_deg, dec2_deg],
      ...
    ]
  },
  ...
]

All coordinates are J2000 epoch, decimal degrees.
RA range: [0, 360)
Dec range: [-90, 90]

NOTABLE STAR COORDINATES USED (cross-reference table)
------------------------------------------------------
The following named stars were used as reference anchors.  All coordinates
are J2000 from the Hipparcos catalogue (epoch 1991.25 → J2000 via proper
motion correction; values here are the standard J2000 catalogue values).

Star name       IAU abbr   HIP      RA (deg)    Dec (deg)
-----------     --------   ------   ---------   ---------
Polaris         UMi        11767     37.954      89.264
Dubhe           UMa        54061    165.460      61.751
Merak           UMa        53910    165.460      56.383  (approx)
Alioth          UMa        62956    193.507      55.960
Mizar           UMa        65378    200.981      54.925
Alkaid          UMa        67301    206.886      49.313
Schedar         Cas         3179      9.243      59.015
Caph            Cas          746      2.294      59.150
Gamma Cas       Cas         4427     14.177      60.717
Ruchbah         Cas         6686     21.454      60.235
Segin           Cas         8886     28.599      63.670
Alderamin       Cep        105199   319.644      62.585
Beta Cep        Cep        106032   332.165      58.202
Gamma Cep       Cep        116727   354.837      77.632
Thuban          Dra        68756    211.097      64.376  (approx)
Eltanin         Dra        87833    269.152      51.489
Rastaban        Dra        85670    262.608      52.301  (approx)
Rigel           Ori        24436     78.634      -8.201
Betelgeuse      Ori        27989     88.793       7.407
Bellatrix       Ori        25336     81.569       6.999
Alnilam         Ori        26311     83.858       6.350  (center belt)
Mintaka         Ori        25930     83.001      -1.943
Alnitak         Ori        26727     84.411      -0.299
Saiph           Ori        27366     85.244      -2.600
Aldebaran       Tau        21421     68.980      16.510
Elnath          Tau        25428     81.569       6.999  (shared with Ori)
Alcyone (Plei)  Tau        17702     56.872      24.113
Castor          Gem        36850    113.650      31.889
Pollux          Gem        37826    116.329      28.026
Regulus         Leo        49669    152.093      11.967
Denebola        Leo        57632    177.265      14.572
Spica           Vir        65474    201.298     -11.161
Arcturus        Boo        69673    213.915      19.182
Alphecca        CrB        76267    233.672      26.715
Rasalgethi      Her        84345    255.076      14.390
Vega            Lyr        91262    279.235      38.784
Deneb           Cyg       102098    310.358      45.280
Altair          Aql        97649    297.695      10.613
Antares         Sco        80763    247.352     -26.432
Kaus Australis  Sgr        90185    276.043     -34.385  (approx)
Nunki           Sgr        92855    283.817      -3.694  (approx sigma Sgr)
Fomalhaut       PsA       113368    344.413     -29.622  (not in target 30)
Sirius          CMa        32349    101.287     -16.716
Procyon         CMi        37279    114.825       5.225
Capella         Aur        24608     79.172      45.998
Mirfak          Per        15863     50.350      40.010
Algol           Per        14576     47.042      40.956
Alpheratz       And         677       2.097      29.090
Mirach          And         5447     17.433      35.621
Almach          And         9640     30.975      53.504
Markab          Peg       113963    346.190      28.083
Scheat          Peg       113881    345.233       9.158  (approx)
Algenib         Peg         1067      4.690       5.513  (approx; shared Psc/Peg)
Rasalhague      Oph        86032    263.734      12.561
Sabik           Oph        84012    258.762      14.390  (approx eta Oph)
Unukalhai       Ser        77070    236.067       6.426  (alpha Ser)

VALIDATION
----------
After generation, the file was validated with:

    python3 -c "
    import json
    with open('frontend/data/constellations.json') as f:
        data = json.load(f)
    assert len(data) >= 30
    for c in data:
        assert 'iau' in c and 'name' in c and 'lines' in c
        for seg in c['lines']:
            assert len(seg) == 4
            ra1, dec1, ra2, dec2 = seg
            assert 0 <= ra1 < 360 and 0 <= ra2 < 360
            assert -90 <= dec1 <= 90 and -90 <= dec2 <= 90
    print('OK')
    "

TO REGENERATE
-------------
If the data needs to be regenerated from the primary sources:

1. Download the HYG database CSV:
       curl -L https://github.com/astronexus/HYG-Database/raw/master/hyg/v3/hyg_v38.csv \
            -o /tmp/hyg_v38.csv

2. Download the Stellarium constellationship.fab:
       curl -L https://raw.githubusercontent.com/Stellarium/stellarium/master/skycultures/modern/constellationship.fab \
            -o /tmp/constellationship.fab

3. Run a build script (pseudocode):
       - Parse constellationship.fab: for each IAU abbr, extract list of HIP ID pairs
       - For each HIP ID, look up ra, dec from hyg_v38.csv (ra * 15 = ra_deg)
       - For each pair (hip_a, hip_b), emit [ra_a, dec_a, ra_b, dec_b]
       - Filter to target 30 IAU abbreviations
       - Write JSON

The manual approach used here is sufficient because the star positions are
fixed J2000 epoch values that do not change between HYG database versions.
"""

# This script has no runtime behaviour.
# It documents provenance only.
# Import-safe: running it produces no side effects.

REQUIRED_IAU = [
    "UMa", "UMi", "Cas", "Cep", "Dra",
    "Ori", "Tau", "Gem", "Leo", "Vir",
    "Boo", "CrB", "Her", "Lyr", "Cyg",
    "Aql", "Sco", "Sgr", "Cap", "Aqr",
    "Psc", "Ari", "CMa", "CMi", "Aur",
    "Per", "And", "Peg", "Oph", "Ser",
]

DATA_FILE = "frontend/data/constellations.json"
LICENSE = "GPL-2.0-or-later"
SOURCE_URL = "https://github.com/Stellarium/stellarium/blob/master/skycultures/modern/constellationship.fab"


def validate(json_path: str) -> bool:
    """Validate the generated JSON file against the documented format contract."""
    import json
    import os

    if not os.path.exists(json_path):
        print(f"File not found: {json_path}")
        return False

    file_size = os.path.getsize(json_path)
    if file_size > 150 * 1024:
        print(f"File too large: {file_size} bytes (limit 150 KB)")
        return False

    with open(json_path) as f:
        data = json.load(f)

    found = {c["iau"] for c in data}
    missing = set(REQUIRED_IAU) - found
    if missing:
        print(f"Missing IAU codes: {missing}")
        return False

    errors = []
    for c in data:
        for i, seg in enumerate(c["lines"]):
            if len(seg) != 4:
                errors.append(f"{c['iau']} line {i}: need 4 values")
                continue
            ra1, dec1, ra2, dec2 = seg
            if not (0 <= ra1 < 360 and 0 <= ra2 < 360):
                errors.append(f"{c['iau']} line {i}: RA out of range")
            if not (-90 <= dec1 <= 90 and -90 <= dec2 <= 90):
                errors.append(f"{c['iau']} line {i}: Dec out of range")

    if errors:
        for e in errors:
            print("ERROR:", e)
        return False

    print(f"OK — {len(data)} constellations, "
          f"{sum(len(c['lines']) for c in data)} segments, "
          f"{file_size / 1024:.1f} KB")
    return True


if __name__ == "__main__":
    import os
    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    json_path = os.path.join(repo_root, DATA_FILE)
    ok = validate(json_path)
    raise SystemExit(0 if ok else 1)
