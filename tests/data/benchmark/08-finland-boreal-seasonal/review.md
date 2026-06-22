# 08 — Finland Boreal Seasonal

## Location
Ostrobothnia, Finland. ~64.02N, 26.02E. Boreal coniferous/mixed forest.

## Change description
Strong seasonal NDVI decline from summer peak to autumn/winter.
Boreal forests have large seasonal swings — snow and needle cast
both reduce NDVI sharply.

## Source of truth
- Copernicus High Resolution Layer
- Finnish Forest Centre data
- Known boreal phenology

## Expected behavior
Pipeline should abstain or flag this as seasonal, not deforestation.
Large NDVI drop (-0.10 to -0.35) but driven by phenology.
If pipeline reports findings, they are false positives from seasonality.

## Reviewer
Farzin Shifat
## Date
2026-06-22
