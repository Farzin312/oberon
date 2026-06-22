# 004 — Benchmark Dataset + Golden Tests

**Parent**: [../README.md](../README.md)

Collect a reviewed set of before/after Sentinel-2 pairs and create golden-case integration tests. Roadmap PDF Phase 2 requires this before any AI claim.

- **Reference:** Roadmap PDF Phase 2 (lines 451-476), Product Brief §8 Evaluation
- **Prerequisite:** 002-baseline-fixes (task contract), 003-clay-experiment (optional)

> **Hard rules:**
> 1. Every example must be human-reviewed. No auto-labeling.
> 2. Geographic AND temporal holdouts — no splitting neighboring patches.
> 3. Must include failure cases (cloud, seasonal, no-data) — not just clean positives.
> 4. Dataset lives in-repo as small GeoJSON + metadata JSON, NOT raw imagery.

---

## Locked decisions

| # | Decision | Choice |
|---|----------|--------|
| 1 | Target size | 12-18 reviewed examples (Roadmap: "small, carefully reviewed benchmark") |
| 2 | Storage | `tests/data/benchmark/NNN-<slug>/` per-example subdir, Git-tracked |
| 3 | Automation | Golden tests marked `@pytest.mark.integration`, skip in CI without `--run-integration` |
| 4 | Verification | Cross-reference with Global Forest Watch / Hansen data for labeling |

---

## In scope vs NOT in scope

### IN SCOPE
- Collect 12-18 examples from diverse regions
- Per-example: aoi.geojson, expected.json, review.md
- Golden test harness with --run-integration flag
- Geographic + temporal holdout split documentation
- Calibration report with actual-vs-expected metrics

### NOT in scope
- AI evaluation (005-evaluation-harness)
- Public dataset publication
- More than 20 examples (expand after pilot)
- Commercial imagery (Sentinel-2 only)
- Golden-case tests that DON'T hit live STAC/COG — network is the point

---

## Risk warnings

- Finding clean Sentinel-2 examples with ground-truthable vegetation loss is manual work. Budget ~30-60 min per example.
- The benchmark is a technical benchmark, not production ground truth. Thresholds derived from it are approximate.
- Live data fetches are slow (~10-30s per example). Total: ~3-9 min for the full suite.
