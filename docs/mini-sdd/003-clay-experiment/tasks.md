# Tasks — Clay Feature Extraction Experiment

**Parent**: [../README.md](../README.md)

---

## Phase 0 — Adapter protocol
**Status:** [x] DONE

- [x] [BE] `src/oberon/ai/__init__.py` — package init
- [x] [BE] `src/oberon/ai/model_adapter.py` — ModelAdapter Protocol + runtime_checkable
- [x] [BE] `src/oberon/core/__init__.py` — export ModelResult
- [x] [TEST] `tests/ai/test_model_adapter.py` — 9 tests (ModelResult construction, abstention, protocol conformance, feature diff)
- [x] [QA] ruff 0; pytest green; mypy 0

## Phase 1 — Install + smoke test
**Status:** [x] DONE — Clay runs on CPU

- [x] [BE] torch 2.12.1 + clay-foundation-model installed via uv
- [x] [BE] DINOv2 teacher model downloaded (vit_large_patch14_reg4_dinov2.lvd142m)
- [x] [BE] Clay v1.5 checkpoint downloaded (~5GB from HuggingFace)
- [x] [BE] Forward pass verified: 12-band 256x256 -> 1025 patch embeddings (1024-dim each)
- [x] [BE] Encoder-only feature extraction: 0.61s/chip on CPU
- [x] [BE] `src/oberon/ai/clay_config.py` — all Clay constants isolated

## Phase 2 — Tiled inference
**Status:** [x] DONE

- [x] [TEST] `tests/ai/test_tiled_inference.py` — 8 tests (grid, extract, stitch)
- [x] [BE] `src/oberon/ai/tiled_inference.py` — chip grid, reflect-pad extract, stitch

## Phase 3 — Clay adapter + feature-diff
**Status:** [x] DONE

- [x] [BE] `src/oberon/ai/clay_adapter.py` — ClayAdapter (lazy model load, encoder-only)
- [x] [TEST] `tests/ai/test_clay_adapter.py` — 9 tests (protocol, feature diff, normalization)

## Phase 4 — Wire into orchestrator
**Status:** [x] DONE

- [x] [BE] `src/oberon/cli/main.py` — `--use-ai` flag
- [x] [BE] `src/oberon/cli/orchestrator.py` — `_run_ai_branch()` (graceful fallback)
- [x] [TEST] `tests/cli/test_analyze.py` — --use-ai flag presence
- [x] [QA] ruff 0; pytest green (157 pass); mypy 0

## Phase 5 — Run experiment + report
**Status:** [x] DONE

- [x] [DOC] `docs/CLAY_EXPERIMENT_REPORT.md` — findings, latency, recommendation
- [x] [DOC] Recommendation: PROCEED WITH CAUTION to 005

---

### Progress

Mini-SDD 003 complete. 131 -> 157 tests. Clay v1.5 runs on CPU.
ModelAdapter protocol + ClayAdapter + tiled inference + --use-ai flag
all working. Feature-diff math verified. Real-data evaluation deferred
to 004 (benchmark dataset) + 005 (evaluation harness).
