# Spec-Driven Development (SDD)

**Parent**: [README.md](../README.md)

SDD is required for broad redesigns, net-new subsystems, or any change with significant unknowns. For bounded, low-ambiguity changes, use [mini-sdd](mini-sdd/README.md).

## When to use full SDD vs mini-SDD

| Aspect | Full SDD | Mini-SDD |
|--------|----------|----------|
| Change size | Net-new subsystems, broad redesigns | Bounded fixes, polish, wiring |
| Ambiguity level | Significant — needs a Clarify phase | Low — decisions known upfront |
| Artifact count | 7 artifacts (spec → clarify → plan → contracts → risks → tasks → analyze → verify) | 3 files (README + plan + tasks) |
| Gate enforcement | Manual per-phase gates | Manual per-phase gates |

## Full SDD flow

```
Specify → Clarify → Plan → Analyze → Implement → Verify
```

Artifacts live in `.specify/specs/<feature-name>/`:
- `spec.md` — requirements and scope
- `analysis.md` — solution audit (required before implementation)
- `contracts.md` — data model, API contracts, interfaces
- `plan.md` — execution plan
- `risks.md` — risk register
- `tasks.md` — task breakdown
- `verify.md` — verification checklist

## Non-negotiable SDD rules

1. No implementation before `analysis.md` (Solution Audit) passes.
2. Clarify has no artificial limits — ask until design is clear.
3. No redesign or new requirements during implementation.
4. Tasks reference artifact IDs, not restated requirements.
5. Risk register is a separate file, never hidden inside plan.md.
6. `/specify` branches: `feature/<NNN>-<slug>`.
