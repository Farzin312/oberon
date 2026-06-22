# Tasks — Baseline Fixes + Task Contract

**Parent**: [../README.md](../README.md)

---

## Phase 0 — Task contract
**Status:** [x] DONE

- [x] [DOC] Create `docs/TASK_CONTRACT.md` per Roadmap PDF Phase 1
- [x] [DOC] Define: positive example, negative example, minimum area (0.5 ha), abstention triggers
- [x] [DOC] Evidence requirements: before/after PNG, overlay, GeoJSON, provenance manifest
- [x] [DOC] Task: `vegetation_disturbance` — NDVI loss >= 0.15

## Phase 1 — pixel_delta implementation (TDD)
**Status:** [x] DONE

- [x] [TEST] `tests/core/test_baselines.py` — test compute_pixel_delta on 3-band synthetic input
- [x] [TEST] `tests/core/test_baselines.py` — test returns NaN where mask is False
- [x] [TEST] `tests/core/test_baselines.py` — test empty band dict returns zeros
- [x] [TEST] `tests/core/test_baselines.py` — test compute_baselines returns non-None pixel_delta_magnitude
- [x] [BE] `src/oberon/core/baselines.py` — implement compute_pixel_delta
- [x] [BE] `src/oberon/core/baselines.py` — wire into compute_baselines

## Phase 2 — Pipeline wiring
**Status:** [x] DONE

- [x] [BE] `src/oberon/core/__init__.py` — add pixel_delta_mean: float = 0.0 to Finding
- [x] [BE] `src/oberon/core/change_detection.py` — extract_findings computes pixel_delta_mean per component
- [x] [BE] `src/oberon/core/change_detection.py` — ranking: max(ndvi_score, delta_score * 0.3)
- [x] [BE] `src/oberon/artifacts/geojson.py` — add pixel_delta_mean to GeoJSON properties
- [x] [BE] `src/oberon/artifacts/provenance.py` — add pixel_delta_mean to finding summary
- [x] [QA] ruff 0; pytest green; mypy 0

## Phase 3 — 001 cleanup
**Status:** [x] DONE

- [x] [BE] DRY sweep: SCL_CLOUD_BITS not duplicated — defined once in core/__init__.py, imported in cog_reader.py + scene_quality.py
- [x] [DOC] EvidenceBundle output shape reviewed; API gap analysis deferred to 006
- [x] [DOC] Update AGENTS.md with pixel_delta gotcha + task contract link
- [x] [DOC] Update DATA_FLOW.md contracts table with pixel_delta
- [x] [DOC] Mark 001 Phase 7 complete

## Phase 4 — QA gate
**Status:** [ ]

- [ ] [QA] `ruff check src/ tests/` — 0 exit
- [ ] [QA] `mypy src/` — 0 exit
- [ ] [QA] `pytest tests/ -v --tb=short` — baseline updated
- [ ] [QA] Commit: `feat: 002 baseline fixes + task contract`

---

### Progress

_None yet._
