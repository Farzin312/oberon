# 011 — Review Workflow + Monitoring System

**Parent**: [../README.md](../README.md)

Transforms Oberon from a one-off analysis CLI into an operational monitoring product. Users register portfolios of polygons, schedule recurring analysis, and review findings with human judgment (approve/reject/uncertain).

> **Implementation note:** Originally planned as Python/SQLite. Re-decided in
> favor of Rust control plane (Gate 9). All functionality implemented in the
> Rust `control-plane/` codebase: portfolio/polygon/run/review CRUD in Axum
> routes, SQLite storage, webhook alerts via reqwest, feedback export endpoint.
> The Python CLI continues to work standalone without the Rust server.

- **Reference:** Product Brief §13 (Monitoring and Alerting), Roadmap Phase 8
- **Prerequisite:** Pipeline validated (005 gate run), calibration complete (013 + 014 DONE)
- **Status:** DONE — implemented in Rust. See `control-plane/src/routes/portfolio.rs`, `control-plane/src/routes/review.rs`, `control-plane/src/alerts.rs`.

> **Hard rules:**
> 1. Review states are part of the product data model, not UI-only. A finding is incomplete until reviewed.
> 2. Scheduled monitoring is idempotent — re-running for the same area+date produces the same job, not a duplicate.
> 3. Feedback (approve/reject/uncertain) is stored and exportable for future model calibration.
> 4. Alerts are evidence-backed. No alert without a finding, no finding without evidence.

---

## Locked decisions

| # | Decision | Choice |
|---|----------|--------|
| 1 | Storage | SQLite (Rust rusqlite). 6 tables: portfolios, polygons, runs, reviews, api_keys, audit_log. |
| 2 | Review states | `pending`, `approved`, `rejected`, `uncertain` |
| 3 | Portfolio model | Named groups of polygons + task + cloud threshold + alert webhook URL |
| 4 | Scheduling | POST /v1/portfolios/{id}/run triggers analysis for all polygons. Cron-based scheduling external. |
| 5 | Alert delivery | Webhook via reqwest with retry. Configurable per-portfolio alert_webhook_url. |
| 6 | Feedback export | GET /v1/reviews/export?portfolio={id} — JSON output |

---

## In scope vs NOT in scope

### IN SCOPE (DONE)
- Portfolio model (named polygon groups with task + thresholds)
- SQLite schema (Rust rusqlite, WAL, FK-enforced)
- Portfolio CRUD + run endpoint (POST /v1/portfolios/{id}/run)
- Finding review states + review notes (POST /v1/reviews)
- Webhook alert when new material change detected (control-plane/src/alerts.rs)
- Feedback export (GET /v1/reviews/export)
- Web dashboard with Leaflet map (dashboard/ directory)

### NOT in scope
- Email/SMS alerts (webhook only)
- Multi-tenant isolation (single deployment)
- Automated retraining from feedback
- Built-in scheduler daemon (use system cron)
