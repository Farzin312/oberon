# 002 — Baseline Fixes + Task Contract

**Parent**: [../README.md](../README.md)

Close out Week 3 of the Product Brief by completing pixel_delta (the last missing deterministic baseline metric) and write the formal task contract per Roadmap PDF Phase 1. Also wraps 001 Phase 7 cleanup.

- **Weeks:** Product Brief Week 3 (gap close-out)
- **Reference:** Roadmap PDF lines 411-449 (Phase 1), 477-510 (Phase 3)
- **Prerequisite:** 001-data-plane-pipeline complete

> **Hard rules:**
> 1. The task contract must be written before any code changes.
> 2. pixel_delta is NOT the primary ranking signal; NDVI stays primary.
> 3. No new dependencies.

---

## Locked decisions

| # | Decision | Choice |
|---|----------|--------|
| 1 | First task | `vegetation_disturbance` — NDVI loss >= 0.15 over >= 0.5 ha |
| 2 | pixel_delta | Euclidean magnitude across all matching bands |
| 3 | Ranking formula | `max(ndvi_score, delta_score * 0.3)` — NDVI stays primary |
| 4 | Task contract location | `docs/TASK_CONTRACT.md` |

---

## In scope vs NOT in scope

### IN SCOPE
- `compute_pixel_delta` function in baselines.py
- Wire through compute_baselines, change_detection, artifacts
- docs/TASK_CONTRACT.md
- 001 Phase 7 cleanup: DRY sweep, docs sync, squash decision

### NOT in scope
- Clay integration (003)
- Benchmark dataset (004)
- Docker (007)
- Rust (008)

---

## Risk warnings

- pixel_delta across all bands includes seasonal variation in non-vegetation bands (e.g., moisture in SWIR). The 0.3 weight caps its influence.
- The 0.5 ha minimum area is a starting default; 004-benchmark-dataset is where it gets calibrated.
