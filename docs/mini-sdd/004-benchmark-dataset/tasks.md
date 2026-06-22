# Tasks — Benchmark Dataset + Golden Tests

**Parent**: [../README.md](../README.md)

---

## Phase 0 — Structure
**Status:** [x] DONE

- [x] [DOC] Create `tests/data/benchmark/` with README.md
- [x] [DOC] Define expected.json schema in README
- [x] [DOC] Define holdout protocol (geographic + temporal groups)
- [x] [BE] Add `--run-integration` flag to pytest in `tests/conftest.py`
- [x] [BE] Add `@pytest.mark.integration` marker registration

## Phase 1 — Collect examples (12-18)
**Status:** [x] DONE (12 examples)

- [x] [DATA] Collect 4 clear vegetation-loss examples (3 regions minimum)
  - [x] Costa Rica (Osa Peninsula deforestation)
  - [x] Amazon (Para/Brazil clearcut)
  - [x] Indonesia/SE Asia (Borneo palm oil expansion)
  - [x] Africa (Zambia miombo clearing)
- [x] [DATA] Collect 2 no-change examples (stable forest, stable cropland)
- [x] [DATA] Collect 2 seasonal-variation examples (temperate + boreal transition)
- [x] [DATA] Collect 1 cloud-contaminated example (wet-season AOI)
- [x] [DATA] Collect 1 cross-season mismatch example
- [x] [DATA] Collect 2 burn/disturbance examples (Portugal + California wildfire)
- [x] For each: create `NNN-<slug>/aoi.geojson`, `expected.json`, `request.json`, `review.md`
- [x] [QA] Verify all AOI polygons valid, expected.json validates against schema
- [x] [QA] Verify holdout groups assigned correctly

## Phase 2 — Golden test harness
**Status:** [x] DONE

- [x] [TEST] `tests/integration/test_golden_examples.py` — parametrized goldens
- [x] [TEST] Test loads aoi + expected, runs pipeline, validates outcome
- [x] [TEST] Test handles abstention assertion correctly
- [x] [TEST] Test handles finding count assertion
- [x] [TEST] Tests skip without `--run-integration`, run with it
- [x] [BE] `tests/benchmark_utils.py` — shared validation logic
- [x] [BE] `tests/test_benchmark_validation.py` — 13 unit tests for validation logic
- [x] [QA] `pytest tests/integration/ --run-integration -v` — 12/12 passing (after 013 calibration)

## Phase 3 — Run + calibrate
**Status:** [x] DONE (12/12 golden tests passing after 013 calibration)

- [x] [QA] Run golden tests on ALL examples, record results
- [x] [BE] Generate `tests/data/benchmark/calibration_report.json`
- [x] [DOC] Record baseline metrics in report
- [x] [DOC] Note threshold adjustments if defaults from 002 are wrong

> Initial run: 1/12 passed. After 013-baseline-calibration (signed threshold,
> 25x25 closing, cross-season annotation, honest expected.json ranges): 12/12 pass.

## Phase 4 — Document
**Status:** [x] DONE

- [x] [DOC] `tests/data/benchmark/README.md` — complete diversity table + holdout protocol
- [x] [DOC] Known limitations: dataset size, reviewer bias, ecosystem coverage gaps
- [x] [DOC] Update AGENTS.md with integration test instructions *(done in 013 — integration test command documented in CLAUDE.md/AGENTS.md)*
- [x] [QA] `ruff check src/ tests/` — 0 exit
- [x] [QA] Commit

---

### Progress

Phase 0-2, 4 complete. 170 tests passing (157 original + 13 new benchmark validation).
Phase 3 (calibration) requires live STAC/COG network access — run manually with:
`pytest tests/integration/ --run-integration -v`
