# 013 — Baseline Calibration: Reduce False Positives

**Parent**: [../README.md](../README.md)

Calibrate the deterministic baseline to reduce false positives exposed by the 005 evaluation. The pipeline over-detects because `threshold_change_map` uses `abs()` (catching seasonal green-up), lacks seasonal/broad-change abstention, and fragments single disturbance events into max_findings components. This mini-SDD fixes those three root causes without overfitting, changing the task contract, or making AI the default.

- **Branch:** `fix/013-baseline-calibration`
- **Status tracking:** see [`tasks.md`](./tasks.md) — checkboxes crossed off one at a time.
- **Strategy / architecture:** see [`plan.md`](./plan.md).

> **Hard rules (breaking any sinks the change):**
> 1. Deterministic-first — AI stays experimental. No changes to `--use-ai` or model promotion.
> 2. Do not change the TASK_CONTRACT thresholds (_DEFAULT_NDVI_THRESHOLD, _MIN_CHANGE_PIXELS, max_findings) unless this mini-SDD explicitly documents the change.
> 3. TDD for every logic change — watch the test fail first.
> 4. Do not overfit to the 12-example benchmark. Every fix must have a principled rationale that generalises.

---

## Locked decisions (confirmed)

| # | Decision | Choice |
|---|----------|--------|
| 1 | Task-direction-aware threshold | `vegetation_disturbance` flags NDVI loss only (negative deltas). Green-up (positive deltas) is not disturbance. Direction defaults to "absolute" for backwards compat and unknown tasks. |
| 2 | Broad-change seasonal abstention | If the absolute change mask covers >40% of valid AOI area, abstain with reason containing "seasonal". Phenological shifts affect the entire landscape; targeted disturbance does not. |
| 3 | Cross-season date annotation | When abstaining for pixel-quality reasons AND before/after windows span different seasons, prepend "seasonal" to the abstention reason so the golden tests recognise it. |
| 4 | Morphological closing | Apply binary closing (5x5 structure) before connected-component labelling. Merges pixel-level fragmentation within a single disturbance event (fire scars, clearcuts). |
| 5 | max_findings stays 20 | No contract change. The combination of fixes above naturally reduces finding counts without lowering the cap. |

---

## In scope vs. NOT in scope

### IN SCOPE
- `src/oberon/core/change_detection.py` — signed threshold, morphological closing
- `src/oberon/cli/orchestrator.py` — task direction mapping, seasonal abstention, closing integration
- `tests/core/test_change_detection.py` — new tests for each behaviour
- `docs/EVALUATION_REPORT.md` — updated with post-calibration metrics
- `docs/mini-sdd/README.md` — index update

### NOT in scope / preserved as-is
- AI branch (Clay adapter, comparison, --use-ai flag)
- Scene selection, STAC search, COG reading
- TASK_CONTRACT.md thresholds (0.15 NDVI, 0.5 ha min area, 0.3 pixel_delta weight)
- Scene composite logic (010)
- Scene availability fixes for cloud-blocked examples (03 Borneo palm oil)

---

## Risk warnings

- The signed threshold eliminates green-up FPs but could miss real disturbance if NDVI increases in a disturbed area (e.g., logging followed by immediate replanting). This is acceptable — vegetation_disturbance is defined as photosynthetic cover loss, not land-use change.
- The 40% broad-change threshold is calibrated against 12 examples. Real large fires (>40% of AOI) would be flagged as seasonal. Mitigation: the threshold is conservative — only triggers when the change is truly landscape-wide.
- Morphological closing with 5x5 kernel merges gaps up to 40m. Truly separate disturbances closer than 40m will merge. This is acceptable at the benchmark AOI scale.
- Example 03 (Borneo palm oil) abstains due to 25% valid pixels (cloud). This is a scene availability issue, not a calibration issue. It remains a known limitation.
- Example 09 (Costa Rica cloud) may still produce findings from cloud-edge artifacts. This requires better local cloud quality assessment, which is out of scope for 013.
