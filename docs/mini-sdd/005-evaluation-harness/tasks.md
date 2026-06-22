# Tasks — Full AI Evaluation + Baseline Comparison

**Parent**: [../README.md](../README.md)

---

## Phase 0 — Comparison harness
**Status:** [ ]

- [ ] [BE] `src/oberon/ai/comparison.py` — ComparisonReport dataclass
- [ ] [BE] `src/oberon/ai/comparison.py` — compute_metrics() function
- [ ] [BE] `src/oberon/ai/comparison.py` — evaluate() runs baseline+AI on benchmark
- [ ] [BE] `scripts/run_evaluation.py` — CLI entry point
- [ ] [TEST] `tests/ai/test_comparison.py` — precision@K with known inputs
- [ ] [TEST] `tests/ai/test_comparison.py` — recall@K with known inputs
- [ ] [TEST] `tests/ai/test_comparison.py` — fp_rate edge case (0 findings)
- [ ] [TEST] `tests/ai/test_comparison.py` — abstention accuracy
- [ ] [QA] ruff 0; pytest green; mypy 0

## Phase 1 — Baseline run
**Status:** [ ]

- [ ] [QA] Run `scripts/run_evaluation.py --baseline-only` on 004 benchmark
- [ ] [QA] Record per-example baseline results
- [ ] [QA] Compute aggregate baseline metrics

## Phase 2 — AI run
**Status:** [ ]

- [ ] [QA] Run `scripts/run_evaluation.py --ai-enabled` on same benchmark
- [ ] [QA] Record per-example AI results
- [ ] [QA] Compute aggregate AI metrics

## Phase 3 — Comparison
**Status:** [ ]

- [ ] [QA] Compute AI vs baseline delta for every metric
- [ ] [QA] Compute per-holdout-group breakdown
- [ ] [QA] Compute confidence intervals (bootstrap or analytic)
- [ ] [QA] Produce final ComparisonReport

## Phase 4 — Decision gate
**Status:** [ ]

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

_None yet. Depends on 003-clay-experiment + 004-benchmark-dataset._
