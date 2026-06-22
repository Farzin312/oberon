# Tasks — CLI Docs + SDK Example + Design Partner Prep

**Parent**: [../README.md](../README.md)

---

## Phase 0 — README overhaul
**Status:** [ ]

- [ ] [DOC] Rewrite `README.md`:
  - What is Oberon (product statement from Blueprint)
  - Quick start (Docker + CLI)
  - CLI examples
  - Deployment options (CPU/GPU)
  - Current status + evaluation results
- [ ] [DOC] Create `ARCHITECTURE.md` from SYSTEM_DESIGN.md content + stage diagram
- [ ] [DOC] Create `ROADMAP.md` from mini-SDD overview (phase listing, decision gates, current phase)
- [ ] [DOC] Update `CLAUDE.md` with latest gotchas
- [ ] [QA] All four files exist and are internally consistent

## Phase 1 — CLI polish
**Status:** [ ]

- [ ] [BE] Review all --help text for clarity, add examples to --help
- [ ] [BE] Ensure error messages are actionable (mention --help, suggest fixes)
- [ ] [DOC] `docs/api/cli.md` — CLI reference (all commands + flags + defaults)
- [ ] [DOC] `docs/api/examples.md` — usage examples (basic, AI, Docker, programmatic)
- [ ] [QA] `oberon analyze --help` — matches docs

## Phase 2 — SDK example
**Status:** [ ]

- [ ] [BE] `oberon/__init__.py` — add `analyze(geometry, before, after, ...)` convenience function
- [ ] [TEST] `tests/cli/test_analyze.py` — test analyze() convenience function
- [ ] [BE] `examples/sdk_demo.py` — full workflow (load AOI → run analysis → print findings)
- [ ] [DOC] `examples/README.md` — how to run the demo
- [ ] [TEST] `pytest tests/cli/ -v` — convenience function passes

## Phase 3 — Public reports
**Status:** [ ]

- [ ] [DOC] `docs/EVALUATION_REPORT.md` — from 005 (baseline vs AI comparison)
- [ ] [DOC] `docs/api/gaps_vs_product_brief.md` — from 006 (API contract gaps)
- [ ] [DOC] `docs/CLAY_EXPERIMENT_REPORT.md` — from 003 (Clay experiment)
- [ ] [QA] All reports present, consistent with evaluation results

## Phase 4 — Design partner prep
**Status:** [ ]

- [ ] [DOC] `docs/partners/osa_conservation.md` — background, opportunity, approach
- [ ] [DOC] `docs/partners/mast_reforestation.md` — backtest proposal
- [ ] [DOC] `docs/partners/blue_forest.md` — portfolio evidence pilot
- [ ] [DOC] All partner docs reference Blueprint §4 org research

## Phase 5 — PDF vaulting
**Status:** [ ]

- [ ] [DOC] Copy Desktop/Oberon PDFs to `docs/planning/` directory
- [ ] [DOC] Add README.md to docs/planning/ referencing each PDF
- [ ] [QA] PDFs committed, not .gitignored, accessible from repo

## Phase 6 — QA gate
**Status:** [ ]

- [ ] [QA] `ruff check src/ tests/` — 0 exit
- [ ] [QA] Full test suite: `pytest tests/ -q` — baseline held
- [ ] [QA] Integration tests: `pytest tests/integration/ --run-integration -q` — passes
- [ ] [QA] Final git log review — clean history
- [ ] [QA] Commit: `docs: 009 launch prep — CLI docs + SDK + partner materials`

---

### Progress

_None yet. Depends on 005 (evaluation results) + 006 (contracts stable) + 007 (Docker) + 008 (optional)._
