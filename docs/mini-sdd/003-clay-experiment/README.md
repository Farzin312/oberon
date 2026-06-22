# 003 — Clay Feature Extraction Experiment

**Parent**: [../README.md](../README.md)

Get Clay v1.5 running, extract features from before/after chips, produce a feature-diff change map on one real example. This is a focused technical experiment to answer the Week 4 decision gate: "Does the foundation model add signal?"

- **Reference:** Product Brief §3 (AI Integration), Roadmap PDF Phase 4
- **Prerequisite:** 002-baseline-fixes

> **Hard rules:**
> 1. Raw embedding distance is NOT confidence. It is a "change score" everywhere in code and docs.
> 2. Clay lives behind `ModelAdapter` protocol — no Clay imports leak into pipeline core.
> 3. This is a technical experiment, not a production integration. The decision gate decides if full evaluation (005) happens.
> 4. If torch/clay cannot be installed, the experiment reports that honestly and stops.

---

## Locked decisions

| # | Decision | Choice |
|---|----------|--------|
| 1 | Model version | Clay v1.5 (10-band, 256x256, 1024-dim embeddings) |
| 2 | Dependency model | torch + clay in `[ai]` extras; --use-ai flag errors gracefully if missing |
| 3 | Integration point | Parallel to baselines, AFTER align_to_common_grid, BEFORE change_detection |
| 4 | Output | ModelResult.feature_diff_map (H, W) + change_score_map (H, W) |
| 5 | Score semantics | "change_score" everywhere — NOT a probability, never labeled confidence |

---

## In scope vs NOT in scope

### IN SCOPE
- ModelAdapter protocol interface
- ClayAdapter implementation
- Tiled inference (chip → batch → stitch)
- Feature-diff map from before/after features
- --use-ai CLI flag with graceful fallback
- docs/CLAY_EXPERIMENT_REPORT.md with gate recommendation

### NOT in scope
- Comparison against baseline (005-evaluation-harness)
- Benchmark dataset (004-benchmark-dataset)
- Task-specific classifier heads (post-pilot)
- Probability calibration (post-evaluation)
- Rust integration for AI worker (008)

---

## Risk warnings

- If Clay or torch cannot install (MPS conflicts, arm64 issues), the experiment may fail clean. That is an acceptable result — document in the report.
- The feature-diff map may not correlate with vegetation change on a random example. That is fine — the experiment's job is to learn this, not to produce a pretty picture.
- 256x256 chips with 32px overlap means ~16 chips for a 1km AOI. CPU inference time for ~16 chips is ~30-60 seconds. This is non-trivial latency for the CLI path.
