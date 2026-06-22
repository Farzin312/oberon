# Task Contract — vegetation_disturbance

**Parent**: [README.md](../README.md)
**Source**: Roadmap PDF Phase 1 (lines 411-449), Product Brief v3
**Mini-SDD**: [002-baseline-fixes](mini-sdd/002-baseline-fixes/README.md)

---

## 1. Task definition

| Field | Value |
|-------|-------|
| Task ID | `vegetation_disturbance` |
| Output type | Ranking + segmentation (connected-component polygons) |
| Primary signal | NDVI loss (Normalized Difference Vegetation Index) |
| Secondary signal | pixel_delta (Euclidean band magnitude), weighted 0.3 |

The system claims to detect **material vegetation disturbance** within a defined area of interest (AOI) between two time windows. "Disturbance" means loss of photosynthetic vegetation cover — deforestation, land clearing, fire, logging, or die-back. It does NOT mean seasonal variation, agricultural rotation, or recovery/regrowth.

---

## 2. Positive example

A finding is a **positive** when ALL of the following hold:

- NDVI loss (after - before) >= 0.15 within the finding polygon
- Finding polygon covers >= 0.5 ha (>= 50 contiguous 10m pixels)
- The loss occurs within the valid-pixel area (both observations have clear, unmasked pixels over the finding)

**Why 0.15 NDVI:** this is a starting threshold calibrated against published disturbance-detection literature for Sentinel-2. It is intentionally conservative — it misses subtle degradation but avoids seasonal-noise false positives. Calibration against 004-benchmark-dataset may adjust this.

---

## 3. Negative example

A finding is a **negative** (should not be reported) when ANY of the following hold:

- |NDVI change| < 0.10 (below detection threshold — noise floor)
- Finding area < 0.25 ha (< 25 contiguous pixels — too small to distinguish from co-registration noise)
- The change is explainable by seasonal variation alone (same vegetation type, same phenological phase, no structural change in other bands)

---

## 4. Minimum area

| Parameter | Value | Pixels (10m) | Rationale |
|-----------|-------|-------------|-----------|
| Minimum finding area | 0.5 ha | ~50 pixels | Large enough to survive co-registration noise; matches `ChangeRequest.min_change_area_ha` and `_MIN_CHANGE_PIXELS` |
| Negative floor | 0.25 ha | ~25 pixels | Below this, single-pixel misalignment artifacts dominate |

Constant: `_MIN_CHANGE_PIXELS = 50` in `change_detection.py`, `_PIXEL_AREA_HA = 0.01`.

---

## 5. Abstention triggers

The pipeline MUST abstain (return exit 0, empty findings, `"Abstained:"` prefix) rather than produce a low-confidence result when:

| Trigger | Threshold | Source |
|---------|-----------|--------|
| Cloud cover over AOI | > 50% of AOI pixels masked as cloud/shadow/snow/ice | `max_cloud_fraction` / SCL mask |
| Valid pixels in AOI | < 30% valid in both before AND after | `PreparedPair.is_usable` (0.30 threshold) |
| Missing required bands | B04 or B08 absent from either observation | `compute_baselines` abstain path |
| Seasonal mismatch | Flagged by user (not yet automated) | `ChangeRequest` — future: auto-detect via phenological phase comparison |

Abstention is a valid analysis result, not an error. Exit code 0.

---

## 6. Ranking formula

```
ndvi_score = min(abs(ndvi_delta_mean) / 0.5, 1.0)
delta_score = min(pixel_delta_mean / 5000.0, 1.0)
score = max(ndvi_score, delta_score * 0.3)
```

- NDVI is the **primary** ranking signal.
- pixel_delta (Euclidean magnitude across all matching bands) is a **secondary** signal capped at 0.3 weight. It can only promote a finding that NDVI alone would rank low — it cannot demote a strong NDVI finding.
- The 5000.0 normalization reflects typical Sentinel-2 reflectance scale (0-10000 range). Calibration in 004-benchmark-dataset.

---

## 7. Evidence requirements

Every reported finding must produce an `EvidenceBundle` containing:

| Artifact | Format | Contents |
|----------|--------|----------|
| Before image | PNG | True-color (B04/B03/B02) composite of the AOI before window |
| After image | PNG | True-color composite of the AOI after window |
| Change overlay | PNG | NDVI difference heatmap overlaid on the after image, finding polygons outlined |
| Findings GeoJSON | .geojson | FeatureCollection; each Feature has geometry + properties (score, area_ha, ndvi_delta_mean, nbr_delta_mean, pixel_delta_mean, valid_pixels_in_finding) |
| Provenance manifest | .json | Oberon version, source scene IDs, bands, processing config, software versions, artifact filenames, abstention status |

A human reviewer must be able to look at the before/after images + overlay and independently judge whether the finding is real. The provenance manifest must enable independent reproduction.

---

## 8. Acceptable date ranges

| Parameter | Default | Constraint |
|-----------|---------|-----------|
| Before window | 30-day lookback from `--before` date | Must contain at least one cloud-suitable scene |
| After window | Single day (or 30-day if `--after-start` set) | Must contain at least one cloud-suitable scene |
| Seasonal mismatch | Not yet auto-detected | User may flag; future: phenological phase comparison |

Both windows must yield a selected scene. If either window has no suitable observation, the pipeline abstains.

---

## 9. What this contract does NOT claim

- Not a **land cover classifier** — we detect change, not what the land cover is.
- Not a **fire severity model** — NBR is computed but not the primary signal. Burn-specific tasks are a future expansion.
- Not a **recovery detector** — recovery requires multi-temporal baselines and is harder to define. Disturbance (loss) is the tractable first claim.
- Not **calibrated** — thresholds (0.15 NDVI, 0.5 ha, 0.3 weight) are starting defaults from literature. 004-benchmark-dataset is where calibration happens.
- Not **real-time** — this is a batch analysis over two historical windows.

---

## 10. Contract parameters summary

| Parameter | Value | Constant / Field | Mini-SDD calibration |
|-----------|-------|-----------------|---------------------|
| NDVI loss threshold | 0.15 | `_DEFAULT_NDVI_THRESHOLD` | 004 |
| Minimum area | 0.5 ha (50 px) | `_MIN_CHANGE_PIXELS` / `min_change_area_ha` | 004 |
| pixel_delta weight | 0.3 | (Phase 2 ranking formula) | 004 |
| pixel_delta normalization | 5000.0 | (Phase 2 ranking formula) | 004 |
| Valid-pixel floor | 30% | `PreparedPair.is_usable` | stable |
| Cloud fraction max | 50% AOI | `max_cloud_fraction` (default 0.15 scene-level) | 004 |
| Max findings returned | 20 | `deduplicate_and_rank(max_findings=20)` | stable |
