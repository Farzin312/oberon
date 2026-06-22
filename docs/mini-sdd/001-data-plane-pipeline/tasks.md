# Tasks — Data Plane Pipeline (Walking Vertical Slice)

**Parent**: [../README.md](../README.md)

Execution checklist. Cross items off one at a time. All quality gates apply per phase.

**Legend:** `[BE]` backend code · `[QA]` verification · `[DOC]` documentation · `[TEST]` failing test first (TDD gate)

---

## Phase 0 — Setup & safety
**Status:** [x] COMPLETE

- [x] [DOC] Create `docs/mini-sdd/001-data-plane-pipeline/` with README, plan, tasks (this doc)
- [x] [DOC] Record locked decisions + in-scope/not-in-scope boundary (README.md)
- [x] [BE] Initialize bounds: `bounds init --root` then `bounds init --subsystem <name>` for each subsystem
- [x] [BE] Create `src/oberon/core/domain.py` with all dataclass models
- [x] [BE] Create `src/oberon/core/__init__.py` exports
- [x] [QA] Baseline: `pytest --collect-only | tail -1` recorded; `bounds validate --quick` clean
- [x] [BE] Create `tests/conftest.py` with shared fixtures
- [x] [BE] Create `tests/data/sample.geojson` — small test polygon (Costa Rica forest, ~100 ha)

## Phase 1 — STAC Discovery + Scene Quality
**Status:** [x] COMPLETE

- [x] [TEST] `tests/core/test_geometry.py` — 15 tests covering validation, bbox, area (edge cases: bowtie, empty coords, missing type, negative lon)
- [x] [BE] `src/oberon/core/geometry.py` — geometry validation, bbox, planar area approximation
- [x] [TEST] `tests/pipeline/test_stac_discovery.py` — 16 tests: search API params, item parsing, empty results, connection errors, missing fields, quality ranking, period split, cloud filtering
- [x] [BE] `src/oberon/pipeline/stac_discovery.py` — STAC search via pystac-client, scene-level quality ranking with period split
- [x] [TEST] `tests/pipeline/test_scene_quality.py` — 10 tests: SCL mask analysis (all-clear, all-cloud, 50/50, empty array, custom bits), scene-proxy bridge
- [x] [BE] `src/oberon/pipeline/scene_quality.py` — SCL valid-fraction computation (pure NumPy), scene quality bridge stub (deferred to Phase 2 for full AOI-local via COG)
- [x] [QA] `ruff check src/ tests/` — 0 exit; 41 tests green; `bounds validate` clean (17 files owned)

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

**Started:** 2026-06-21
**Phases complete:** 1 (Setup + STAC Discovery + Scene Quality)
**Key commits:** `5d41071` (initial scaffolding), `...` (Phase 1 implementation)
**Test baseline:** 41 tests, 0 failures, 0 warnings
**Lint:** ruff 0 exit
**Bounds:** 17 files owned, 4 subsystems, validate clean
**What remains:** Phases 2-7 (COG reading, preparation, baselines, evidence, CLI, verify, cleanup)
