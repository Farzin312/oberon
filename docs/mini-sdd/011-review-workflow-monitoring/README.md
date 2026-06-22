# 011 — Review Workflow + Monitoring System

**Parent**: [../README.md](../README.md)

Roadmap PDF Phase 8 (lines 708-734): Transform Oberon from a one-off query API into an operational monitoring product. This is where Oberon becomes "a product rather than an analysis endpoint." It includes portfolios of polygons, scheduled reruns, ranked finding queues, and human review states (approve/reject/uncertain).

Product Brief Section 13 expansion: "Users register areas, schedules, and task thresholds. Oberon runs new-observation checks and sends evidence-backed alerts."

- **Reference:** Roadmap PDF Phase 8, Product Brief §13 Phase 4 (Monitoring and Alerting)
- **Prerequisite:** 008-rust-control-plane (job system, persistence), 005-evaluation-harness (validated pipeline)

> **Hard rules:**
> 1. Review states are part of the product data model, not UI-only. A finding is incomplete until reviewed.
> 2. Scheduled monitoring is idempotent — re-running for the same area+date produces the same job, not a duplicate.
> 3. Feedback (approve/reject/uncertain) is stored and exportable for future model calibration.
> 4. Alerts are evidence-backed. No alert without a finding, no finding without evidence.

---

## Locked decisions

| # | Decision | Choice |
|---|----------|--------|
| 1 | Review states | `pending`, `approved`, `rejected`, `uncertain` |
| 2 | Portfolio model | Named groups of polygons + schedule + task + thresholds |
| 3 | Scheduling | SQLite-based job scheduler in Rust control plane (008) |
| 4 | Alert delivery | Webhook (configurable URL) + in-app notification. No email/SMS at this stage. |
| 5 | Feedback export | JSON + CSV export of all review decisions with provenance links |

---

## In scope vs NOT in scope

### IN SCOPE
- Portfolio model (named polygon groups with schedules)
- Scheduled reruns (cron-like: monthly, quarterly, custom)
- Finding review states + review notes
- Alert webhook when new material change detected
- Historical comparison (compare current findings to previous run)
- Feedback export (JSON/CSV for model calibration)

### NOT in scope
- Web dashboard UI (API + CLI only)
- Email/SMS alerts (webhook only)
- Multi-tenant isolation (single deployment)
- Automated retraining from feedback (separate future work)
- Field verification workflow (out of scope — that's the human's job)

---

## Risk warnings

- This mini-SDD transitions Oberon from "tool" to "product." Only proceed after the pipeline is validated (005 gate passed) and the control plane exists (008 complete).
- Scheduled jobs that hit live STAC APIs will incur real latency. Rate limiting and backoff are essential.
- Review fatigue: if the system produces too many false positives, users stop reviewing. Precision matters more than recall for operational monitoring.
