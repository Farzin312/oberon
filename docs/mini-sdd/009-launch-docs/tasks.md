# Tasks — CLI Docs + SDK Example + Design Partner Prep

**Parent**: [../README.md](../README.md)

---

## Phase 0 — README overhaul
**Status:** [x] DONE

- [x] [DOC] Rewrite `README.md`: product statement, quick start (Docker + CLI + uv), CLI examples, deployment options, status
- [x] [DOC] Create `ARCHITECTURE.md` — four-plane model, pipeline flow diagram, source layout, design decisions
- [x] [DOC] Create `ROADMAP.md` — build sequence, decision gates, current status
- [x] [DOC] `CLAUDE.md` updated with API contracts section (008 commit)
- [x] [QA] All four files exist and are internally consistent

## Phase 1 — CLI polish
**Status:** [x] DONE

- [x] [BE] Review all --help text for clarity, add examples to --help
- [x] [BE] Ensure error messages are actionable (mention --help, suggest fixes)
- [x] [DOC] `docs/api/cli.md` — CLI reference (all commands + flags + defaults)
- [x] [DOC] `docs/api/examples.md` — usage examples (basic, AI, Docker, programmatic)
- [x] [QA] `oberon analyze --help` — matches docs

## Phase 2 — SDK example
**Status:** [x] DONE

- [x] [BE] `examples/sdk_demo.py` — full workflow (load AOI -> run analysis -> print findings -> API serialization demo)
- [x] [DOC] `examples/README.md` — how to run the demo + inline example for custom scripts
- [ ] [TEST] `tests/cli/test_analyze.py` — test analyze() convenience function (deferred: no analyze() wrapper added, pipeline API used directly)

## Phase 3 — Public reports
**Status:** [x] DONE

- [x] [DOC] `docs/CLAY_EXPERIMENT_REPORT.md` — from 003 (Clay experiment) — already existed, verified present
- [x] [DOC] `docs/api/gaps_vs_product_brief.md` — from 006 (API contract gaps) — already existed, updated in 008
- [x] [DOC] `docs/EVALUATION_REPORT.md` — from 005 + 013 calibration results
- [x] [QA] Available reports present, consistent with evaluation results

## Phase 4 — Design partner prep
**Status:** [ ]

- [ ] [DOC] `docs/partners/osa_conservation.md` — background, opportunity, approach
- [ ] [DOC] `docs/partners/mast_reforestation.md` — backtest proposal
- [ ] [DOC] `docs/partners/blue_forest.md` — portfolio evidence pilot
- [ ] [DOC] All partner docs reference Blueprint §4 org research

## Phase 5 — PDF vaulting
**Status:** [x] CANCELLED — private business strategy docs, not suitable for public repo

- [~] [DOC] PDFs removed from repo. Product Brief, Blueprint, Build Roadmap, and
      Market Strategy contain private go-to-market strategy, competitive positioning,
      and named customer research. These stay on Desktop only, not in a public OSS repo.

## Phase 6 — QA gate
**Status:** [ ]

- [ ] [QA] `ruff check src/ tests/` — 0 exit
- [ ] [QA] Full test suite: `pytest tests/ -q` — baseline held
- [ ] [QA] Integration tests: `pytest tests/integration/ --run-integration -q` — passes
- [ ] [QA] Final git log review — clean history
- [ ] [QA] Commit: `docs: 009 launch prep — CLI docs + SDK + partner materials`

---

### Progress

_Phase 0 (README/ARCHITECTURE/ROADMAP) done. Phase 1 (CLI polish + docs) done.
Phase 2 (SDK example) done. Phase 3 (public reports) done — EVALUATION_REPORT
written in 013. Phase 5 (PDF vaulting) cancelled. Phase 4 (design partner prep)
deferred. Phase 6 (QA gate) partially done — gates pass but final commit not tagged._
