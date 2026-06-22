# Testing Guide

**Parent**: [README.md](../README.md)

## Philosophy

Oberon follows Test-Driven Development (TDD) for all non-trivial logic. If you didn't watch the test fail, it doesn't count.

## Test layers

| Layer | What it covers | Location | Command |
|-------|---------------|----------|---------|
| Unit | Deterministic ops: index calc, masks, geometry, ranking, provenance | `tests/core/` | `pytest tests/core/ -v` |
| Golden | Fixed real examples with approved outputs | `tests/pipeline/` | `pytest tests/pipeline/ -v --golden` |
| Integration | STAC query → scene selection, COG read → preparation, pipeline stages | `tests/pipeline/` | `pytest tests/pipeline/ -v --integration` |
| E2E | Complete public example: job → artifacts → provenance | `tests/cli/` | `pytest tests/cli/ -v --e2e` |
| Failure | Invalid polygons, missing data, clouds, network errors | `tests/core/` | `pytest tests/core/ -v --failure` |

## TDD rules

1. **Write failing test first.** One behavior per test. Clear descriptive name.
2. **Verify RED.** Run the test. Confirm it fails for the right reason (feature missing, not typo).
3. **Write minimal code.** The simplest thing that makes the test pass.
4. **Verify GREEN.** Run the test. Confirm it passes. Run full suite for regressions.
5. **Refactor.** Clean up, keep tests green throughout.

**Violation**: If a test passes on first run, you didn't write it first. Delete the code and start over.

## Test file structure

```
tests/
├── core/
│   ├── test_scene_selection.py
│   ├── test_quality_masking.py
│   ├── test_baselines.py
│   ├── test_geometry.py
│   ├── test_provenance.py
│   └── test_ranking.py
├── pipeline/
│   ├── test_stac_discovery.py
│   ├── test_cog_reading.py
│   ├── test_preparation.py
│   └── test_evidence_bundles.py
├── cli/
│   └── test_analyze.py
├── data/
│   ├── sample.geojson
│   └── small_cog.tif
└── conftest.py
```

## Markers

```
pytest -m unit       # fast, no network
pytest -m integration # requires network (STAC, COG URLs)
pytest -m e2e        # full pipeline run
pytest -m failure    # edge case / error tests
pytest -m golden     # fixed-output regression tests
```
