# 07 — Temperate Forest Seasonal Variation

## Location
Bavaria, Germany. ~50.02N, 9.02E. Temperate deciduous forest.

## Change description
Natural seasonal leaf senescence (summer to autumn).
This is NOT deforestation — it is the normal phenological cycle.

## Source of truth
- Copernicus High Resolution Layer (Forest)
- Sentinel-2 visual inspection
- Known phenological calendar for Central European deciduous forest

## Expected behavior
Pipeline should detect NDVI drop from canopy green-up to senescence.
This is a known false-positive risk — seasonal changes should ideally
lead to abstention or be distinguishable from real disturbance.
Expected outcome: abstention with seasonal reason, OR findings that
are clearly attributable to phenology, not deforestation.

## Reviewer
Farzin Shifat
## Date
2026-06-22
