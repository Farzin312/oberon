# Plan — Spatial-Variance Seasonal Detection

**Parent**: [./README.md](./README.md)

---

## 1. Verified repo facts

| Area | Current state | Source |
|---|---|---|
| Change mask | Boolean np.ndarray, post-closing | `orchestrator.py` line 151 `apply_morphological_closing(change_mask)` |
| NDVI diff | np.ndarray, computed from baselines | `orchestrator.py` line 137-138 |
| Valid mask | `pair.mask` boolean array | `PreparedPair.mask` in `core/__init__.py` |
| Closing kernel | 25x25 (250m) | `change_detection.py` `apply_morphological_closing(kernel_size=25)` |
| Directional threshold | negative direction for veg_disturbance | `orchestrator.py` line 143 |
| Current flow | threshold -> closing -> extract_findings -> rank | `orchestrator.py` lines 144-159 |

New insertion point: between closing (line 151) and extract_findings (line 154).

---

## 2. Architecture

### 2.1 Spatial variance computation

```
Input: change_mask (bool ndarray), ndvi_diff (float ndarray), valid_mask (bool ndarray)

changed_values = ndvi_diff[change_mask & valid_mask]
if len(changed_values) < 50:  # too few changed pixels for statistics
    return None  # skip variance check

mean_loss = np.mean(changed_values)  # expected negative (NDVI loss)
std_loss = np.std(changed_values)

if abs(mean_loss) < 1e-6:
    cv = 0.0  # near-zero mean loss, treat as uniform
else:
    cv = std_loss / abs(mean_loss)

coverage = np.count_nonzero(change_mask & valid_mask) / valid_mask.sum()
```

Return a `SeasonalAssessment` with cv, coverage, is_uniform, should_abstain.

### 2.2 Orchestrator integration

```python
# After closing, before extraction:
assessment = compute_change_spatial_variance(change_mask, ndvi_diff, pair.mask)

if assessment and assessment.should_abstain:
    reason = f"Seasonal pattern detected: uniform NDVI loss (CV={assessment.cv:.2f}, coverage={assessment.coverage:.0%})"
    return _abstention_result(reason, output_dir)

# If seasonal_risk but not abstaining, annotate provenance:
seasonal_risk = assessment is not None and assessment.is_uniform and not assessment.should_abstain
```

---

## 3. Contracts

### 3.1 New dataclass

```python
@dataclass(frozen=True)
class SeasonalAssessment:
    cv: float              # coefficient of variation of NDVI loss
    coverage: float        # fraction of valid pixels with change
    is_uniform: bool       # cv < 0.3
    should_abstain: bool   # is_uniform AND coverage > 0.5
```

### 3.2 Provenance annotation

When `seasonal_risk=True`, processing_config gets:
```json
{
  "seasonal_risk": true,
  "spatial_cv": 0.25,
  "change_coverage": 0.35
}
```

---

## 4. Execution order

1. **Phase 1 — Dataclass + variance computation** (change_detection.py)
2. **Phase 2 — Unit tests** (test_change_detection.py) — TDD: write tests first
3. **Phase 3 — Orchestrator integration** (orchestrator.py)
4. **Phase 4 — Provenance annotation** (provenance.py + orchestrator.py)
5. **Phase 5 — Bounds + docs sync**

---

## 5. Risk register

| Risk | Mitigation |
|---|---|
| CV threshold 0.3 too aggressive (catches real fires) | Dual-condition guard: must also have >50% coverage. Megafires rarely cover >50% of a small AOI. |
| CV threshold 0.3 too conservative (misses seasonal) | Golden integration tests will reveal. Adjust and document. |
| All-same-value edge case | Guard: if abs(mean) < 1e-6, cv=0.0 (treated as uniform). |
| Small AOI noise | Guard: if <50 changed pixels, skip variance check entirely. |
