# API Contract Gap Analysis: EvidenceBundle vs Product Brief POST /v1/change

**Parent**: [../../README.md](../../README.md)

**Created**: 2026-06-22 (006 Phase 4)

This document compares the current Oberon `EvidenceBundle` output shape against the
target API contract defined in the Product Brief (§5, lines 314-341). It records each
gap and its remediation path.

## Target response shape (Product Brief §5)

```json
{
  "status": "review_recommended" | "abstained" | "failed",
  "findings": [
    {
      "geometry": "...",
      "change_score": 0.0-1.0,
      "suggested_class": "deforestation" | "fire" | ...,
      "changed_area_m2": 1234.5,
      "evidence": {
        "ndvi_delta": -0.3,
        "nbr_delta": -0.2
      },
      "model": {
        "encoder": "clay-v1.5",
        "confidence": null
      }
    }
  ],
  "artifacts": {
    "before": "url",
    "after": "url",
    "overlay": "url"
  }
}
```

## Current EvidenceBundle shape

```json
{
  "output_dir": "path/",
  "before_image": "path/before.png",
  "after_image": "path/after.png",
  "overlay_image": "path/overlay.png",
  "findings_geojson": "path/findings.geojson",
  "provenance_manifest": "path/provenance.json",
  "provenance": {
    "oberon_version": "0.1.0",
    "model_versions": ["deterministic-v1"],
    "artifacts": {...},
    "findings": [
      {"id": 1, "score": 0.72, "area_ha": 2.3, "metrics": {"ndvi_delta_mean": -0.32, ...}}
    ],
    "software": {...}
  }
}
```

## Gap table

| # | Product Brief field | Current state | Gap | Fix target |
|---|---------------------|---------------|-----|------------|
| 1 | `status` | Missing entirely | No top-level status field. CLI infers from abstention vs findings. | Add status field to response shape in 008 (Rust control plane) |
| 2 | `findings[].change_score` | `Finding.score` exists | Field renamed: `score` vs `change_score` | Rename in API serialization layer (008) |
| 3 | `findings[].suggested_class` | Not present | No task head — Clay is encoder-only. Classification deferred to post-pilot. | Document as known limitation; add when task head is trained |
| 4 | `findings[].changed_area_m2` | `Finding.area_ha` exists | Unit mismatch: hectares vs square meters. 1 ha = 10,000 m2. | Convert in serialization layer (008) |
| 5 | `findings[].evidence.ndvi_delta` | `Finding.ndvi_delta_mean` exists | Field renamed and nested differently. | Restructure in serialization (008) |
| 6 | `findings[].model.encoder` | `provenance.model_versions` (run-level) | Model version is run-level, not per-finding. Acceptable for now — all findings in a run use the same models. | Add per-finding model field in 008 if mixed-model runs become possible |
| 7 | `findings[].model.confidence` | Not present | Clay feature diff is NOT confidence (uncalibrated). Correctly excluded. | Add calibrated confidence post-pilot |
| 8 | `artifacts.before/after/overlay` | `bundle.before_image` etc. | Paths are local, not URLs. Need upload + URL generation for API. | Add artifact URL resolver in 008 |
| 9 | `model_versions` (provenance) | Added in 006 Phase 2 | Present in provenance, not in top-level response. | Surface in API response (008) |
| 10 | `artifact_index.json` | Added in 006 Phase 1 | Per-run index with checksums exists. Not exposed in API response. | Include in API response or reference by run_id (008) |

## Remediation summary

**Fixed in Python pre-work (008 Phase 1, done 2026-06-22)**: gaps 1, 2, 4, 5, 6,
8, 9, 10 — resolved by `src/oberon/api/contracts.py` (Pydantic v2 models) +
`src/oberon/api/serialization.py` (serialization layer). 26 tests in
`tests/api/test_contracts.py` verify the full Product Brief §5 shape.

**Fix in Rust control plane (008 Phases 2-7, deferred)**: Rust Axum server will
use these same contract shapes via serde, spawn the Python pipeline via
subprocess, and serve the serialized ChangeResponse via HTTP.

**Fix post-pilot**: gaps 3, 7 — these require a trained task head and calibrated
confidence scores, which are explicitly deferred.

## --json CLI flag (006 Phase 4)

The `--json` flag on `oberon analyze` produces a JSON summary on stdout:

```json
{
  "status": "complete",
  "finding_count": 3,
  "model_versions": ["deterministic-v1"],
  "artifacts": {...},
  "output_dir": "path/"
}
```

This is NOT the final API response shape — it is a CLI convenience output. The full
API response shape will be implemented in 008.
