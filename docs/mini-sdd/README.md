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
