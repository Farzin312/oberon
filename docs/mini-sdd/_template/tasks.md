# Tasks — {{Title}}

**Parent**: [../README.md](../README.md)

Execution checklist. Cross items off (`- [ ]` → `- [x]`) one at a time.
See [`plan.md`](./plan.md) for the *how* and [`README.md`](./README.md) for decisions.

**Legend:** `[BE]` backend code/migrations · `[QA]` verification · `[DOC]` documentation · `[TEST]` failing test first (TDD gate)

---

## Phase 0 — Setup & safety
**Status:** [ ]
- [ ] [DOC] Create `docs/mini-sdd/{{slug}}/` with `README.md`, `plan.md`, `tasks.md`
- [ ] [DOC] Record locked decisions + in-scope/not-in-scope boundary
- [ ] [QA] Baseline: test count recorded; `bounds validate --quick` clean

## Phase 1 — {{First slice}}  ⚠️ gate before Phase 2
**Status:** [ ]
- [ ] [TEST] {{failing test for the behavior, per plan.md §4.x}}
- [ ] [BE] {{exact change per plan.md §4.x}}
- [ ] [QA] lint 0; tests green; bounds validate --quick; code review
- [ ] [DOC] Update affected docs

> {{Gate note: record the verified result when the phase closes.}}

## Phase 2 — {{Next area}}
**Status:** [ ]
- [ ] [TEST] {{...}}
- [ ] [BE] {{...}}
- [ ] [QA] {{...}}

## Phase N-1 — Verify & QA
**Status:** [ ]
- [ ] [QA] `ruff check src/ tests/` exits 0; full `pytest tests/ -q` ≥ baseline
- [ ] [QA] `bounds preflight --ci` green
- [ ] [QA] Code review — zero open blocking items

## Phase N — Cleanup & doc sync (END)
**Status:** [ ]
- [ ] [BE] DRY sweep per plan.md §6 — behavior-preserving only
- [ ] [DOC] Permanent docs synced with new state (same change, not follow-up)
- [ ] [DOC] Re-baseline bounds manifest if public surface changed

---

### Progress
{{Running summary: phases done, key commits, baseline counts held, what remains.}}
