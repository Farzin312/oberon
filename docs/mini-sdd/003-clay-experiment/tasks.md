# Tasks — Clay Feature Extraction Experiment

**Parent**: [../README.md](../README.md)

---

## Phase 0 — Adapter protocol
**Status:** [ ]

- [ ] [BE] `src/oberon/ai/__init__.py` — package init
- [ ] [BE] `src/oberon/ai/model_adapter.py` — ModelAdapter Protocol + ModelResult dataclass
- [ ] [BE] `src/oberon/core/__init__.py` — export ModelResult
- [ ] [TEST] `tests/ai/test_model_adapter.py` — ModelResult construction + abstention
- [ ] [QA] ruff 0; pytest green; mypy 0

## Phase 1 — Install + smoke test
**Status:** [ ]

- [ ] [BE] Add `torch`, `clay-foundation-model` to `[ai]` extras in pyproject.toml
- [ ] [BE] Install extras: `uv sync --extra ai`
- [ ] [BE] Run Clay's own Sentinel-2 inference example (256x256, 10 bands)
- [ ] [BE] Record exact Clay version, model config in `src/oberon/ai/clay_config.py`
- [ ] [QA] Smoke test: Clay produces 1024-dim embedding from synthetic 10-band chip
- [ ] [DOC] Update AGENTS.md with install instructions

## Phase 2 — Tiled inference
**Status:** [ ]

- [ ] [TEST] `tests/ai/test_tiled_inference.py` — chipping produces correct grid for known AOI size
- [ ] [TEST] `tests/ai/test_tiled_inference.py` — stitching reconstructs original dimensions
- [ ] [TEST] `tests/ai/test_tiled_inference.py` — zero-padding handles AOI edges
- [ ] [TEST] `tests/ai/test_tiled_inference.py` — feathered overlap produces seamless output
- [ ] [BE] `src/oberon/ai/tiled_inference.py` — chip AOI into grid, batch inference, stitch

## Phase 3 — Clay adapter + feature-diff
**Status:** [ ]

- [ ] [TEST] `tests/ai/test_clay_adapter.py` — adapter returns correct embedding dims (mocked)
- [ ] [TEST] `tests/ai/test_clay_adapter.py` — adapter records model + adapter version
- [ ] [TEST] `tests/ai/test_clay_adapter.py` — feature diff on identical features ≈ 0
- [ ] [TEST] `tests/ai/test_clay_adapter.py` — feature diff on very different features > 0
- [ ] [TEST] `tests/ai/test_clay_adapter.py` — abstention when features are None
- [ ] [BE] `src/oberon/ai/clay_adapter.py` — ClayAdapter conforming to ModelAdapter
- [ ] [BE] `src/oberon/ai/clay_adapter.py` — compute_feature_diff(before, after) -> diff_map

## Phase 4 — Wire into orchestrator
**Status:** [ ]

- [ ] [BE] `src/oberon/cli/main.py` — add `--use-ai` flag (default: False)
- [ ] [BE] `src/oberon/cli/orchestrator.py` — AI branch behind flag, runs parallel to baseline
- [ ] [BE] `src/oberon/artifacts/provenance.py` — model_version, adapter_version in manifest
- [ ] [TEST] `tests/cli/test_analyze.py` — --use-ai flag presence
- [ ] [TEST] `tests/cli/test_analyze.py` — --use-ai without torch gives graceful error
- [ ] [QA] ruff 0; pytest green; mypy 0

## Phase 5 — Run experiment + report
**Status:** [ ]

- [ ] [QA] Run `oberon analyze --use-ai` on the sample.geojson with wide dates
- [ ] [QA] Examine: does feature-diff map correlate with NDVI delta?
- [ ] [QA] Record: inference time per chip (CPU), total for benchmark
- [ ] [DOC] Write `docs/CLAY_EXPERIMENT_REPORT.md`:
  - Did Clay produce a sensible change map?
  - Correlation with NDVI delta?
  - Latency numbers
  - Recommendation: PROCEED to 005 / PROCEED WITH CAUTION / STOP
- [ ] [DOC] Update AGENTS.md with experiment conclusions

---

### Progress

_None yet. Depends on 002-baseline-fixes._
