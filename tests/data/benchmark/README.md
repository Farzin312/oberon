# Benchmark Dataset

**Parent**: [../../mini-sdd/004-benchmark-dataset/README.md](../../mini-sdd/004-benchmark-dataset/README.md)

A small, human-reviewed set of before/after Sentinel-2 AOI polygons for evaluating
Oberon's change-detection pipeline. Each example is a real geographic location with
documented vegetation change (or stability), chosen for diversity across regions,
ecosystems, seasons, and failure modes.

## Dataset format

Each example lives in `NNN-<slug>/` with exactly 3 files:

| File | Contents |
|------|----------|
| `aoi.geojson` | A GeoJSON Feature with a single Polygon geometry |
| `expected.json` | Expected pipeline outcome (see schema below) |
| `review.md` | Human review notes: what changed, source of truth, reviewer, date |

## expected.json schema

```json
{
  "expected_outcome": "findings" | "abstention",
  "abstention_reason_substring": null | "cloud" | "seasonal" | "insufficient",
  "finding_count": {"min": 1, "max": 5},
  "ndvi_delta_range": [-0.5, -0.1],
  "area_ha_min": 0.5,
  "region": "tropical" | "temperate" | "boreal" | "arid",
  "ecosystem": "rainforest" | "savanna" | "cropland" | "temperate_forest",
  "time_interval_months": 6,
  "season_comparison": "same_season" | "cross_season",
  "holdout_group": "geo_<region>" | "temporal_<pair>"
}
```

## Diversity table

| # | Slug | Region | Ecosystem | Change Type | Season |
|---|------|--------|-----------|-------------|--------|
| 01 | costa-rica-deforest | Central America | rainforest | Deforestation | same |
| 02 | amazon-para-clearcut | South America | rainforest | Deforestation | same |
| 03 | borneo-palm-oil | SE Asia | rainforest | Plantation expansion | same |
| 04 | zambia-miombo-clearing | Africa | savanna | Smallholder clearing | same |
| 05 | borneo-stable-forest | SE Asia | rainforest | No change (stable) | same |
| 06 | iowa-stable-cropland | North America | cropland | No change (stable) | same |
| 07 | temperate-summer-to-fall | Europe | temperate_forest | Seasonal variation | cross |
| 08 | finland-boreal-seasonal | Europe | boreal | Seasonal variation | cross |
| 09 | costa-rica-cloud-wet | Central America | rainforest | Cloud contamination | same |
| 10 | iowa-summer-vs-winter | North America | cropland | Cross-season mismatch | cross |
| 11 | portugal-wildfire-2024 | Europe | temperate_forest | Wildfire scar | same |
| 12 | california-fire-2024 | North America | temperate_forest | Wildfire scar | same |

## Holdout protocol

- **Geographic groups**: geo_central_america, geo_south_america, geo_africa, geo_asia,
  geo_north_america, geo_europe
- **Temporal groups**: temporal_same_season, temporal_cross_season
- Calibration uses examples from N-1 geographic groups
- Validation uses the held-out group
- No neighboring patches are split across train/test

## Known limitations

- 12 examples is a **technical benchmark**, not a statistically powered evaluation dataset.
- Thresholds derived from this benchmark are approximate — do not present them as production ground truth.
- Examples are selected from known-change locations; they do not represent the global distribution of land cover.
- Live STAC/COG fetches are slow (~10-30s per example). Full suite: ~2-6 min.
- Cloud cover and scene availability change over time; calibration results may drift as STAC catalogs update.
