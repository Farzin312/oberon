# Tasks — Spatial-Variance Seasonal Detection

**Parent**: [./README.md](./README.md)

---

## Phase 1 — Dataclass + variance computation

- [x] [BE] Add `SeasonalAssessment` dataclass to `core/__init__.py`
- [x] [BE] Add `compute_change_spatial_variance()` to `change_detection.py`
  - Inputs: change_mask (bool ndarray), ndvi_diff (float ndarray), valid_mask (bool ndarray)
  - Returns: `SeasonalAssessment | None`
  - Guards: <50 changed pixels -> None, near-zero mean -> cv=0.0
  - Thresholds: cv < 0.3 = uniform, coverage > 0.5 = broad -> should_abstain

Status: [x] DONE

## Phase 2 — Unit tests (TDD)

- [x] [BE] Test: uniform NDVI loss (all same value) -> is_uniform=True, should_abstain depends on coverage
- [x] [BE] Test: patchy NDVI loss (high variance) -> is_uniform=False, should_abstain=False
- [x] [BE] Test: uniform + high coverage -> should_abstain=True
- [x] [BE] Test: uniform + low coverage -> is_uniform=True, should_abstain=False
- [x] [BE] Test: <50 changed pixels -> returns None
- [x] [BE] Test: near-zero mean loss -> cv=0.0

Status: [x] DONE

## Phase 3 — Orchestrator integration

- [x] [BE] Call `compute_change_spatial_variance()` after closing, before extraction
- [x] [BE] Abstain when `assessment.should_abstain`
- [x] [BE] Set `seasonal_risk` flag when `assessment.is_uniform and not should_abstain`

Status: [x] DONE

## Phase 4 — Provenance annotation

- [x] [BE] Add `seasonal_risk`, `spatial_cv`, `change_coverage` to processing_config when applicable
- [x] [BE] Test provenance includes seasonal fields when seasonal_risk=True (covered by orchestrator integration)

Status: [x] DONE

## Phase 5 — Bounds + docs sync

- [x] [BE] Add SeasonalAssessment + compute_change_spatial_variance to bounds manifest (core.yaml)
- [x] [BE] Update mini-SDD README index with 014
- [x] [BE] Update EVALUATION_REPORT.md with spatial-variance approach
- [x] [BE] Update TASK_CONTRACT.md abstention triggers table

Status: [x] DONE

## QA Gate

- [x] `uv run ruff check src/ tests/` => clean
- [x] `uv run mypy src/` => clean
- [x] `uv run pytest tests/ --ignore=tests/integration --ignore=tests/cli/test_request_json.py -q` => 287 pass
- [x] `uv run bounds preflight --ci` => clean

Status: [x] DONE
