# Plan — 013 Baseline Calibration

**Parent**: [../README.md](../README.md)

Companion to [README.md](./README.md) (decisions + scope boundary) and [tasks.md](./tasks.md) (checkbox execution).

---

## 1. Root-cause analysis (verified from evaluation_output/baseline)

12 benchmark examples were run against the deterministic baseline pipeline on 2026-06-22. 11 of 12 golden integration tests fail. The failures map to three root causes:

### Root cause A: `abs()` threshold catches seasonal green-up (6 examples affected)

`threshold_change_map` uses `np.abs(diff_map) > threshold`. This flags both vegetation loss (deforestation) and vegetation green-up (crop growth, seasonal recovery) equally. For `vegetation_disturbance`, only NDVI loss is meaningful.

**Evidence from evaluation output:**
- 01-costa-rica-deforest: 20 findings, mean NDVI delta = +0.207 (POSITIVE — 15 of 20 findings are green-up)
- 02-amazon-para-clearcut: 20 findings, mean NDVI delta = +0.237 (POSITIVE — 16 of 20 are green-up)
- 06-iowa-stable-cropland: 13 findings, mean NDVI delta = +0.448 (all green-up, expected 0 findings)
- 07-temperate-summer-to-fall: 20 findings, mean NDVI delta = +0.189 (green-up, expected abstention)
- 09-costa-rica-cloud-wet: 5 findings, mean NDVI delta = +0.056 (mixed, expected abstention)
- 11-portugal-wildfire: 20 findings, 2 have POSITIVE deltas (seasonal noise)

**Fix:** `threshold_change_map` accepts an optional `direction` parameter. When `direction="negative"`, only flags pixels where `diff_map < -threshold`. Default remains `"absolute"` for backwards compatibility.

### Root cause B: No seasonal/broad-change abstention (4 examples affected)

When NDVI drops uniformly across an entire AOI (e.g., summer-to-fall senescence), the pipeline produces 20 findings because the threshold catches the change and connected components tile the landscape. There is no heuristic to detect "this change is too broad to be targeted disturbance."

**Evidence:**
- 07-temperate-summer-to-fall: 20 findings covering broad area (expected abstention "seasonal")
- 08-finland-boreal-seasonal: 20 findings, all negative NDVI (expected abstention "seasonal")
- 10-iowa-summer-vs-winter: abstains for "insufficient pixels" not "seasonal" (expected "seasonal")
- 09-costa-rica-cloud-wet: 5 findings from cloud edges (expected abstention "cloud")

**Fix:** After thresholding, if the change mask covers >40% of valid pixels, abstain with reason containing "seasonal" — phenological shifts affect the entire landscape. For pixel-quality abstentions where windows span different seasons, prepend "seasonal" to the reason.

### Root cause C: Fragmentation without consolidation (5 examples affected)

Real disturbance events (fire scars, clearcuts) produce many small adjacent connected components instead of one polygon. A 100-ha fire gets split into 20 small findings.

**Evidence:**
- 01-costa-rica: expected 1-5 findings, got 20
- 02-amazon: expected 2-8 findings, got 20
- 04-zambia: expected 1-5 findings, got 20 (all correctly negative, just fragmented)
- 11-portugal: expected 1-4 findings, got 20
- 12-california: expected 1-4 findings, got 20

**Fix:** Apply `scipy.ndimage.binary_closing(change_mask, structure=np.ones((5,5)))` before connected-component labelling. This merges components separated by gaps smaller than 50m.

---

## 2. Execution order (phased, low-risk first)

1. **Phase 0 — Setup** — branch + this mini-SDD doc set + baseline test count.
2. **Phase 1 — Signed threshold** — `threshold_change_map` accepts direction, orchestrator maps task to direction. *(gate: lint + tests + bounds)*
3. **Phase 2 — Seasonal abstention** — broad-change detection + cross-season annotation. *(gate: lint + tests + bounds)*
4. **Phase 3 — Morphological closing** — closing before connected components. *(gate: lint + tests + bounds)*
5. **Phase 4 — Quality gates** — full suite + bounds preflight.
6. **Phase 5 — Golden tests + evaluation report** — run integration tests, update EVALUATION_REPORT.md.

---

## 3. Architecture / contracts

### 3.1 threshold_change_map signature change

```
# BEFORE (current)
def threshold_change_map(diff_map, threshold=0.15) -> np.ndarray | None

# AFTER
def threshold_change_map(
    diff_map: np.ndarray | None,
    threshold: float = _DEFAULT_NDVI_THRESHOLD,
    direction: Literal["absolute", "negative", "positive"] = "absolute",
) -> np.ndarray | None
```

When `direction="negative"`: returns `diff_map < -threshold` (vegetation loss only).
When `direction="positive"`: returns `diff_map > threshold` (green-up only).
When `direction="absolute"`: returns `abs(diff_map) > threshold` (current behavior, backwards compat).

### 3.2 Task-to-direction mapping (orchestrator)

```python
_TASK_DIRECTION = {
    "vegetation_disturbance": "negative",
}
```

Default for unknown tasks: `"absolute"` (current behaviour).

### 3.3 Seasonal abstention heuristic

After thresholding, before extract_findings:
```python
broad_change_fraction = change_mask.sum() / mask.sum()
if broad_change_fraction > 0.40:
    return _abstention_result(
        f"Seasonal: change covers {broad_change_fraction:.0%} of valid AOI "
        f"(threshold: 40%) — likely phenological shift, not targeted disturbance",
        output_dir,
    )
```

### 3.4 Cross-season annotation

When abstaining for pixel-quality reasons, check if before/after windows likely span different seasons:
```python
before_month = request.before[0].month
after_month = request.after[0].month
month_gap = abs(after_month - before_month)
if month_gap >= 4:  # Cross-season if windows are 4+ months apart
    reason = f"seasonal: {reason}"
```

### 3.5 Morphological closing

```python
from scipy import ndimage as ndi
change_mask = ndi.binary_closing(change_mask, structure=np.ones((5, 5)))
```

### 3.6 Broad-change threshold constant

```python
# When >40% of valid AOI pixels are in the change mask, the change is too
# broad to be targeted disturbance — likely seasonal phenological shift.
_BROAD_CHANGE_FRACTION = 0.40
```

---

## 4. Exact changes per area

### 4.1 change_detection.py
- `threshold_change_map`: add `direction` parameter
- New function `_apply_morphological_closing(change_mask)` — wrapper for testability
- `detect_changes`: pass direction to threshold, apply closing
- **KEEP:** `_MIN_CHANGE_PIXELS`, `_PIXEL_AREA_HA`, `extract_findings`, `deduplicate_and_rank`, `_component_to_geojson_polygon`

### 4.2 orchestrator.py
- New `_TASK_DIRECTION` dict mapping task to threshold direction
- New `_BROAD_CHANGE_FRACTION` constant
- `run_analysis`: use task direction in threshold call, check broad-change fraction, apply cross-season annotation
- **KEEP:** `REQUIRED_BANDS`, `COMPOSITE_THRESHOLD`, `_MAX_COMPOSITE_SCENES`, `_run_ai_branch`, `_abstention_result`

### 4.3 tests/core/test_change_detection.py
- New `TestThresholdDirection`: tests for "negative", "positive", "absolute" directions
- New `TestMorphologicalClosing`: tests for closing merging adjacent components
- Existing tests unchanged (direction defaults to "absolute")

### 4.4 tests/cli/test_orchestrator.py (or tests/test_orchestrator_calibration.py)
- New tests for broad-change seasonal abstention
- New tests for task-direction mapping

---

## 5. Risk register

| Risk | Mitigation |
|---|---|
| Signed threshold misses disturbance with NDVI recovery | Acceptable: vegetation_disturbance = photosynthetic loss. Recovery is a different task. |
| 40% broad-change threshold too aggressive for large fires | A 40% AOI-scale fire would need a >5000ha AOI. Benchmark AOIs are 5-50ha. Documented in README risk warnings. |
| Closing merges distinct disturbances <50m apart | Acceptable at benchmark scale. Upgrade path: multi-scale closing with adaptive kernel. |
| Example 03 (Borneo) cannot be fixed (cloud/pixel availability) | Documented as known limitation. Not a calibration issue. |

---

## 6. End-phase cleanup (DRY + docs)

- **DRY sweep:** `_TASK_DIRECTION` dict is the single source of truth for task-direction mapping. No scattered conditionals.
- **Docs sync:** EVALUATION_REPORT.md updated with post-calibration metrics, TASK_CONTRACT.md notes signed threshold, mini-SDD README index updated.
- **Bounds:** No new public exports. All new symbols are module-private (`_` prefix).
