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
**Status:** [ ] DEFERRED (requires live STAC network access)

- [ ] [QA] Run `scripts/run_evaluation.py --baseline-only` on 004 benchmark
- [ ] [QA] Record per-example baseline results
- [ ] [QA] Compute aggregate baseline metrics

## Phase 2 — AI run
**Status:** [ ] DEFERRED (requires live STAC + Clay checkpoint)

- [ ] [QA] Run `scripts/run_evaluation.py --ai-enabled` on same benchmark
- [ ] [QA] Record per-example AI results
- [ ] [QA] Compute aggregate AI metrics

## Phase 3 — Comparison
**Status:** [ ] DEFERRED (depends on Phase 1+2)

- [ ] [QA] Compute AI vs baseline delta for every metric
- [ ] [QA] Compute per-holdout-group breakdown
- [ ] [QA] Compute confidence intervals (bootstrap or analytic)
- [ ] [QA] Produce final ComparisonReport

## Phase 4 — Decision gate
**Status:** [ ] DEFERRED (depends on Phase 3)

- [ ] [DOC] Write `docs/EVALUATION_REPORT.md` with:
  - Executive summary (which column wins?)
  - Full metrics table
  - Per-geography breakdown
  - Per-season breakdown
  - Limitations and caveats
  - Clear decision: AI_wins / AI_ties / AI_loses / insufficient_data
- [ ] [DOC] If AI_wins: update SYSTEM_DESIGN.md AI branch, update AGENTS.md
- [ ] [DOC] If AI_loses: document "deterministic-only" in README, keep --use-ai experimental
- [ ] [DOC] Either way: publish report, commit
- [ ] [QA] `ruff check src/ tests/` — 0 exit
- [ ] [QA] Commit

---

### Progress

Phase 0 complete. 196 tests passing (157 original + 13 benchmark + 26 comparison).
26 new tests: precision/recall/fp_rate/abstention metrics, compute_metrics aggregation,
evaluate() decision gate logic, format_report markdown output.

Phases 1-4 require live STAC/COG network + Clay checkpoint — run manually with:
  `uv run python scripts/run_evaluation.py --both`
