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
**Status:** [ ]

**COG reader — windowed reads from cloud-optimized GeoTIFFs**

- [ ] [TEST] `tests/pipeline/test_cog_reader.py` — test `read_window` returns dict of band arrays with correct keys and shapes for a mocked COG window
- [ ] [TEST] `tests/pipeline/test_cog_reader.py` — test 404 COG URL raises `FileNotFoundError` with scene ID
- [ ] [TEST] `tests/pipeline/test_cog_reader.py` — test missing band in assets returns partial dict (available bands only)
- [ ] [TEST] `tests/pipeline/test_cog_reader.py` — test empty band list raises `ValueError`
- [ ] [TEST] `tests/pipeline/test_cog_reader.py` — test buffer_pixels=1 adds correct padding to window dimensions
- [ ] [BE] `src/oberon/pipeline/cog_reader.py` — implement `read_window(scene, aoi_geom, bands, buffer=1) -> RasterWindow`

**SCL masking — composite mask from Scene Classification Layer**

- [ ] [TEST] `tests/pipeline/test_preparation.py` — test `build_valid_mask` combines SCL invalid bits + nodata (0) correctly
- [ ] [TEST] `tests/pipeline/test_preparation.py` — test missing SCL falls back to nodata-only mask with warning flag
- [ ] [TEST] `tests/pipeline/test_preparation.py` — test all-pixels-obstructed returns `(all_false_mask, "AOI fully obstructed")`
- [ ] [BE] `src/oberon/pipeline/preparation.py` — implement `build_valid_mask(window) -> tuple[mask, reason]`

**Preparation — reproject, resample, crop**

- [ ] [TEST] `tests/pipeline/test_preparation.py` — test `align_to_common_grid` returns before/after with same shape, same CRS
- [ ] [TEST] `tests/pipeline/test_preparation.py` — test before/after from different CRS reprojected correctly to centroid UTM zone
- [ ] [TEST] `tests/pipeline/test_preparation.py` — test intersection bounds cropping (crops to overlap region)
- [ ] [TEST] `tests/pipeline/test_preparation.py` — test resampled dimension < 10px returns PreparedPair with is_usable=False
- [ ] [TEST] `tests/pipeline/test_preparation.py` — test 20m bands bilinearly upsampled to 10m (shape matches 10m bands)
- [ ] [TEST] `tests/pipeline/test_preparation.py` — test SCL band nearest-neighbor resampled (not bilinear)
- [ ] [BE] `src/oberon/pipeline/preparation.py` — implement `align_to_common_grid(before, after, target_crs, target_resolution=10) -> PreparedPair`
- [ ] [BE] `src/oberon/pipeline/preparation.py` — add `PreparedPair.is_usable` property (>= 30% valid)

**Quality bridge upgrade**

- [ ] [BE] `src/oberon/pipeline/scene_quality.py` — upgrade `assess_scene` to use `read_window` for SCL when COG reader exists

**QA gate**

- [ ] [QA] `ruff check src/ tests/` — 0 exit; Phase 2 tests green
- [ ] [QA] `bounds validate --quick` — clean
- [ ] [DOC] Update `AGENTS.md` with COG URL pattern gotcha if discovered

> **Gate note:** All prepared arrays must have the same CRS, the same shape, and the same bounds. If any differ, the transformation is broken.

---

## Phase 3 — Baseline Analytics + Change Detection
**Status:** [ ]

**Baseline computation — complete wiring of stubs**

- [ ] [TEST] `tests/core/test_baselines.py` — test `compute_all` returns abstention when `pair.is_usable` is False
- [ ] [TEST] `tests/core/test_baselines.py` — test all bands present computes NDVI + NBR + NDMI + abstention check
- [ ] [TEST] `tests/core/test_baselines.py` — test missing SWIR bands (B11, B12) produces NDMI=None, NBR=None gracefully
- [ ] [TEST] `tests/core/test_baselines.py` — test all-zero arrays produce NDVI of 0.0 (NIR=0, Red=0 → division guard = epsilon)
- [ ] [TEST] `tests/core/test_baselines.py` — test NIR-saturated values (10000) produce NDVI near 0.0 with Red near 10000
- [ ] [TEST] `tests/core/test_baselines.py` — test fully masked pair returns `BaselineResult(abstain=True)`
- [ ] [BE] `src/oberon/core/baselines.py` — wire `compute_all(pair) -> BaselineResult` using existing compute_* functions

**Change detection — complete wiring of stubs**

- [ ] [TEST] `tests/core/test_change_detection.py` — test `extract_findings` with no change mask returns empty list
- [ ] [TEST] `tests/core/test_change_detection.py` — test single connected component produces one Finding with correct area
- [ ] [TEST] `tests/core/test_change_detection.py` — test multiple components with only one above min_pixels returns 1 Finding
- [ ] [TEST] `tests/core/test_change_detection.py` — test component below min_change_area (49px) is filtered out
- [ ] [TEST] `tests/core/test_change_detection.py` — test `deduplicate_and_rank` returns findings sorted by score descending
- [ ] [TEST] `tests/core/test_change_detection.py` — test `deduplicate_and_rank` with 25 findings caps at max_findings=20
- [ ] [TEST] `tests/core/test_change_detection.py` — test geometry is valid GeoJSON Polygon (exterior ring)
- [ ] [TEST] `tests/core/test_change_detection.py` — test all-zero scores returns empty result
- [ ] [BE] `src/oberon/core/change_detection.py` — implement `_component_to_geojson_polygon` using shapely `convex_hull` (replaces bbox polygon)
- [ ] [BE] `src/oberon/core/change_detection.py` — implement `deduplicate_and_rank(findings, max_findings=20) -> list[Finding]`
- [ ] [BE] `src/oberon/core/change_detection.py` — wire all functions into a combined `detect_changes(pair, threshold, min_pixels) -> list[Finding]`

**QA gate**

- [ ] [QA] `ruff check src/ tests/` — 0 exit; Phase 3 tests green
- [ ] [QA] `bounds validate --quick` — clean

---

## Phase 4 — Evidence Bundles + Provenance
**Status:** [ ]

**True-color imagery**

- [ ] [TEST] `tests/artifacts/test_images.py` — test `render_true_color` produces a valid PNG at output path
- [ ] [TEST] `tests/artifacts/test_images.py` — test all-zero bands produce valid PNG (0 → 0 after 2% clip)
- [ ] [TEST] `tests/artifacts/test_images.py` — test all-10000 bands produce valid PNG (10000 → 255 after 98% clip)
- [ ] [TEST] `tests/artifacts/test_images.py` — test `render_change_overlay` produces PNG with red overlay on before image
- [ ] [BE] `src/oberon/artifacts/images.py` — implement `render_true_color(red, green, blue, path) -> Path` using PIL/Pillow
- [ ] [BE] `src/oberon/artifacts/images.py` — implement `render_change_overlay(before_rgb, change_mask, path) -> Path`

**GeoJSON findings**

- [ ] [TEST] `tests/artifacts/test_geojson.py` — test `write_findings_geojson` produces valid GeoJSON FeatureCollection
- [ ] [TEST] `tests/artifacts/test_geojson.py` — test empty findings list produces FeatureCollection with 0 features (valid GeoJSON)
- [ ] [TEST] `tests/artifacts/test_geojson.py` — test each feature has geometry + all required properties
- [ ] [TEST] `tests/artifacts/test_geojson.py` — test findings in different CRS are reprojected to EPSG:4326
- [ ] [BE] `src/oberon/artifacts/geojson.py` — implement `write_findings_geojson(findings, path, out_crs="EPSG:4326") -> Path`

**Provenance manifest**

- [ ] [TEST] `tests/core/test_provenance.py` — test `build_provenance` manifest contains all required fields from the schema
- [ ] [TEST] `tests/core/test_provenance.py` — test abstention case produces manifest with abstention populated and no findings
- [ ] [TEST] `tests/core/test_provenance.py` — test empty findings produces valid manifest with empty_findings flag
- [ ] [TEST] `tests/core/test_provenance.py` — test manifest includes software versions for all key deps
- [ ] [BE] `src/oberon/artifacts/provenance.py` — implement `build_provenance(findings, bundle, request, scenes) -> dict`

**Output directory management**

- [ ] [BE] `src/oberon/artifacts/__init__.py` — add `create_output_dir(path: Path) -> Path` that creates dir and returns it
- [ ] [BE] `src/oberon/artifacts/__init__.py` — add `build_evidence_bundle(findings, pair, request, scenes, output_dir) -> EvidenceBundle`

**QA gate**

- [ ] [QA] `ruff check src/ tests/` — 0 exit; Phase 4 tests green
- [ ] [QA] `bounds validate --quick` — clean
- [ ] [QA] Manual inspection: output PNG is valid, GeoJSON is valid JSON

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
**Phases complete:** 1 (Setup + STAC Discovery + Scene Quality)
**Key commits:** `5d41071` (scaffolding), `b0a64f6` (Phase 1 implementation)
**Test baseline:** 41 tests, 0 failures, 0 warnings
**Lint:** ruff 0 exit
**Bounds:** 17 files owned, 4 subsystems, validate clean
**Last plan update:** All phases 2-7 fully scoped with data contracts, abstention rules, edge cases, and bite-sized TDD tasks (2026-06-21)
**Next phase:** Phase 2 — COG Reading + Preparation
**What's needed:** Clear context, fresh agent picks up Phase 2 from tasks.md
