# Tasks — Data Plane Pipeline (Walking Vertical Slice)

**Parent**: [../README.md](../README.md)

Execution checklist. Cross items off one at a time. All quality gates apply per phase.

**Legend:** `[BE]` backend code · `[QA]` verification · `[DOC]` documentation · `[TEST]` failing test first (TDD gate)

---

## Phase 0 — Setup & safety
**Status:** [⏳] IN PROGRESS

- [ ] [DOC] Create `docs/mini-sdd/001-data-plane-pipeline/` with README, plan, tasks (this doc)
- [ ] [DOC] Record locked decisions + in-scope/not-in-scope boundary (README.md)
- [ ] [BE] Initialize bounds: `bounds init --root` then `bounds init --subsystem <name>` for each subsystem
- [ ] [BE] Create `src/oberon/core/domain.py` with all dataclass models
- [ ] [BE] Create `src/oberon/core/__init__.py` exports
- [ ] [QA] Baseline: `pytest --collect-only | tail -1` recorded; `bounds validate --quick` clean
- [ ] [BE] Create `tests/conftest.py` with shared fixtures
- [ ] [BE] Create `tests/data/sample.geojson` — small test polygon (Costa Rica forest, ~100 ha)

> **Gate note:** All files above must be green before Phase 1 starts.

---

## Phase 1 — STAC Discovery + Scene Quality  ⚠️ gate before Phase 2
**Status:** [ ]

- [ ] [TEST] `tests/pipeline/test_stac_discovery.py` — test that STAC query returns items intersecting AOI with `intersects` filter
- [ ] [BE] `src/oberon/pipeline/stac_discovery.py` — STAC search function, CandidateScene model parsing
- [ ] [TEST] `tests/core/test_geometry.py` — test geometry validation, bbox calculation from GeoJSON polygon
- [ ] [BE] `src/oberon/core/geometry.py` — geometry helpers
- [ ] [TEST] `tests/pipeline/test_scene_quality.py` — test local valid-pixel fraction from SCL mask
- [ ] [BE] `src/oberon/pipeline/scene_quality.py` — quality assessment, scene ranking, best-per-period selection
- [ ] [QA] `ruff check src/ tests/` — 0 exit; `pytest tests/pipeline/test_stac_discovery.py tests/core/test_geometry.py -v` — all pass
- [ ] [QA] `bounds validate --quick` — clean

---

## Phase 2 — COG Reading + Preparation  ⚠️ gate before Phase 3
**Status:** [ ]

- [ ] [TEST] `tests/pipeline/test_cog_reader.py` — test windowed read returns correct bands and shape
- [ ] [BE] `src/oberon/pipeline/cog_reader.py` — COG range read, band extraction, nodata handling
- [ ] [TEST] `tests/pipeline/test_preparation.py` — test SCL masking, reprojection, resampling, alignment
- [ ] [BE] `src/oberon/pipeline/preparation.py` — mask composite construction, reproject/resample, CRS alignment
- [ ] [QA] `ruff check src/ tests/` — 0 exit; full phase tests green
- [ ] [QA] `bounds validate --quick` — clean
- [ ] [DOC] `bounds calibrate --dump-baseline` for modified subsystems

> **Gate note:** Assert created arrays are same CRS, same shape, same bounds. If not, the preparation is broken.

---

## Phase 3 — Baseline Analytics  ⚠️ gate before Phase 4
**Status:** [ ]

- [ ] [TEST] `tests/core/test_baselines.py` — test NDVI, NBR, NDMI computation with known inputs (e.g., all-zeros -> 0, all-NIR high -> 1)
- [ ] [BE] `src/oberon/core/baselines.py` — index computation on aligned arrays, division-by-zero guard
- [ ] [TEST] `tests/core/test_change_detection.py` — test thresholding, connected components, area calculation
- [ ] [BE] `src/oberon/core/change_detection.py` — threshold diff maps → binary mask → connected components → Finding list
- [ ] [TEST] `tests/core/test_baselines.py` — test abstention: masked arrays with < 30% valid pixels return abstention
- [ ] [BE] `src/oberon/core/baselines.py` — abstention logic in BaselineResult
- [ ] [QA] `ruff check src/ tests/` — 0 exit; full phase tests green
- [ ] [QA] `bounds validate --quick` — clean

---

## Phase 4 — Evidence Bundles + Provenance  ⚠️ gate before Phase 5
**Status:** [ ]

- [ ] [TEST] `tests/artifacts/test_images.py` — test true-color composite from B04/B03/B02, test overlay rendering
- [ ] [BE] `src/oberon/artifacts/images.py` — PNG composite generation, change overlay on before image
- [ ] [TEST] `tests/artifacts/test_geojson.py` — test valid GeoJSON FeatureCollection output
- [ ] [BE] `src/oberon/artifacts/geojson.py` — Finding list → GeoJSON FeatureCollection file
- [ ] [TEST] `tests/core/test_provenance.py` — test manifest contains all required fields
- [ ] [BE] `src/oberon/artifacts/provenance.py` — provenance dict construction, JSON output
- [ ] [QA] `bounds validate --quick` — clean

---

## Phase 5 — CLI Wiring
**Status:** [ ]

- [ ] [TEST] `tests/cli/test_analyze.py` — test CLI runs end-to-end with mock STAC and synthetic arrays
- [ ] [BE] `src/oberon/cli/main.py` — click group + `analyze` command with all options
- [ ] [BE] `src/oberon/cli/orchestrator.py` — pipeline orchestration: call stages, handle abstention, write output
- [ ] [BE] `src/oberon/core/__init__.py` — update exports to include all public models
- [ ] [BE] `src/oberon/pipeline/__init__.py` — update exports
- [ ] [BE] `src/oberon/artifacts/__init__.py` — update exports
- [ ] [QA] `python -m oberon.cli analyze --help` — works, shows all options
- [ ] [BE] `uv lock` — lock all dependencies

---

## Phase 6 — Verify & QA
**Status:** [ ]

- [ ] [QA] `ruff check src/ tests/` — 0 exit
- [ ] [QA] `mypy src/` — all type-checked (use `# type: ignore` only for unavoidable Rasterio/NumPy signature issues)
- [ ] [QA] `pytest tests/ -v --tb=short` — all tests pass, ≥ baseline count
- [ ] [QA] `bounds preflight --ci` — green (no boundary violations, no orphan exports)
- [ ] [QA] Manual check: all `# ponytail:` comments present and correct
- [ ] [DOC] `docs/architecture/SYSTEM_DESIGN.md` — verify matches actual implementation
- [ ] [DOC] `docs/architecture/DATA_FLOW.md` — verify matches actual pipeline order
- [ ] [DOC] `AGENTS.md` — update gotchas with any discoveries from implementation
- [ ] [DOC] `bounds calibrate --dump-baseline` — re-baseline all manifests

---

## Phase 7 — Cleanup & doc sync (END)
**Status:** [ ]

- [ ] [BE] DRY sweep: check for duplicated masking logic, repeated CRS handling, shared constants
- [ ] [DOC] Update mini-SDD tasks.md — all checkboxes crossed, progress summary written
- [ ] [DOC] Final docs review: CLAUDE.md, AGENTS.md, README.md, CONTRIBUTING.md — all current
- [ ] [BE] Squash commits into clean history for the feature branch
- [ ] [DOC] Write phase-end summary in Progress section below

---

### Progress

<!-- Keep current — the at-a-glance state. -->

**Started:** 2026-06-21
**Phases complete:** 0 (in progress — scaffolding docs complete, source code pending)
**Key commits:** (none yet)
**Test baseline:** (to be recorded)
**What remains:** Phases 1-7 above
