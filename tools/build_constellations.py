#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""
tools/build_constellations.py
==============================
Automated build script that generates frontend/data/constellations.json from
authoritative astronomical data sources.

PURPOSE
-------
This script rebuilds constellation stick-figure data from upstream sources
to ensure accuracy and traceability. It combines constellation topology from
Stellarium with precise stellar coordinates from the HYG database, validates
all coordinates against bright-stars.json, and generates a clean JSON output
suitable for sky map rendering.

Use this script when:
- Updating to newer versions of source data
- Adding new constellations to the rendered set
- Verifying constellation data accuracy

WORKFLOW
--------
1. Download source data:
   $ cd tools && ./download_sources.sh

2. Build constellation data:
   $ python3 tools/build_constellations.py

3. Validation: Script automatically cross-checks coordinates against
   frontend/data/bright-stars.json and fails if discrepancies exceed 0.1°

DATA SOURCES
------------
This script uses two authoritative data sources:

1. **Stellarium v24.4 Modern Skyculture** — constellationship.fab
   - Downloaded from: https://github.com/Stellarium/stellarium
   - Defines constellation stick-figure topology (which HIP stars connect)
   - Format: <IAU_abbr> <segment_count> <HIP_id_A> <HIP_id_B> ...
   - License: GPL-2.0-or-later (see THIRD_PARTY_LICENSES.md)

2. **HYG Database v3.8** — hyg_v38.csv
   - Downloaded from: https://github.com/astronexus/HYG-Database
   - Provides J2000 equatorial coordinates (RA/Dec) for Hipparcos stars
   - Note: RA in CSV is decimal hours; converted to degrees (* 15)

VALIDATION
----------
All coordinates are validated against frontend/data/bright-stars.json:
- Compares HYG coordinates with reference coordinates for named stars
- Tolerance: 0.1 degrees in both RA and Dec
- Build fails if validation fails (ensures data consistency)

OUTPUT
------
Generated file: frontend/data/constellations.json

Format:
[
  {
    "iau": "UMa",
    "name": "Ursa Major",
    "lines": [
      [ra1_deg, dec1_deg, ra2_deg, dec2_deg],
      ...
    ]
  },
  ...
]

Each line segment is a straight connection between two stars in J2000 coordinates.

EXPECTED OUTPUT FOR VERIFICATION
---------------------------------
Sample coordinates for key constellation stars:

Polaris (UMi, HIP 11767):   RA = 37.955°,  Dec = 89.264°
Dubhe   (UMa, HIP 54061):   RA = 165.932°, Dec = 61.751°
Rigel   (Ori, HIP 24436):   RA = 78.634°,  Dec = -8.202°
Vega    (Lyr, HIP 91262):   RA = 279.235°, Dec = 38.784°
Altair  (Aql, HIP 97649):   RA = 297.696°, Dec = 8.868°

These values should match the generated output within rounding precision.
"""

import csv
import json
import sys
from pathlib import Path
from typing import Dict, List, Tuple

# --- Configuration ---

# Target 30 constellations visible from Sweden
REQUIRED_IAU = [
    "UMa", "UMi", "Cas", "Cep", "Dra",
    "Ori", "Tau", "Gem", "Leo", "Vir",
    "Boo", "CrB", "Her", "Lyr", "Cyg",
    "Aql", "Sco", "Sgr", "Cap", "Aqr",
    "Psc", "Ari", "CMa", "CMi", "Aur",
    "Per", "And", "Peg", "Oph", "Ser",
]

# IAU code to English name mapping
IAU_TO_NAME = {
    "UMa": "Ursa Major",
    "UMi": "Ursa Minor",
    "Cas": "Cassiopeia",
    "Cep": "Cepheus",
    "Dra": "Draco",
    "Ori": "Orion",
    "Tau": "Taurus",
    "Gem": "Gemini",
    "Leo": "Leo",
    "Vir": "Virgo",
    "Boo": "Bootes",
    "CrB": "Corona Borealis",
    "Her": "Hercules",
    "Lyr": "Lyra",
    "Cyg": "Cygnus",
    "Aql": "Aquila",
    "Sco": "Scorpius",
    "Sgr": "Sagittarius",
    "Cap": "Capricornus",
    "Aqr": "Aquarius",
    "Psc": "Pisces",
    "Ari": "Aries",
    "CMa": "Canis Major",
    "CMi": "Canis Minor",
    "Aur": "Auriga",
    "Per": "Perseus",
    "And": "Andromeda",
    "Peg": "Pegasus",
    "Oph": "Ophiuchus",
    "Ser": "Serpens",
}

# HIP ID to star name mapping (for bright stars in constellations)
HIP_TO_NAME = {
    # Ursa Major
    54061: "Dubhe",
    53910: "Merak",
    62956: "Alioth",
    65378: "Mizar",
    67301: "Alkaid",
    # Ursa Minor
    11767: "Polaris",
    # Cassiopeia
    3179: "Schedar",
    746: "Caph",
    4427: "Gamma Cas",
    6686: "Ruchbah",
    8886: "Segin",
    # Cepheus
    105199: "Alderamin",
    106032: "Beta Cep",
    116727: "Gamma Cep",
    # Draco
    68756: "Thuban",
    87833: "Eltanin",
    85670: "Rastaban",
    # Orion
    24436: "Rigel",
    27989: "Betelgeuse",
    25336: "Bellatrix",
    26311: "Alnilam",
    25930: "Mintaka",
    26727: "Alnitak",
    27366: "Saiph",
    22449: "Meissa",
    # Taurus
    21421: "Aldebaran",
    25428: "Elnath",
    # Gemini
    36850: "Castor",
    37826: "Pollux",
    # Leo
    49669: "Regulus",
    57632: "Denebola",
    # Virgo
    65474: "Spica",
    # Bootes
    69673: "Arcturus",
    # Corona Borealis
    76267: "Alphecca",
    # Hercules
    84345: "Rasalgethi",
    # Lyra
    91262: "Vega",
    # Cygnus
    102098: "Deneb",
    # Aquila
    97649: "Altair",
    # Scorpius
    80763: "Antares",
    # Sagittarius
    90185: "Kaus Australis",
    92855: "Nunki",
    # Canis Major
    32349: "Sirius",
    # Canis Minor
    37279: "Procyon",
    # Auriga
    24608: "Capella",
    # Perseus
    15863: "Mirfak",
    14576: "Algol",
    # Andromeda
    677: "Alpheratz",
    5447: "Mirach",
    9640: "Almach",
    # Pegasus
    113963: "Markab",
    # Ophiuchus
    86032: "Rasalhague",
    # Serpens
    77070: "Unukalhai",
}


# --- Step 2: Parse Stellarium Data ---

def parse_constellationship(fab_path: Path) -> Dict[str, List[Tuple[int, int]]]:
    """
    Parse constellationship.fab and extract line segments.
    
    Args:
        fab_path: Path to constellationship.fab file
        
    Returns:
        Dict mapping IAU code to list of (HIP_A, HIP_B) tuples
    """
    constellations = {}
    
    with open(fab_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
                
            parts = line.split()
            if len(parts) < 3:
                print(f"WARNING: Malformed line: {line}", file=sys.stderr)
                continue
                
            iau_code = parts[0]
            
            # Only process target constellations
            if iau_code not in REQUIRED_IAU:
                continue
                
            try:
                segment_count = int(parts[1])
                hip_ids = [int(x) for x in parts[2:]]
            except ValueError as e:
                print(f"WARNING: Invalid data in line for {iau_code}: {e}", file=sys.stderr)
                continue
            
            # Extract pairs of consecutive HIP IDs as line segments
            segments = []
            for i in range(0, len(hip_ids), 2):
                if i + 1 < len(hip_ids):
                    segments.append((hip_ids[i], hip_ids[i + 1]))
            
            if len(segments) != segment_count:
                print(f"WARNING: {iau_code} declares {segment_count} segments but has {len(segments)}", 
                      file=sys.stderr)
            
            constellations[iau_code] = segments
            
    return constellations


# --- Step 2: Load HYG Catalog ---

def load_hyg_catalog(csv_path: Path) -> Dict[int, Tuple[float, float]]:
    """
    Load HYG catalog and build HIP ID to (RA, Dec) mapping.
    
    Args:
        csv_path: Path to hyg_v38.csv file
        
    Returns:
        Dict mapping HIP ID to (ra_deg, dec_deg)
    """
    catalog = {}
    
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        
        for row in reader:
            hip_str = row.get('hip', '').strip()
            if not hip_str:
                continue
                
            try:
                hip_id = int(hip_str)
                ra_hours = float(row['ra'])
                dec_deg = float(row['dec'])
                
                # Convert RA from decimal hours to degrees
                ra_deg = ra_hours * 15.0
                
                # Validate ranges
                if not (0 <= ra_deg < 360):
                    print(f"WARNING: HIP {hip_id} has RA out of range: {ra_deg}", file=sys.stderr)
                    continue
                if not (-90 <= dec_deg <= 90):
                    print(f"WARNING: HIP {hip_id} has Dec out of range: {dec_deg}", file=sys.stderr)
                    continue
                    
                catalog[hip_id] = (ra_deg, dec_deg)
                
            except (ValueError, KeyError) as e:
                print(f"WARNING: Error parsing row for HIP {hip_str}: {e}", file=sys.stderr)
                continue
    
    return catalog


# --- Step 3: Cross-Validation ---

def load_bright_stars(json_path: Path) -> Dict[str, Tuple[float, float]]:
    """
    Load bright stars JSON and create name to (RA, Dec) mapping.
    
    Args:
        json_path: Path to bright-stars.json
        
    Returns:
        Dict mapping star name to (ra_deg, dec_deg)
    """
    with open(json_path, 'r', encoding='utf-8') as f:
        stars = json.load(f)
    
    return {star['name']: (star['ra_deg'], star['dec_deg']) for star in stars}


def validate_coordinates(hyg_catalog: Dict[int, Tuple[float, float]], 
                        bright_stars: Dict[str, Tuple[float, float]]) -> bool:
    """
    Validate that HYG catalog coordinates match bright-stars.json within tolerance.
    
    Args:
        hyg_catalog: HIP ID to (RA, Dec) mapping from HYG
        bright_stars: Star name to (RA, Dec) mapping from bright-stars.json
        
    Returns:
        True if all validation passed, False otherwise
    """
    tolerance = 0.1  # degrees
    errors = []
    
    for hip_id, star_name in HIP_TO_NAME.items():
        if hip_id not in hyg_catalog:
            print(f"WARNING: HIP {hip_id} ({star_name}) not found in HYG catalog", file=sys.stderr)
            continue
            
        if star_name not in bright_stars:
            # Not all constellation stars are in the bright-stars.json
            continue
        
        hyg_ra, hyg_dec = hyg_catalog[hip_id]
        ref_ra, ref_dec = bright_stars[star_name]
        
        # Calculate differences
        ra_diff = abs(hyg_ra - ref_ra)
        # Handle RA wraparound at 0/360
        if ra_diff > 180:
            ra_diff = 360 - ra_diff
            
        dec_diff = abs(hyg_dec - ref_dec)
        
        if ra_diff > tolerance or dec_diff > tolerance:
            errors.append(
                f"HIP {hip_id} ({star_name}): "
                f"HYG=({hyg_ra:.3f}, {hyg_dec:.3f}) "
                f"vs bright-stars=({ref_ra:.3f}, {ref_dec:.3f}) "
                f"diff=({ra_diff:.3f}, {dec_diff:.3f})"
            )
    
    if errors:
        print("\nERROR: Coordinate validation failed:", file=sys.stderr)
        for error in errors:
            print(f"  {error}", file=sys.stderr)
        return False
    
    return True


# --- Step 5: JSON Generation ---

def build_constellations_json(constellations: Dict[str, List[Tuple[int, int]]],
                             hyg_catalog: Dict[int, Tuple[float, float]],
                             output_path: Path) -> bool:
    """
    Build constellations.json from parsed data.
    
    Args:
        constellations: IAU code to list of HIP ID pairs
        hyg_catalog: HIP ID to (RA, Dec) mapping
        output_path: Path to write JSON file
        
    Returns:
        True if successful, False otherwise
    """
    result = []
    skipped_segments = 0
    
    for iau_code in REQUIRED_IAU:
        if iau_code not in constellations:
            print(f"WARNING: Constellation {iau_code} not found in .fab file", file=sys.stderr)
            # Include with empty lines array
            result.append({
                "iau": iau_code,
                "name": IAU_TO_NAME[iau_code],
                "lines": []
            })
            continue
        
        lines = []
        segments = constellations[iau_code]
        
        for hip_a, hip_b in segments:
            if hip_a not in hyg_catalog:
                print(f"WARNING: {iau_code}: HIP {hip_a} not in catalog, skipping segment", 
                      file=sys.stderr)
                skipped_segments += 1
                continue
            if hip_b not in hyg_catalog:
                print(f"WARNING: {iau_code}: HIP {hip_b} not in catalog, skipping segment", 
                      file=sys.stderr)
                skipped_segments += 1
                continue
            
            ra1, dec1 = hyg_catalog[hip_a]
            ra2, dec2 = hyg_catalog[hip_b]
            
            # Round to 3 decimal places
            lines.append([
                round(ra1, 3),
                round(dec1, 3),
                round(ra2, 3),
                round(dec2, 3)
            ])
        
        if not lines:
            print(f"WARNING: {iau_code} has zero line segments after filtering", file=sys.stderr)
        
        result.append({
            "iau": iau_code,
            "name": IAU_TO_NAME[iau_code],
            "lines": lines
        })
    
    # Validate output schema
    if len(result) != len(REQUIRED_IAU):
        print(f"ERROR: Expected {len(REQUIRED_IAU)} constellations, got {len(result)}", 
              file=sys.stderr)
        return False
    
    found_iau = {c["iau"] for c in result}
    missing_iau = set(REQUIRED_IAU) - found_iau
    if missing_iau:
        print(f"ERROR: Missing IAU codes in output: {missing_iau}", file=sys.stderr)
        return False
    
    # Validate coordinate ranges
    for constellation in result:
        for line in constellation["lines"]:
            if len(line) != 4:
                print(f"ERROR: {constellation['iau']} has line with {len(line)} values", 
                      file=sys.stderr)
                return False
            ra1, dec1, ra2, dec2 = line
            if not (0 <= ra1 < 360 and 0 <= ra2 < 360):
                print(f"ERROR: {constellation['iau']} has RA out of range", file=sys.stderr)
                return False
            if not (-90 <= dec1 <= 90 and -90 <= dec2 <= 90):
                print(f"ERROR: {constellation['iau']} has Dec out of range", file=sys.stderr)
                return False
    
    # Write JSON
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(result, f, indent=2)
    
    total_segments = sum(len(c["lines"]) for c in result)
    print(f"\nSUCCESS: Generated {len(result)} constellations, {total_segments} line segments")
    if skipped_segments > 0:
        print(f"  (skipped {skipped_segments} segments due to missing HIP IDs)")
    
    return True


# --- Main ---

def main() -> int:
    """Main entry point."""
    # Determine paths
    script_dir = Path(__file__).parent
    repo_root = script_dir.parent
    
    fab_path = script_dir / "data" / "constellationship.fab"
    hyg_path = script_dir / "data" / "hyg_v38.csv"
    bright_stars_path = repo_root / "frontend" / "data" / "bright-stars.json"
    output_path = repo_root / "frontend" / "data" / "constellations.json"
    
    # Check input files exist
    if not fab_path.exists():
        print(f"ERROR: {fab_path} not found", file=sys.stderr)
        return 1
    if not hyg_path.exists():
        print(f"ERROR: {hyg_path} not found", file=sys.stderr)
        return 1
    if not bright_stars_path.exists():
        print(f"ERROR: {bright_stars_path} not found", file=sys.stderr)
        return 1
    
    # Step 2: Parse constellation data and load catalog
    print("Parsing constellation data...")
    constellations = parse_constellationship(fab_path)
    print(f"  Loaded {len(constellations)} target constellations")
    
    print("\nLoading HYG catalog...")
    hyg_catalog = load_hyg_catalog(hyg_path)
    print(f"  Loaded {len(hyg_catalog)} stars from HYG database")
    
    # Step 3: Cross-validation
    print("\nValidating coordinates against bright-stars.json...")
    bright_stars = load_bright_stars(bright_stars_path)
    if not validate_coordinates(hyg_catalog, bright_stars):
        print("\nERROR: Validation failed", file=sys.stderr)
        return 1
    print("  Validation passed")
    
    # Step 5: Generate JSON
    print("\nGenerating constellations.json...")
    if not build_constellations_json(constellations, hyg_catalog, output_path):
        return 1
    
    print(f"\nOutput written to: {output_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
