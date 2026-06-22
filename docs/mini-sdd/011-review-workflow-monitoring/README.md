# 011 — Review Workflow + Monitoring System (Python/SQLite)

**Parent**: [../README.md](../README.md)

Transforms Oberon from a one-off analysis CLI into an operational monitoring product. Users register portfolios of polygons, schedule recurring analysis, and review findings with human judgment (approve/reject/uncertain).

Gate 4 decision (008): Rust control plane is deferred indefinitely. Python CLI is the primary interface. This mini-SDD builds the monitoring layer in pure Python with SQLite (stdlib `sqlite3`), no HTTP server required.

- **Reference:** Product Brief §13 (Monitoring and Alerting), Roadmap Phase 8
- **Prerequisite:** Pipeline validated (005 gate run), calibration complete (013 + 014 DONE)

> **Hard rules:**
> 1. Review states are part of the product data model, not UI-only. A finding is incomplete until reviewed.
> 2. Scheduled monitoring is idempotent — re-running for the same area+date produces the same job, not a duplicate.
> 3. Feedback (approve/reject/uncertain) is stored and exportable for future model calibration.
> 4. Alerts are evidence-backed. No alert without a finding, no finding without evidence.
> 5. No new dependencies. SQLite via stdlib `sqlite3`. JSON via stdlib. CLI via click.

---

## Locked decisions

| # | Decision | Choice |
|---|----------|--------|
| 1 | Storage | SQLite via stdlib `sqlite3`. Database at `~/.oberon/oberon.db` (override: `OBERON_DB_PATH`). |
| 2 | Review states | `pending`, `approved`, `rejected`, `uncertain` |
| 3 | Portfolio model | Named groups of polygons + schedule + task + thresholds |
| 4 | Scheduling | `oberon monitor run --portfolio <id>` CLI command. Cron-based scheduling external (system cron, systemd timer). Oberon does not run a daemon. |
| 5 | Alert delivery | Webhook (configurable URL). No email/SMS at this stage. |
| 6 | Feedback export | `oberon portfolio export-feedback` → JSON + CSV |

---

## In scope vs NOT in scope

### IN SCOPE
- Portfolio model (named polygon groups with schedules)
- SQLite schema + migrations
- `oberon portfolio` CLI subcommands (create, list, add-polygon, run, status)
- Finding review states + review notes (`oberon review` subcommands)
- Webhook alert when new material change detected
- Feedback export (JSON/CSV for model calibration)

### NOT in scope
- HTTP API server (deferred to 012)
- Web dashboard UI (CLI only)
- Email/SMS alerts (webhook only)
- Multi-tenant isolation (single deployment)
- Automated retraining from feedback
- Built-in scheduler daemon (use system cron)
