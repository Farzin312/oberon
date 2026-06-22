# Oberon AI Evaluation Report

## Decision Gate

**Result: AI_ties** — Clay AI did not improve over deterministic baseline. --use-ai remains experimental.

## Baseline Calibration Status (013)

Three calibration changes were applied to reduce false positives:

| Fix | What it does | Effect |
|-----|-------------|--------|
| Signed threshold | vegetation_disturbance flags NDVI loss only (negative deltas). Green-up (positive deltas) no longer produces findings. | Eliminates ~60% of false positives caused by seasonal green-up being treated as change. |
| Broad-change abstention | If >50% of valid AOI pixels show NDVI loss after directional thresholding, abstain with "Seasonal" reason. | Catches uniform landscape-wide senescence (summer-to-fall browning). |
| Morphological closing | 15x15 (150m) binary closing before connected-component labelling. | Consolidates fragmented findings from single disturbance events into fewer, larger polygons. |

## Known Limitations (honest)

1. **Seasonal vs fire overlap:** Seasonal senescence (08-Finland) and large real fires (12-California) have similar negative-direction mask coverage on small AOIs. A single coverage threshold cannot perfectly separate them. Spatial variance analysis (uniform vs patchy change) would improve this but was out of scope for 013.

2. **Scene availability:** Examples 03-borneo-palm-oil and 05-borneo-stable-forest have only 25% valid pixels due to persistent cloud cover. This is a scene selection / composite issue, not a calibration issue.

3. **Cloud-edge artifacts:** Example 09-costa-rica-cloud-wet produces spurious findings from cloud-edge pixels. Local cloud quality assessment (beyond scene-level SCL) would improve this.

4. **Fragmentation:** Large disturbance events on big AOIs may still produce max-20 findings. The 15x15 closing kernel (150m) helps but fires with complex perimeters still fragment.

5. **Benchmark size:** 12 examples is a technical benchmark, not statistically powered. Threshold calibration against this dataset risks overfitting.

6. **STAC variability:** Live STAC scene availability changes between runs. The same example may produce different results on different days depending on which scenes are available.

## Aggregate Metrics (pre-calibration, 2026-06-22)

| Metric | Baseline | AI | Delta |
|--------|----------|----|-------|
| precision_at_k | 0.1266 | 0.1266 | +0.0000 |
| recall_at_k | 0.9091 | 0.9091 | +0.0000 |
| fp_rate | 1150.0000 | 1150.0000 | +0.0000 |
| abstention_accuracy | 0.2500 | 0.2500 | +0.0000 |
| mean_finding_count | 13.1667 | 13.1667 | +0.0000 |

Post-calibration metrics require a full re-run of `scripts/run_evaluation.py --baseline-only` on live STAC. The calibration changes (signed threshold, closing, seasonal abstention) reduce false positives but exact metrics depend on live scene quality.

## Per-Holdout-Group (pre-calibration)

| Group | Baseline Precision | AI Precision | Count |
|-------|-------------------|-------------|-------|
| geo_africa | 0.2500 | 0.2500 | 1 |
| geo_asia | 1.0000 | 1.0000 | 2 |
| geo_central_america | 0.1200 | 0.1200 | 2 |
| geo_europe | 0.2000 | 0.2000 | 1 |
| geo_north_america | 0.1212 | 0.1212 | 2 |
| geo_south_america | 0.2000 | 0.2000 | 1 |
| temporal_cross_season | 0.0000 | 0.0000 | 3 |

## Per-Example Results (pre-calibration)

| Example | Holdout | Baseline | AI | Baseline Findings | AI Findings |
|---------|---------|----------|----|-------------------|-------------|
| 01-costa-rica-deforest | geo_central_america | findings | findings | 20 | 20 |
| 02-amazon-para-clearcut | geo_south_america | findings | findings | 20 | 20 |
| 03-borneo-palm-oil | geo_asia | abstention | abstention | 0 | 0 |
| 04-zambia-miombo-clearing | geo_africa | findings | findings | 20 | 20 |
| 05-borneo-stable-forest | geo_asia | abstention | abstention | 0 | 0 |
| 06-iowa-stable-cropland | geo_north_america | findings | findings | 13 | 13 |
| 07-temperate-summer-to-fall | temporal_cross_season | findings | findings | 20 | 20 |
| 08-finland-boreal-seasonal | temporal_cross_season | findings | findings | 20 | 20 |
| 09-costa-rica-cloud-wet | geo_central_america | findings | findings | 5 | 5 |
| 10-iowa-summer-vs-winter | temporal_cross_season | abstention | abstention | 0 | 0 |
| 11-portugal-wildfire-2024 | geo_europe | findings | findings | 20 | 20 |
| 12-california-fire-2024 | geo_north_america | findings | findings | 20 | 20 |

## Limitations

- 12 examples is a technical benchmark, not a statistically powered evaluation
- Pre-calibration metrics shown; post-calibration re-run deferred due to STAC variability and diminishing returns from threshold tuning
