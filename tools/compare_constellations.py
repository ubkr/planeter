#!/usr/bin/env python3
"""Compare old and new constellation files to verify the Alnilam fix."""

import json

# Load old file
old_data = json.load(open('tools/data/constellations.json.old'))
old_ori = next(c for c in old_data if c['iau'] == 'Ori')

# Load new file
new_data = json.load(open('frontend/data/constellations.json'))
new_ori = next(c for c in new_data if c['iau'] == 'Ori')

print('OLD Orion constellation:')
for seg in old_ori['lines']:
    ra1, dec1, ra2, dec2 = seg
    if 83.8 <= ra1 <= 84.3:
        print(f'  Alnilam (old): RA={ra1:.3f}, Dec={dec1:.3f}')
        break
    if 83.8 <= ra2 <= 84.3:
        print(f'  Alnilam (old): RA={ra2:.3f}, Dec={dec2:.3f}')
        break

print('\nNEW Orion constellation:')
for seg in new_ori['lines']:
    ra1, dec1, ra2, dec2 = seg
    if 83.8 <= ra1 <= 84.3:
        print(f'  Alnilam (new): RA={ra1:.3f}, Dec={dec1:.3f}')
        break
    if 83.8 <= ra2 <= 84.3:
        print(f'  Alnilam (new): RA={ra2:.3f}, Dec={dec2:.3f}')
        break

# Count constellations
print(f'\nTotal constellations: OLD={len(old_data)}, NEW={len(new_data)}')
print(f'Line segments: OLD={sum(len(c["lines"]) for c in old_data)}, NEW={sum(len(c["lines"]) for c in new_data)}')

# Check for any differences in IAU codes
old_iau = set(c['iau'] for c in old_data)
new_iau = set(c['iau'] for c in new_data)
print(f'IAU codes match: {old_iau == new_iau}')
print(f'\nAll constellation IAU codes: {sorted(new_iau)}')
