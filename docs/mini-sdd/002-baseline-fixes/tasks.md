# Tasks — Baseline Fixes + Task Contract

**Parent**: [../README.md](../README.md)

---

## Phase 0 — Task contract
**Status:** [ ]

- [ ] [DOC] Create `docs/TASK_CONTRACT.md` per Roadmap PDF Phase 1
- [ ] [DOC] Define: positive example, negative example, minimum area (0.5 ha), abstention triggers
- [ ] [DOC] Evidence requirements: before/after PNG, overlay, GeoJSON, provenance manifest
- [ ] [DOC] Task: `vegetation_disturbance` — NDVI loss >= 0.15

## Phase 1 — pixel_delta implementation (TDD)
**Status:** [ ]

- [ ] [TEST] `tests/core/test_baselines.py` — test compute_pixel_delta on 3-band synthetic input
- [ ] [TEST] `tests/core/test_baselines.py` — test returns NaN where mask is False
- [ ] [TEST] `tests/core/test_baselines.py` — test empty band dict returns zeros
- [ ] [TEST] `tests/core/test_baselines.py` — test compute_baselines returns non-None pixel_delta_magnitude
- [ ] [BE] `src/oberon/core/baselines.py` — implement compute_pixel_delta
- [ ] [BE] `src/oberon/core/baselines.py` — wire into compute_baselines

## Phase 2 — Pipeline wiring
**Status:** [ ]

- [ ] [BE] `src/oberon/core/__init__.py` — add pixel_delta_mean: float = 0.0 to Finding
- [ ] [BE] `src/oberon/core/change_detection.py` — extract_findings computes pixel_delta_mean per component
- [ ] [BE] `src/oberon/core/change_detection.py` — ranking: max(ndvi_score, delta_score * 0.3)
- [ ] [BE] `src/oberon/artifacts/geojson.py` — add pixel_delta_mean to GeoJSON properties
- [ ] [BE] `src/oberon/artifacts/provenance.py` — add pixel_delta_mean to finding summary
- [ ] [QA] ruff 0; pytest green; mypy 0

## Phase 3 — 001 cleanup
**Status:** [ ]

- [ ] [BE] DRY sweep: verify SCL_CLOUD_BITS not duplicated across modules
- [ ] [DOC] Verify EvidenceBundle output shape, note deviations from POST /v1/change (defer to 006)
- [ ] [DOC] Update AGENTS.md with pixel_delta gotcha
- [ ] [DOC] Update DATA_FLOW.md contracts table with pixel_delta
- [ ] [DOC] Mark 001 Phase 7 complete

## Phase 4 — QA gate
**Status:** [ ]

- [ ] [QA] `ruff check src/ tests/` — 0 exit
- [ ] [QA] `mypy src/` — 0 exit
- [ ] [QA] `pytest tests/ -v --tb=short` — baseline updated
- [ ] [QA] Commit: `feat: 002 baseline fixes + task contract`

---

### Progress

_None yet._
