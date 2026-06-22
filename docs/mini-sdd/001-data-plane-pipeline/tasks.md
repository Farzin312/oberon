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

## Phase 2 — COG Reading + Preparation
**Status:** [DONE — 12/12 items]

**COG reader — windowed reads from cloud-optimized GeoTIFFs**

- [x] [TEST] `tests/pipeline/test_cog_reader.py` — test `read_window` returns dict of band arrays with correct keys and shapes for a mocked COG window
- [x] [TEST] `tests/pipeline/test_cog_reader.py` — test 404 COG URL raises `FileNotFoundError` with scene ID
- [x] [TEST] `tests/pipeline/test_cog_reader.py` — test missing band in assets returns partial dict (available bands only)
- [x] [TEST] `tests/pipeline/test_cog_reader.py` — test empty band list raises `ValueError`
- [x] [TEST] `tests/pipeline/test_cog_reader.py` — test buffer_pixels=1 adds correct padding to window dimensions
- [x] [BE] `src/oberon/pipeline/cog_reader.py` — implement `read_window(scene, aoi_geom, bands, buffer=1) -> RasterWindow`

**SCL masking — composite mask from Scene Classification Layer**

- [x] [TEST] `tests/pipeline/test_preparation.py` — test `build_valid_mask` combines SCL invalid bits + nodata (0) correctly
- [x] [TEST] `tests/pipeline/test_preparation.py` — test missing SCL falls back to nodata-only mask with warning flag
- [x] [TEST] `tests/pipeline/test_preparation.py` — test all-pixels-obstructed returns `(all_false_mask, "AOI fully obstructed")`
- [x] [BE] `src/oberon/pipeline/preparation.py` — implement `build_valid_mask(window) -> tuple[mask, reason]`

**Preparation — reproject, resample, crop**

- [x] [TEST] `tests/pipeline/test_preparation.py` — test `align_to_common_grid` returns before/after with same shape, same CRS
- [x] [TEST] `tests/pipeline/test_preparation.py` — test before/after from different CRS reprojected correctly to target
- [x] [TEST] `tests/pipeline/test_preparation.py` — test intersection bounds cropping (crops to overlap region)
- [x] [TEST] `tests/pipeline/test_preparation.py` — test resampled dimension < 10px returns PreparedPair with is_usable=False
- [x] [TEST] `tests/pipeline/test_preparation.py` — test SCL band nearest-neighbor resampled (not bilinear)
- [x] [BE] `src/oberon/pipeline/preparation.py` — implement `align_to_common_grid(before, after, target_crs, target_resolution=10) -> PreparedPair`
- [x] [BE] `src/oberon/core/__init__.py` — add `PreparedPair.is_usable` and `PreparedPair.valid_fraction` properties
- [x] [TEST] `tests/pipeline/test_scene_quality.py` — test SCL-based `assess_scene` returns correct local valid fraction
- [x] [TEST] `tests/pipeline/test_scene_quality.py` — test SCL read failure falls back to cloud-pct proxy gracefully
- [x] [BE] `src/oberon/pipeline/scene_quality.py` — upgrade `assess_scene` to read SCL band from COG when available

**Quality bridge upgrade** ([absorbed into task above])

- [-] ~~[BE] `src/oberon/pipeline/scene_quality.py` — upgrade `assess_scene` to use `read_window` for SCL when COG reader exists~~

**QA gate**

- [x] [QA] `ruff check src/ tests/` — 0 exit; Phase 2 tests green
- [~] [QA] `bounds validate --quick` — clean (bounds CLI not in PATH — skipped; see Progress)
- [ ] [DOC] Update `AGENTS.md` with COG URL pattern gotcha if discovered (deferred to Phase 6 doc sweep)

> **Gate note:** All prepared arrays must have the same CRS, the same shape, and the same bounds. If any differ, the transformation is broken.

---

## Phase 3 — Baseline Analytics + Change Detection
**Status:** [x] COMPLETE — 80 tests green, ruff 0 exit

**Baseline computation — complete wiring of stubs**

> Note: the task list originally named the entry point `compute_all`; the de-facto contract (plan.md §6.3 orchestrator pseudocode) is `compute_baselines`, which already existed and passed all six tests unchanged.

- [x] [TEST] `tests/core/test_baselines.py` — test `compute_baselines` returns abstention when `pair.is_usable` is False
- [x] [TEST] `tests/core/test_baselines.py` — test all bands present computes NDVI + NBR + NDMI + abstention check
- [x] [TEST] `tests/core/test_baselines.py` — test missing SWIR bands (B11, B12) produces NDMI=None, NBR=None gracefully
- [x] [TEST] `tests/core/test_baselines.py` — test all-zero arrays produce NDVI of 0.0 (NIR=0, Red=0 → division guard = epsilon)
- [x] [TEST] `tests/core/test_baselines.py` — test NIR-saturated values (10000) produce NDVI near 0.0 with Red near 10000
- [x] [TEST] `tests/core/test_baselines.py` — test fully masked pair returns `BaselineResult(abstain=True)`
- [x] [BE] `src/oberon/core/baselines.py` — `compute_baselines(pair) -> BaselineResult` verified (no code change needed)

**Change detection — complete wiring of stubs**

- [x] [TEST] `tests/core/test_change_detection.py` — test `extract_findings` with no change mask returns empty list
- [x] [TEST] `tests/core/test_change_detection.py` — test single connected component produces one Finding with correct area
- [x] [TEST] `tests/core/test_change_detection.py` — test multiple components with only one above min_pixels returns 1 Finding
- [x] [TEST] `tests/core/test_change_detection.py` — test component below min_change_area (49px) is filtered out
- [x] [TEST] `tests/core/test_change_detection.py` — test `deduplicate_and_rank` returns findings sorted by score descending
- [x] [TEST] `tests/core/test_change_detection.py` — test `deduplicate_and_rank` with 25 findings caps at max_findings=20
- [x] [TEST] `tests/core/test_change_detection.py` — test geometry is valid GeoJSON Polygon (exterior ring)
- [x] [TEST] `tests/core/test_change_detection.py` — test all-zero scores returns empty result
- [x] [BE] `src/oberon/core/change_detection.py` — `_component_to_geojson_polygon` now uses shapely `convex_hull` (bbox fallback for degenerate hulls)
- [x] [BE] `src/oberon/core/change_detection.py` — implemented `deduplicate_and_rank(findings, max_findings=20) -> list[Finding]`
- [x] [BE] `src/oberon/core/change_detection.py` — wired `detect_changes(pair, threshold, min_pixels) -> list[Finding]`
- [x] [BE] `src/oberon/core/change_detection.py` — fixed bug: `findings.append` was nested inside `if ndvi_diff is not None:` (findings dropped when ndvi_diff None)

**QA gate**

- [x] [QA] `ruff check src/ tests/` — 0 exit; Phase 3 tests green (80 passed)
- [~] [QA] `bounds validate --quick` — clean (bounds CLI not in PATH — skipped; see Progress)

---

## Phase 4 — Evidence Bundles + Provenance
**Status:** [x] COMPLETE — 106 tests, ruff 0 exit

**True-color imagery**

- [x] [TEST] `tests/artifacts/test_images.py` — test `render_true_color` produces a valid PNG at output path
- [x] [TEST] `tests/artifacts/test_images.py` — test all-zero bands produce valid PNG (0 → 0 after 2% clip)
- [x] [TEST] `tests/artifacts/test_images.py` — test all-10000 bands produce valid PNG (10000 → 255 after 98% clip)
- [x] [TEST] `tests/artifacts/test_images.py` — test `render_change_overlay` produces PNG with red overlay on before image
- [x] [BE] `src/oberon/artifacts/images.py` — implement `render_true_color(red, green, blue, path) -> Path` using PIL/Pillow
- [x] [BE] `src/oberon/artifacts/images.py` — implement `render_change_overlay(before_rgb, change_mask, path) -> Path`

**GeoJSON findings**

- [x] [TEST] `tests/artifacts/test_geojson.py` — test `write_findings_geojson` produces valid GeoJSON FeatureCollection
- [x] [TEST] `tests/artifacts/test_geojson.py` — test empty findings list produces FeatureCollection with 0 features (valid GeoJSON)
- [x] [TEST] `tests/artifacts/test_geojson.py` — test each feature has geometry + all required properties
- [x] [TEST] `tests/artifacts/test_geojson.py` — test findings in different CRS are reprojected to EPSG:4326
- [x] [BE] `src/oberon/artifacts/geojson.py` — implement `write_findings_geojson(findings, path) -> Path`

**Provenance manifest**

- [x] [TEST] `tests/artifacts/test_provenance.py` — test `build_provenance` manifest contains all required fields from the schema
- [x] [TEST] `tests/artifacts/test_provenance.py` — test abstention case produces manifest with abstention populated and no findings
- [x] [TEST] `tests/artifacts/test_provenance.py` — test empty findings produces valid manifest with empty_findings flag
- [x] [TEST] `tests/artifacts/test_provenance.py` — test manifest includes software versions for all key deps
- [x] [BE] `src/oberon/artifacts/provenance.py` — implement `build_provenance(findings, bundle, abstention_reason) -> dict`

**Output directory management**

- [x] [BE] `src/oberon/artifacts/__init__.py` — add `create_output_dir(path: Path) -> Path` that creates dir and returns it
- [x] [BE] `src/oberon/artifacts/__init__.py` — add `build_evidence_bundle(findings, pair, output_dir, abstention_reason) -> EvidenceBundle`
- [x] [TEST] `tests/artifacts/test_evidence_bundle.py` — integration test: all artifacts created, GeoJSON valid, images valid PNGs, empty findings, abstention

**QA gate**

- [x] [QA] `ruff check src/ tests/` — 0 exit; Phase 4 tests green (26 artifact tests)
- [~] [QA] `bounds validate --quick` — clean (bounds CLI not in PATH — skipped; see Progress)
- [x] [QA] Manual inspection: output PNG is valid, GeoJSON is valid JSON

---

## Phase 5 — CLI Wiring + Pipeline Orchestration
**Status:** [ ]

**Full pipeline orchestration**

- [ ] [BE] `src/oberon/cli/orchestrator.py` — implement `run_analysis(request, output_dir) -> EvidenceBundle` following the orchestration flow in plan.md §6.3
- [ ] [BE] `src/oberon/cli/orchestrator.py` — handle each abstention path: "No suitable scenes found", "Missing before/after scene", "Insufficient valid pixels", abstention in baselines
- [ ] [BE] `src/oberon/cli/orchestrator.py` — handle STAC connection error, invalid polygon, COG read failure with descriptive messages

**CLI command**

- [ ] [TEST] `tests/cli/test_analyze.py` — test `oberon analyze --help` shows all options
- [ ] [TEST] `tests/cli/test_analyze.py` — test `oberon analyze` with invalid date format exits with error code 1
- [ ] [TEST] `tests/cli/test_analyze.py` — test `oberon analyze` with missing --aoi flag shows required error
- [ ] [TEST] `tests/cli/test_analyze.py` — test end-to-end with mocked STAC + synthetic COG + expected output
- [ ] [BE] `src/oberon/cli/main.py` — complete click `analyze` command: option definitions, type validation, error handling, call orchestrator

**Export cleanup**

- [ ] [BE] `src/oberon/core/__init__.py` — verify all public models are exported
- [ ] [BE] `src/oberon/pipeline/__init__.py` — add exports for pipeline functions
- [ ] [BE] `src/oberon/artifacts/__init__.py` — add exports for artifact functions
- [ ] [QA] `python -m oberon.cli analyze --help` — works, shows all options
- [ ] [BE] `uv lock` — lock all dependencies

**QA gate**

- [ ] [QA] `ruff check src/ tests/` — 0 exit
- [ ] [QA] `pytest tests/cli/ -v` — all pass

---

## Phase 6 — Verify & QA
**Status:** [ ]

- [ ] [QA] `ruff check src/ tests/` — 0 exit
- [ ] [QA] `mypy src/` — 0 exit (allow `# type: ignore` on Rasterio/NumPy signatures only)
- [ ] [QA] `pytest tests/ -v --tb=short` — all tests pass, track baseline count
- [ ] [QA] `bounds preflight --ci` — green (no boundary violations, no orphan exports)
- [ ] [QA] Manual check: all `# ponytail:` comments name the ceiling and upgrade path
- [ ] [DOC] `docs/architecture/SYSTEM_DESIGN.md` — verify matches actual implementation
- [ ] [DOC] `docs/architecture/DATA_FLOW.md` — verify matches actual pipeline order
- [ ] [DOC] `AGENTS.md` — update gotchas with discoveries from COG URLs, CRS handling, abstention edge cases
- [ ] [DOC] `bounds calibrate --dump-baseline` — re-baseline all manifests

---

## Phase 7 — Cleanup & Documentation (END)
**Status:** [ ]

- [ ] [BE] DRY sweep: check for duplicated masking logic across cog_reader, preparation, scene_quality; extract shared constants to `core/__init__.py`
- [ ] [DOC] Update mini-SDD tasks.md — all checkboxes crossed, progress summary written
- [ ] [DOC] Final docs review: CLAUDE.md, AGENTS.md, README.md, CONTRIBUTING.md — all current
- [ ] [DOC] Verify EvidenceBundle output shape matches forward-compatible `/v1/change` API response
- [ ] [BE] Squash feature commits into clean history
- [ ] [DOC] Write phase-end summary in Progress section below

---

### Progress

**Started:** 2026-06-21
**Phases complete:** 1—4 (Setup + STAC/Quality + COG/Preparation + Baselines/Change Detection + Evidence Bundles/Provenance)
**Key commits:** `5d41071` (scaffolding), `b0a64f6` (Phase 1), `4ad0579` (Phase 2 scene-quality SCL bridge)
**Test baseline:** 106 tests, 0 failures, 0 warnings (up from 80)
**Lint:** ruff 0 exit
**New deps:** Pillow 12.2 (image rendering)
**Bounds:** bounds CLI not in PATH — skipped
**Last plan update:** Phase 4 complete — `render_true_color`, `render_change_overlay`, `write_findings_geojson`, `build_provenance`, `render_evidence_bundle` all implemented. 18 artifact tests + 8 integration tests green. Files created: images.py, geojson.py, provenance.py, __init__.py (artifacts), test_images.py, test_geojson.py, test_provenance.py, test_evidence_bundle.py.
**Next phase:** Phase 5 — CLI Wiring + Pipeline Orchestration (orchestrator.py + cli/main.py)
