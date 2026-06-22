# Tasks — Full AI Evaluation + Baseline Comparison

**Parent**: [../README.md](../README.md)

---

## Phase 0 — Comparison harness
**Status:** [x] DONE

- [x] [BE] `src/oberon/ai/comparison.py` — ExampleResult dataclass
- [x] [BE] `src/oberon/ai/comparison.py` — ComparisonReport dataclass
- [x] [BE] `src/oberon/ai/comparison.py` — compute_metrics() function
- [x] [BE] `src/oberon/ai/comparison.py` — evaluate() runs baseline+AI comparison, produces decision
- [x] [BE] `src/oberon/ai/comparison.py` — format_report() for markdown output
- [x] [BE] `src/oberon/ai/__init__.py` — export comparison module
- [x] [BE] `scripts/run_evaluation.py` — CLI entry point (--baseline-only / --ai-enabled / --both)
- [x] [TEST] `tests/ai/test_comparison.py` — precision@K with known inputs (4 tests)
- [x] [TEST] `tests/ai/test_comparison.py` — recall@K with known inputs (4 tests)
- [x] [TEST] `tests/ai/test_comparison.py` — fp_rate edge case (4 tests)
- [x] [TEST] `tests/ai/test_comparison.py` — abstention accuracy (4 tests)
- [x] [TEST] `tests/ai/test_comparison.py` — compute_metrics aggregation (3 tests)
- [x] [TEST] `tests/ai/test_comparison.py` — evaluate decision gate (6 tests)
- [x] [TEST] `tests/ai/test_comparison.py` — format_report markdown (1 test)
- [x] [QA] ruff 0; pytest green; mypy 0

## Phase 1 — Baseline run
**Status:** [x] DONE

- [x] [QA] Run `scripts/run_evaluation.py --baseline-only` on 004 benchmark
- [x] [QA] Record per-example baseline results
- [x] [QA] Compute aggregate baseline metrics

## Phase 2 — AI run
**Status:** [x] DONE

- [x] [QA] Run `scripts/run_evaluation.py --ai-enabled` on same benchmark
- [x] [QA] Record per-example AI results
- [x] [QA] Compute aggregate AI metrics

## Phase 3 — Comparison
**Status:** [x] DONE

- [x] [QA] Compute AI vs baseline delta for every metric
- [x] [QA] Compute per-holdout-group breakdown
- [x] [QA] Document confidence limitation (12 examples is not statistically powered)
- [x] [QA] Produce final ComparisonReport

## Phase 4 — Decision gate
**Status:** [x] DONE

- [x] [DOC] Write `docs/EVALUATION_REPORT.md` with:
  - Executive summary (which column wins?)
  - Full metrics table
  - Per-geography breakdown
  - Per-season breakdown
  - Limitations and caveats
  - Clear decision: AI_wins / AI_ties / AI_loses / insufficient_data
- [ ] [DOC] If AI_wins: update SYSTEM_DESIGN.md AI branch, update AGENTS.md
- [x] [DOC] If AI_ties: document deterministic-first in README, keep --use-ai experimental
- [x] [DOC] Either way: publish report
- [x] [QA] `ruff check src/ tests/ scripts/ examples/`; `mypy src/`; `pytest tests/ -v --tb=short`; `bounds preflight --ci` — 0 exit
- [x] [QA] Commit

---

### Progress

Phases 1-4 completed from live STAC/COG run on 2026-06-22.

Decision: AI_ties. Baseline `precision_at_k` 0.1266, AI `precision_at_k` 0.1266, delta +0.0000. AI remains experimental. The benchmark exposed high false positives and weak seasonal/no-change handling; those are calibration work, not AI-promotion evidence.
