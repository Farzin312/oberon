# 014 — Spatial-Variance Seasonal Detection

**Parent**: [../README.md](../README.md)

Addresses the #1 known limitation from 013-baseline-calibration: seasonal senescence and real fire produce similar negative-NDVI coverage on small AOIs. No coverage threshold can separate them (proven across 4 iterations in 013). This mini-SDD uses a different signal: **spatial pattern analysis**.

Seasonal senescence produces uniform, landscape-wide NDVI loss (low spatial variance in the change mask). Real disturbance (fire, clearing) produces patchy, concentrated change (high spatial variance). Computing the spatial variance of the change mask within the AOI distinguishes these two patterns.

- **Reference:** EVALUATION_REPORT.md Known Limitation #1, 013-baseline-calibration references
- **Prerequisite:** 013-baseline-calibration (DONE)

> **Hard rules:**
> 1. Deterministic-first. No ML for spatial pattern classification. Use a variance ratio heuristic.
> 2. Abstention over confident failure. If variance is ambiguous (neither clearly uniform nor clearly patchy), do NOT abstain — annotate the finding with a `seasonal_risk` flag instead. Only abstain when variance is decisively uniform AND coverage is high.
> 3. No new dependencies. NumPy/SciPy already provide everything needed.
> 4. Honest metrics. Golden tests must reflect real spatial patterns. Do not tune the threshold to force-pass examples.

---

## Locked decisions

| # | Decision | Choice |
|---|----------|--------|
| 1 | Metric | Coefficient of variation (CV) of per-pixel NDVI loss within the change mask. CV = std/mean of NDVI diff values where change_mask is True. |
| 2 | Uniform threshold | CV < 0.3 = uniform (likely seasonal). Patchy threshold: CV >= 0.3 = likely real disturbance. |
| 3 | Abstention condition | Abstain ONLY when: CV < 0.3 AND coverage > 50% of valid pixels. Both conditions required. |
| 4 | Annotation | When CV < 0.3 but coverage <= 50%, annotate findings with `seasonal_risk: true` in provenance. Do not abstain. |
| 5 | Scope | Applied after morphological closing, before connected-component extraction. Part of the orchestrator's Phase 3. |

---

## In scope vs NOT in scope

### IN SCOPE
- `compute_change_spatial_variance()` function in change_detection.py
- Seasonal abstention check in orchestrator (after closing, before extraction)
- `seasonal_risk` annotation in provenance processing_config
- Unit tests for variance computation and threshold logic
- Golden test expectation updates (honest — only where spatial variance genuinely changes the outcome)

### NOT in scope
- Multi-scale variance (wavelet decomposition) — future if single-scale CV is insufficient
- Land-use context (cropland vs forest) — that's a different signal entirely
- Machine learning classifier for spatial patterns — deterministic heuristic first

---

## Risk warnings

- The CV threshold (0.3) is an initial estimate from benchmark data. It may need tuning after live integration tests. Document the tuning process if it changes.
- Small AOIs (few pixels) produce unreliable variance statistics. The function must handle edge cases (all-same-value, single component) gracefully.
- Some real fires are large and relatively uniform (massive megafires). The coverage > 50% requirement prevents abstaining on these, but the CV alone might misclassify them. The dual-condition guard is essential.
