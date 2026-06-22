# 10 — Iowa Cross-Season Mismatch

## Location
Story County, Iowa, USA. ~41.82N, -93.62W. Same area as 06.

## Change description
Same field in summer vs. winter. Huge NDVI drop from growing season to
dormant season. This is entirely seasonal, not deforestation or disturbance.

## Source of truth
- USDA Cropland Data Layer
- Known crop calendar (corn/soy: planted Apr-May, senescence Oct-Nov)

## Expected behavior
Pipeline should ABSTAIN recognizing cross-season comparison.
Large NDVI delta (-0.10 to -0.50) but this is crop senescence, not change.
This tests the pipeline's ability to distinguish seasonal from real change.
If the pipeline reports findings, they are false positives.

## Reviewer
Farzin Shifat
## Date
2026-06-22
