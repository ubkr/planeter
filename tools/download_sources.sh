#!/usr/bin/env bash
set -euo pipefail

################################################################################
# Constellation Source Data Downloader
#
# Purpose:
#   Downloads required source data files for constellation line reconstruction:
#   - HYG Database v3.8 (star catalog with HIP IDs, positions, magnitudes)
#   - Stellarium constellationship.fab (constellation line definitions)
#
# When to run:
#   Run this script once before executing build_constellations.py
#   Re-run if source data needs to be refreshed
#
# Output files created in tools/data/:
#   - hyg_v38.csv (decompressed star catalog, ~7 MB)
#   - constellationship.fab (constellation HIP ID pairs, ~5 KB)
#
# Usage:
#   ./tools/download_sources.sh
################################################################################

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DATA_DIR="${SCRIPT_DIR}/data"

echo "=== Constellation Source Data Downloader ==="
echo

# Create data directory if it doesn't exist
mkdir -p "${DATA_DIR}"
echo "✓ Data directory: ${DATA_DIR}"
echo

# Utility function: Get file size in bytes (cross-platform)
get_file_size() {
    local file="$1"
    if [[ "$OSTYPE" == "darwin"* ]]; then
        stat -f%z "$file"
    else
        stat -c%s "$file"
    fi
}

# Utility function: Download a file using curl or wget
download_file() {
    local output_file="$1"
    local url="$2"
    
    if command -v curl &> /dev/null; then
        curl -L -o "${output_file}" "${url}"
    elif command -v wget &> /dev/null; then
        wget -O "${output_file}" "${url}"
    else
        echo "✗ ERROR: Neither curl nor wget found. Install one to continue."
        exit 1
    fi
}

# Check for download tool availability
if command -v curl &> /dev/null; then
    echo "✓ Using curl for downloads"
elif command -v wget &> /dev/null; then
    echo "✓ Using wget for downloads"
else
    echo "✗ ERROR: Neither curl nor wget found. Install one to continue."
    exit 1
fi
echo

# Download 1: HYG Database v3.8
echo "--- Downloading HYG Database v3.8 ---"
HYG_URL="https://raw.githubusercontent.com/astronexus/HYG-Database/master/hyg/v3/hyg_v38.csv.gz"
HYG_GZ_FILE="${DATA_DIR}/hyg_v38.csv.gz"
HYG_FILE="${DATA_DIR}/hyg_v38.csv"

if download_file "${HYG_GZ_FILE}" "${HYG_URL}"; then
    echo "✓ Downloaded hyg_v38.csv.gz"
    
    # Decompress the file
    if gunzip -f "${HYG_GZ_FILE}"; then
        echo "✓ Decompressed to hyg_v38.csv"
    else
        echo "✗ ERROR: Failed to decompress hyg_v38.csv.gz"
        exit 1
    fi
    
    # Validate file size (decompressed should be 30-35 MB)
    FILE_SIZE=$(get_file_size "${HYG_FILE}")
    if [ "${FILE_SIZE}" -lt 30000000 ] || [ "${FILE_SIZE}" -gt 35000000 ]; then
        echo "✗ ERROR: hyg_v38.csv file size out of expected range (${FILE_SIZE} bytes, expected 30-35 MB)"
        exit 1
    fi
    echo "  File size: $(numfmt --to=iec-i --suffix=B ${FILE_SIZE} 2>/dev/null || echo "${FILE_SIZE} bytes")"
    
    # Validate CSV header contains required columns (exact match with word boundaries)
    HEADER=$(head -n 1 "${HYG_FILE}")
    if ! echo "${HEADER}" | grep -qE '(^|,)"?hip"?(,|$)' || \
       ! echo "${HEADER}" | grep -qE '(^|,)"?ra"?(,|$)' || \
       ! echo "${HEADER}" | grep -qE '(^|,)"?dec"?(,|$)'; then
        echo "✗ ERROR: hyg_v38.csv missing required columns (hip, ra, dec)"
        echo "  Header: ${HEADER}"
        exit 1
    fi
    echo "  ✓ Header validation passed (contains hip, ra, dec)"
else
    echo "✗ ERROR: Failed to download hyg_v38.csv.gz"
    exit 1
fi
echo

# Download 2: Stellarium constellation data
echo "--- Downloading Stellarium constellation data ---"
CONSTELLATION_URL="https://raw.githubusercontent.com/Stellarium/stellarium/v24.4/skycultures/modern/constellationship.fab"
CONSTELLATION_FILE="${DATA_DIR}/constellationship.fab"

if download_file "${CONSTELLATION_FILE}" "${CONSTELLATION_URL}"; then
    echo "✓ Downloaded constellationship.fab"
    
    # Validate file size (should be 8-10 KB)
    FILE_SIZE=$(get_file_size "${CONSTELLATION_FILE}")
    if [ "${FILE_SIZE}" -lt 8000 ] || [ "${FILE_SIZE}" -gt 10000 ]; then
        echo "✗ ERROR: constellationship.fab file size out of expected range (${FILE_SIZE} bytes, expected 8-10 KB)"
        exit 1
    fi
    echo "  File size: ${FILE_SIZE} bytes"
    
    # Validate file contains constellation line data (HIP ID pairs for Orion)
    if ! grep -q "Ori " "${CONSTELLATION_FILE}"; then
        echo "✗ ERROR: constellationship.fab missing expected constellation data (Ori pattern)"
        exit 1
    fi
    echo "  ✓ Content validation passed (contains constellation line data)"
else
    echo "✗ ERROR: Failed to download constellationship.fab"
    exit 1
fi
echo

echo "=== All downloads completed successfully ==="
echo "Files ready in: ${DATA_DIR}/"
echo "  • hyg_v38.csv"
echo "  • constellationship.fab"
