# Mini-SDD — Bounded-Change Documentation Sets

**Parent**: [README.md](../README.md)

A mini-SDD is the lightweight doc set (README.md + plan.md + tasks.md) for a bounded, low-ambiguity change. It follows the same pattern as `spex_backend` mini-SDDs:

- **README.md** — decisions, scope boundary, hard rules, risk warnings
- **plan.md** — architecture, verified repo facts, contracts, execution order, risk register
- **tasks.md** — checkbox execution checklist per phase with TDD gates

Mini-SDDs trim the *artifacts* of the full SDD cycle but **never** trim the quality gates (lint, TDD, bounds validation, docs sync, code review).

## When to use mini-SDD vs full SDD

| Aspect | Mini-SDD | Full SDD |
|--------|----------|----------|
| Change type | Bounded fixes, wiring, migrations, contract additions | Net-new subsystems, broad redesigns |
| Ambiguity | Low — decisions known upfront | Significant — needs Clarify phase |
| Artifacts | 3 files (README, plan, tasks) | 7+ files (spec → clarify → plan → contracts → risks → tasks → analyze → verify) |
| When to upgrade | If you're inventing requirements mid-mini-SDD | Start with full SDD |

## Mini-SDD directory structure

```
docs/mini-sdd/
├── README.md              ← this file
├── _template/             ← copy these for new mini-SDDs
│   ├── README.md
│   ├── plan.md
│   └── tasks.md
└── <NNN>-<slug>/
    ├── README.md          ← decisions + scope
    ├── plan.md            ← architecture + contracts
    └── tasks.md           ← execution checklist
```

## How to create a mini-SDD

1. Copy `_template/` to `<NNN>-<slug>/`
2. Fill in README.md with decisions, scope, locked choices
3. Fill in plan.md with verified repo facts, contracts, execution phases
4. Create tasks.md with per-phase checkboxes
5. Run `bounds validate --quick` to baseline
6. Proceed to implementation, crossing off tasks one at a time

---

## Mini-SDD index

| ID | Status | Description |
|----|--------|-------------|
| `001-data-plane-pipeline` | **DONE** — 118 tests | Full data-plane pipeline: STAC discovery → scene quality → COG read → preparation → baselines → change detection → evidence bundles → CLI. Phase 7 cleanup closed out by 002. |
| `002-baseline-fixes` | **DONE** — 114 tests | Complete pixel_delta stub, write task contract, close 001 Phase 7 |
| `003-clay-experiment` | **DONE** — 157 tests | Clay v1.5 adapter, tiled inference, --use-ai flag. PROCEED WITH CAUTION to 005. |
| `004-benchmark-dataset` | **DONE** — 12/12 golden tests passing | Collect 12 reviewed before/after pairs, golden integration tests. Phase 3 run+calibrate completed live. 013 calibration brought golden tests from 1/12 to 12/12. |
| `005-evaluation-harness` | **GATE RUN** — AI_ties | Full AI vs deterministic baseline comparison completed on 12 examples. Clay did not improve precision (`0.1266` vs `0.1266`), so AI remains experimental. |
| `006-model-registry-provenance` | **DONE** — 226 tests | Model registry, artifact index, provenance enrichment, COG cache, --json/--cache flags, API gap doc |
| `007-packaging-deployment` | **DONE** — 131 tests | Docker Compose (CPU+GPU), structured logging, health check, verified in container |
| `008-rust-control-plane` | **DONE** — 287 py + 8 rs tests | Axum API, typed job contracts, SQLite state machine, Python subprocess, portfolio/review routes, web dashboard, audit middleware, auth, Docker server. |
| `009-launch-docs` | **Phase 0-3 DONE** — Phase 4 (partner prep) + Phase 6 (QA) deferred | README/ARCHITECTURE/ROADMAP rewrite, CLI polish + reference docs, SDK demo, reports verified. Phase 5 (PDF vaulting) cancelled. Phase 4 partner prep deferred. |
| `010-scene-composite` | **DONE** — 128 tests | Cloud-masked composite when single scene insufficient (Roadmap correction #2) |
| `011-review-workflow-monitoring` | **DONE** — Rust control plane | Portfolios, runs, review states, webhook alerts, feedback export. Implemented in Rust (not Python) per 008 architecture decision. |
| `012-security-hardening` | **DONE** — Rust control plane | API key auth (SHA-256), audit logging middleware, non-root Docker, path traversal guards, resource limits. Implemented in Rust. |
| `013-baseline-calibration` | **DONE** — 12/12 golden, 277 unit tests | Signed threshold (veg_disturbance = NDVI loss only), morphological closing (25x25), cross-season annotation. Golden tests 1/12 -> 12/12. Known limitations: seasonal-vs-fire overlap (needs spatial variance), cloud-edge artifacts. |
| `014-spatial-variance-seasonal-detection` | **DONE** — 287 unit tests | Spatial-variance seasonal detection: CV of NDVI loss distinguishes uniform seasonal senescence from patchy real disturbance. Abstains only when uniform AND broad. Annotates seasonal_risk in provenance otherwise. |
| `015-dashboard-ui-polish` | **DONE** | Static dashboard revamp: neutral operational dark mode, map-first workflow, no imported font/decorative shell, cleaner portfolio/run/review UX. |
| `016-dashboard-complete-revamp` | **DONE** | Complete visual and layout redesign of WebGIS console: full-screen map overlay, floating glassmorphic panels, chronological run timeline, modalless direct drawing. |
| `017-dashboard-ui-hardening` | **DONE** | Fix dashboard revamp regressions: step-based portfolio creation, no horizontal modal overflow, clearer signal controls, visible logo, and bounded sidebar panels. |

### Recommended build sequence

```
Layer 1 — Core pipeline (build first)
  001 (DONE) → 002 → 010

Layer 2 — AI evaluation (gate: does AI earn its place?)
  003 → 004 → 005

Layer 3 — Stability + deployment
  006 → 007

Layer 4 — Control plane
  008

Layer 5 — Product + launch
  011 → 012 → 009
```

Each layer can proceed when its prerequisites are done. Layers 2 and 3 can run in parallel after Layer 1.

### Decision gates between phases

- **Gate 1** (after 003): Does Clay produce a sensible change map? If no → skip 004-005, go to 007.
- **Gate 2** (after 005): Does AI beat baseline? If no → deterministic-only default.
- **Gate 3** (after 007): Can external user reproduce? If no → fix packaging before features.
- **Gate 4** (after 008): Is Rust worth the complexity? If no → Python CLI as primary interface.
- **Gate 5** (after 011): Does monitoring create enough value to justify hosting? If no → keep as OSS tool.

### PDF coverage map

| PDF Section | Mini-SDD |
|---|---|
| Roadmap Phase 1 (task contract) | 002 |
| Roadmap Phase 2 (benchmark dataset) | 004 |
| Roadmap Phase 3 (deterministic baseline) | 001 + 002 |
| Roadmap Phase 4 (AI as parallel branch) | 003 + 005 |
| Roadmap Phase 5 (local engine) | 006 |
| Roadmap Phase 6 (reproducible) | 007 |
| Roadmap Phase 7 (control plane) | 008 |
| Roadmap Phase 8 (review + monitoring) | 011 |
| Roadmap correction #2 (scene composite) | 010 |
| Product Brief §3 (AI components 1-2) | 003 |
| Product Brief §3 (AI components 3-4) | Deferred (post-pilot task heads) |
| Product Brief §4 (hybrid intelligence) | 002 + 005 |
| Product Brief §5 (API contract) | 006 + 008 |
| Product Brief §6 (tech architecture) | 006 + 008 |
| Product Brief §8 (evaluation) | 005 |
| Product Brief §10 (deployment + security) | 007 + 012 |
| Product Brief §12 (risks + gates) | README index + each mini-SDD risk register |
| Product Brief §13 (expansion: monitoring) | 011 |
| Blueprint §6 (scaling stages) | 008 + 011 |
| Blueprint §8 (OSS to commercial boundary) | 009 |
| Blueprint §10 (economics) | 006 (cache) + documented in 009 |
| Market Strategy §3-7 (positioning + customers) | 009 |
