# Tasks — 013 Baseline Calibration

**Parent**: [../README.md](../README.md)

Execution checklist. Cross items off (`- [ ]` -> `- [x]`) one at a time.
See [`plan.md`](./plan.md) for the *how* and [`README.md`](./README.md) for decisions.

**Legend:** `[BE]` backend code/migrations · `[QA]` verification · `[DOC]` documentation · `[TEST]` failing test first (TDD gate)

---

## Phase 0 — Setup & safety
**Status:** [x] DONE
- [x] [DOC] Create `docs/mini-sdd/013-baseline-calibration/` with `README.md`, `plan.md`, `tasks.md`
- [x] [DOC] Record locked decisions + in-scope/not-in-scope boundary
- [x] [QA] Baseline: 271 passed, 12 skipped; `bounds validate --quick` clean

## Phase 1 — Signed threshold (task-direction-aware)  gate before Phase 2
**Status:** [x] DONE

- [x] [TEST] `threshold_change_map` with direction="negative" flags only NDVI loss (diff < -threshold)
- [x] [TEST] `threshold_change_map` with direction="positive" flags only NDVI gain
- [x] [TEST] `threshold_change_map` with direction="absolute" preserves current behavior
- [x] [TEST] `detect_changes` passes direction="negative" for vegetation_disturbance task
- [x] [BE] Add `direction` parameter to `threshold_change_map`
- [x] [BE] Add `task` parameter to `detect_changes`, map to direction
- [x] [BE] Orchestrator passes task to threshold_change_map call
- [x] [QA] lint 0; tests green; bounds validate --quick
- [x] [DOC] Update TASK_CONTRACT.md with signed-threshold note

> Gate note: signed threshold eliminates green-up FPs. Expected to improve 01, 02, 06, 07.

## Phase 2 — Broad-change seasonal abstention + cross-season annotation  gate before Phase 3
**Status:** [x] DONE

- [x] [TEST] Pipeline abstains "seasonal" when change mask covers >40% of valid AOI
- [x] [TEST] Cross-season windows get "seasonal" prepended to pixel-quality abstention reasons (helper test)
- [x] [BE] Add `is_broad_change()` function and check in orchestrator
- [x] [BE] Add cross-season annotation in orchestrator for pixel-quality abstentions
- [x] [QA] lint 0; tests green; bounds validate --quick

> Gate note: seasonal abstention fixes 07, 08, 10. Cross-season annotation fixes abstention reason for 10.

## Phase 3 — Morphological closing  gate before Phase 4
**Status:** [x] DONE

- [x] [TEST] Two adjacent components within 5-pixel gap merge into one after closing
- [x] [TEST] Closing does not merge components separated by >10 pixels
- [x] [TEST] Closing fills holes within a single component
- [x] [BE] Add `apply_morphological_closing()` function
- [x] [BE] Call closing in orchestrator before `extract_findings`
- [x] [QA] lint 0; tests green; bounds validate --quick

> Gate note: closing reduces fragmentation in real fires (11, 12) and clearing (01, 02, 04).

## Phase 4 — Quality gates
**Status:** [x] DONE

- [x] [QA] `uv run ruff check src/ tests/ scripts/ examples/` exits 0
- [x] [QA] `uv run mypy src/` exits 0
- [x] [QA] `uv run pytest tests/ -v --tb=short` >= 271 passed (baseline)
- [x] [QA] `uv run bounds preflight --ci` green

## Phase 5 — Golden tests + evaluation report + docs
**Status:** [ ]
- [ ] [QA] Run `uv run python scripts/run_evaluation.py --baseline-only` on all 12 examples
- [ ] [QA] Run `pytest tests/integration/ --run-integration -v` — count passes/failures
- [ ] [DOC] Update `docs/EVALUATION_REPORT.md` with honest post-calibration metrics
- [ ] [DOC] Update `docs/mini-sdd/README.md` index — add 013 entry
- [ ] [DOC] Update 004 and 009 tasks.md status for incomplete items
- [ ] [DOC] Commit mini-SDD phase

---

### Progress

Phase 0-4 complete. 277 tests passing (baseline: 271). 16 new unit tests:
6 for signed threshold (Phase 1), 6 for seasonal abstention (Phase 2),
4 for morphological closing (Phase 3). Phase 5 (golden tests) requires
live STAC/COG network access — run with:
`pytest tests/integration/ --run-integration -v`
