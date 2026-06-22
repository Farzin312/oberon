# 009 — CLI Docs + SDK Example + Design Partner Prep

**Parent**: [../README.md](../README.md)

Final deliverables before design-partner launch. CLI docs, SDK demo script, README overhaul (following strict OSS doc separation per user's standards), evaluation report publication, and design partner preparation.

- **Reference:** Product Brief §9 (Build Plan Week 9-10), Blueprint §4 (Customer priority)
- **Prerequisite:** 005-evaluation-harness (gate decision known), 006 (stable contracts), 007 (Docker)

> **Hard rules:**
> 1. README never overclaims. Claims match evaluation results from 005.
> 2. All four OSS doc files maintained: README, CLAUDE.md, ARCHITECTURE.md, ROADMAP.md.
> 3. Desktop PDFs committed to repo as planning references before this mini-SDD closes.
> 4. If 005 decision was "AI loses", README describes Oberon as deterministic-first with optional AI.

---

## Locked decisions

| # | Decision | Choice |
|---|----------|--------|
| 1 | README audience | Users + marketing — what, why, quick start |
| 2 | SDK shape | Python convenience function wrapping CLI, not a new API |
| 3 | Evaluation report | Public — committed to repo at `docs/EVALUATION_REPORT.md` |
| 4 | PDF vaulting | `docs/planning/` directory in repo |
| 5 | Design partner first | Osa Conservation (from Blueprint §4) — restoration corridor benchmark |

---

## In scope vs NOT in scope

### IN SCOPE
- README.md rewrite
- ARCHITECTURE.md + ROADMAP.md creation
- CLI --help polishing
- examples/sdk_demo.py
- Evaluation report publication
- PDF vaulting
- Design partner outreach materials (NOT sending — just prep)

### NOT in scope
- Design partner outreach execution (user does this)
- Web dashboard (explicitly excluded per Product Brief §12)
- Post-launch support
- Marketing site
- A hosted demo

---

## Risk warnings

- README claims must exactly match the evaluation results from 005. If the AI decision is marginal, the README should say "AI available as experimental flag, deterministic by default."
- SDK convenience function is not a product guarantee. If package API changes, the SDK example should be the first to break (caught by CI).
