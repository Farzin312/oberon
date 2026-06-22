# Plan — Baseline Fixes + Task Contract

**Parent**: [../README.md](./README.md)

Companion to [README.md](./README.md) and [tasks.md](./tasks.md).

---

## 1. Repo facts (verified)

| Area | Current state | Source |
|---|---|---|
| pixel_delta_magnitude | Stubbed as None in 3 places | `src/oberon/core/baselines.py:58,94,107` |
| Finding dataclass | No pixel_delta_mean | `src/oberon/core/__init__.py` |
| 001 Phase 7 cleanup | DRY + docs review + commit entire suite unchecked | 001 tasks.md |
| Test baseline | 114 tests, ruff 0, mypy 0 | `main` HEAD |

---

## 2. Execution order

1. **Phase 0 — Task contract doc** — `docs/TASK_CONTRACT.md` per Roadmap PDF Phase 1
2. **Phase 1 — pixel_delta implementation** (TDD)
3. **Phase 2 — pixel_delta wired through change_detection + artifacts**
4. **Phase 3 — 001 Phase 7 cleanup items**
5. **Phase 4 — QA gate**

---

## 3. Contracts

### 3.1 pixel_delta

```python
def compute_pixel_delta(
    before: dict[str, np.ndarray],
    after: dict[str, np.ndarray],
    mask: np.ndarray,
) -> np.ndarray:
    """Euclidean magnitude across all matching bands.
    
    Finds bands present in BOTH dicts. Stacks as (H, W, N).
    Computes sqrt(sum((after - before)^2, axis=2)).
    Returns (H, W) float32. NaN where not masked.
    """
```

Added to Finding: `pixel_delta_mean: float = 0.0`

Ranking formula update:
```python
ndvi_score = min(abs(ndvi_delta_mean) / 0.5, 1.0)
delta_score = min(pixel_delta_mean / 5000.0, 1.0)
score = max(ndvi_score, delta_score * 0.3)   # NDVI-weighted primary
```

### 3.2 Task contract

From Roadmap PDF Phase 1 (lines 411-449) + Product Brief:
- **Task:** `vegetation_disturbance`
- **Positive:** NDVI loss >= 0.15 over >= 0.5 ha within valid-pixel area
- **Negative:** NDVI change < 0.10 or area < 0.25 ha
- **Abstain triggers:** clouds > 50% AOI, valid pixels < 30%, seasonal mismatch flagged by user
- **Evidence required:** before/after PNG, overlay, GeoJSON, provenance manifest
- **Minimum area:** 0.5 ha (~50 Sentinel-2 pixels at 10m)

---

## 4. Exact changes

### 4.1 baselines.py
- Add `compute_pixel_delta(before, after, mask) -> np.ndarray` (new function)
- Replace `pixel_delta_magnitude=None` with `compute_pixel_delta(before, after, mask)` in compute_baselines

### 4.2 core/__init__.py
- Add `pixel_delta_mean: float = 0.0` to Finding

### 4.3 change_detection.py
- Track `pixel_delta_mean` per connected component in extract_findings
- Update ranking to: `score = max(ndvi_score, delta_score * 0.3)`

### 4.4 artifacts/geojson.py
- Add `pixel_delta_mean` to GeoJSON finding properties
- Add `analysis: {"pixel_delta_mean": ...}` block

### 4.5 artifacts/provenance.py
- Add `pixel_delta_mean` to finding summary in provenance

### 4.6 docs/TASK_CONTRACT.md (NEW)
- Per Roadmap Phase 1: positive, negative, minimum area, abstention triggers, evidence requirements

---

## 5. Risk register

| Risk | Mitigation |
|---|---|
| pixel_delta noisy with seasonal bands | Used only as secondary signal (0.3 weight) |
| 0.5 ha minimum area is wrong | Flag for calibration in mini-SDD 004 |
| Finding dataclass change breaks existing code | Add with default=0.0, backward compatible |

---

## 6. End-phase cleanup

- DRY sweep: verify SCL_CLOUD_BITS not duplicated
- Update AGENTS.md: pixel_delta gotcha + task contract reference
- Update DATA_FLOW.md contracts table
- Mark 001 Phase 7 complete or reference 002
