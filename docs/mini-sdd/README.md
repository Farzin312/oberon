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
| `001-data-plane-pipeline` | **DONE** — 114 tests | Full data-plane pipeline: STAC discovery → scene quality → COG read → preparation → baselines → change detection → evidence bundles → CLI |
| `002-baseline-fixes` | **NEXT** — Ready to build | Complete pixel_delta stub, write task contract (Roadmap Phase 1), close 001 Phase 7 |
| `003-clay-experiment` | Ready (after 002) | Product Brief Week 4: Get Clay running, produce feature-diff map on one example |
| `004-benchmark-dataset` | Ready (after 003) | Collect 12-18 reviewed before/after pairs, create golden integration tests |
| `005-evaluation-harness` | Ready (after 003+004) | Full AI vs deterministic baseline comparison; decision gate (Roadmap Phase 4) |
| `006-model-registry-provenance` | Ready (after 002+003) | Model registry, artifact index, COG cache, API contract alignment |
| `007-packaging-deployment` | Ready (after 002) | Docker Compose (CPU+GPU), structured logging, external reproducibility |
| `008-rust-control-plane` | Deferred (after 006+007) | Axum API, typed job contracts, SQLite state machine, Python subprocess |
| `009-launch-docs` | Last (after 005+006+007) | README/ARCHITECTURE/ROADMAP rewrite, SDK demo, design partner prep |

### Recommended build sequence

```
002 → 003 → 004 → 005   (Core pipeline + AI evaluation)
                  ↓
            006 → 007   (Stability + deployment)
                  ↓
            008         (Control plane — defer until pipeline proven)
                  ↓
            009         (Launch — after evaluation results known)
```

The PDF ordering (Product Brief Weeks 0-10, Roadmap Phases 1-8) is preserved. 001 = Weeks 0-3. 002-005 = Roadmap Phases 1-4. 006-007 = Product Brief Weeks 6-8. 008 = Week 5 (deferred per Roadmap Phase 7). 009 = Weeks 9-10.

### Decision gates between phases

- **Gate 1** (after 003): Does Clay produce a sensible change map? If no → skip 004-005, go to 007.
- **Gate 2** (after 005): Does AI beat baseline? If no → deterministic-only default.
- **Gate 3** (after 007): Can external user reproduce? If no → fix packaging before features.
- **Gate 4** (after 008): Is Rust worth the complexity? If no → Python CLI as primary interface.
