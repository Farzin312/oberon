# Tasks — Benchmark Dataset + Golden Tests

**Parent**: [../README.md](../README.md)

---

## Phase 0 — Structure
**Status:** [ ]

- [ ] [DOC] Create `tests/data/benchmark/` with README.md
- [ ] [DOC] Define expected.json schema in README
- [ ] [DOC] Define holdout protocol (geographic + temporal groups)
- [ ] [BE] Add `--run-integration` flag to pytest in `tests/conftest.py`
- [ ] [BE] Add `@pytest.mark.integration` marker registration

## Phase 1 — Collect examples (12-18)
**Status:** [ ]

- [ ] [DATA] Collect 4-6 clear vegetation-loss examples (3 regions minimum)
  - [ ] Costa Rica (e.g., Osa Peninsula deforestation)
  - [ ] Amazon (e.g., Pará/Brazil clearcut)
  - [ ] Indonesia/SE Asia (e.g., palm oil expansion)
  - [ ] Africa (e.g., Zambia miombo clearing)
- [ ] [DATA] Collect 2-3 no-change examples (stable forest, stable agriculture)
- [ ] [DATA] Collect 2 seasonal-variation examples (temperate forest transition)
- [ ] [DATA] Collect 1 cloud-contaminated example (wet-season AOI)
- [ ] [DATA] Collect 1 cross-season mismatch example
- [ ] [DATA] Collect 1-2 burn/disturbance examples (wildfire scar)
- [ ] For each: create `NNN-<slug>/aoi.geojson`, `expected.json`, `review.md`
- [ ] [QA] Verify all AOI polygons valid, expected.json validates against schema
- [ ] [QA] Verify holdout groups assigned correctly

## Phase 2 — Golden test harness
**Status:** [ ]

- [ ] [TEST] `tests/integration/test_golden_examples.py` — parametrized goldens
- [ ] [TEST] Test loads aoi + expected, runs pipeline, validates outcome
- [ ] [TEST] Test handles abstention assertion correctly
- [ ] [TEST] Test handles finding count assertion
- [ ] [TEST] Tests skip without `--run-integration`, run with it
- [ ] [BE] `tests/conftest.py` — benchmark dir auto-discovery
- [ ] [QA] `pytest tests/integration/ --run-integration -v` — verified pass on 5+ examples

## Phase 3 — Run + calibrate
**Status:** [ ]

- [ ] [QA] Run golden tests on ALL examples, record results
- [ ] [BE] Generate `tests/data/benchmark/calibration_report.json`
- [ ] [DOC] Record baseline metrics in report
- [ ] [DOC] Note threshold adjustments if defaults from 002 are wrong

## Phase 4 — Document
**Status:** [ ]

- [ ] [DOC] `tests/data/benchmark/README.md` — complete diversity table + holdout protocol
- [ ] [DOC] Known limitations: dataset size, reviewer bias, ecosystem coverage gaps
- [ ] [DOC] Update AGENTS.md with integration test instructions
- [ ] [DOC] Update DATA_FLOW.md with integration test section
- [ ] [QA] `ruff check src/ tests/` — 0 exit
- [ ] [QA] Commit

---

### Progress

_None yet. Depends on 002-baseline-fixes._
