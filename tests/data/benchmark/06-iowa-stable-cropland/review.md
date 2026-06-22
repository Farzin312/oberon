# 06 — Iowa Stable Cropland

## Location
Story County, Iowa, USA. ~41.82N, -93.62W.
Established corn/soy rotation farmland.

## Change description
No significant land-cover change expected within the same growing season.
Crop growth occurs but field boundaries and overall vegetation pattern stable.

## Source of truth
- USDA Cropland Data Layer
- Sentinel-2 visual inspection

## Expected behavior
Zero findings expected (finding_count min=0, max=0).
NDVI may shift due to crop growth cycle but should not trigger change detection
within the same season. Small NDVI range (-0.10 to +0.10).
This is the FP-control for temperate cropland.

## Reviewer
Farzin Shifat
## Date
2026-06-22
