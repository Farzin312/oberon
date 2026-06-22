# Tasks — Spatial-Variance Seasonal Detection

**Parent**: [./README.md](./README.md)

---

## Phase 1 — Dataclass + variance computation

- [ ] [BE] Add `SeasonalAssessment` dataclass to `core/__init__.py`
- [ ] [BE] Add `compute_change_spatial_variance()` to `change_detection.py`
  - Inputs: change_mask (bool ndarray), ndvi_diff (float ndarray), valid_mask (bool ndarray)
  - Returns: `SeasonalAssessment | None`
  - Guards: <50 changed pixels -> None, near-zero mean -> cv=0.0
  - Thresholds: cv < 0.3 = uniform, coverage > 0.5 = broad -> should_abstain

Status: [ ]

## Phase 2 — Unit tests (TDD)

- [ ] [BE] Test: uniform NDVI loss (all same value) -> is_uniform=True, should_abstain depends on coverage
- [ ] [BE] Test: patchy NDVI loss (high variance) -> is_uniform=False, should_abstain=False
- [ ] [BE] Test: uniform + high coverage -> should_abstain=True
- [ ] [BE] Test: uniform + low coverage -> is_uniform=True, should_abstain=False
- [ ] [BE] Test: <50 changed pixels -> returns None
- [ ] [BE] Test: near-zero mean loss -> cv=0.0

Status: [ ]

## Phase 3 — Orchestrator integration

- [ ] [BE] Call `compute_change_spatial_variance()` after closing, before extraction
- [ ] [BE] Abstain when `assessment.should_abstain`
- [ ] [BE] Set `seasonal_risk` flag when `assessment.is_uniform and not should_abstain`

Status: [ ]

## Phase 4 — Provenance annotation

- [ ] [BE] Add `seasonal_risk`, `spatial_cv`, `change_coverage` to processing_config when applicable
- [ ] [BE] Test provenance includes seasonal fields when seasonal_risk=True

Status: [ ]

## Phase 5 — Bounds + docs sync

- [ ] [BE] Add SeasonalAssessment + compute_change_spatial_variance to bounds manifest (core.yaml)
- [ ] [BE] Update mini-SDD README index with 014
- [ ] [BE] Update EVALUATION_REPORT.md with spatial-variance approach
- [ ] [BE] Update TASK_CONTRACT.md abstention triggers table

Status: [ ]

## QA Gate

- [ ] `uv run ruff check src/ tests/` => clean
- [ ] `uv run mypy src/` => clean
- [ ] `uv run pytest tests/ --ignore=tests/integration --ignore=tests/cli/test_request_json.py -q` => all pass
- [ ] `uv run bounds preflight --ci` => clean

Status: [ ]
