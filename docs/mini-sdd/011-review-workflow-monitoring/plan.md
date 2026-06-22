# Plan — Review Workflow + Monitoring System

**Parent**: [../README.md](./README.md)

---

## 1. Repo facts

| Area | Current state | Source |
|---|---|---|
| Job system | SQLite-backed, single-shot (from 008) | Rust control plane |
| Finding model | Geometry + score + evidence, no review state | `core/__init__.py` |
| API | POST /v1/change, GET /v1/jobs/:id | Rust routes |
| Scheduling | None | N/A |
| Portfolio model | None | N/A |

---

## 2. Execution order

1. **Phase 0 — Data model** — Portfolio, MonitoringSchedule, ReviewDecision
2. **Phase 1 — Portfolio API** — CRUD for polygon groups
3. **Phase 2 — Scheduler** — cron-like engine that creates jobs on schedule
4. **Phase 3 — Review states** — finding lifecycle: pending → approved/rejected/uncertain
5. **Phase 4 — Alert webhook** — notify on new material change
6. **Phase 5 — Historical comparison** — diff current vs previous run findings
7. **Phase 6 — Feedback export**

---

## 3. Architecture

### 3.1 Data model (Rust + SQLite)

```sql
-- Portfolios: named groups of polygons
CREATE TABLE portfolios (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    task TEXT NOT NULL DEFAULT 'vegetation_disturbance',
    created_at TEXT NOT NULL
);

-- Polygons within a portfolio
CREATE TABLE portfolio_polygons (
    id TEXT PRIMARY KEY,
    portfolio_id TEXT NOT NULL REFERENCES portfolios(id),
    geometry_json TEXT NOT NULL,
    label TEXT,
    created_at TEXT NOT NULL
);

-- Monitoring schedules
CREATE TABLE schedules (
    id TEXT PRIMARY KEY,
    portfolio_id TEXT NOT NULL REFERENCES portfolios(id),
    cron_expr TEXT NOT NULL,           -- e.g. "0 0 1 * *" = monthly
    before_window_days INTEGER NOT NULL DEFAULT 30,
    after_window_days INTEGER NOT NULL DEFAULT 30,
    max_cloud_fraction REAL DEFAULT 0.5,
    enabled INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL
);

-- Review decisions on findings
CREATE TABLE reviews (
    id TEXT PRIMARY KEY,
    job_id TEXT NOT NULL REFERENCES jobs(id),
    finding_id TEXT NOT NULL,
    portfolio_id TEXT REFERENCES portfolios(id),
    polygon_id TEXT REFERENCES portfolio_polygons(id),
    state TEXT NOT NULL CHECK(state IN ('pending', 'approved', 'rejected', 'uncertain')),
    reviewer_notes TEXT,
    reviewer_id TEXT,
    reviewed_at TEXT,
    created_at TEXT NOT NULL
);
```

### 3.2 API surface

| Endpoint | Method | Purpose |
|---|---|---|
| `/v1/portfolios` | POST | Create portfolio with polygons |
| `/v1/portfolios/:id` | GET | Get portfolio + polygon count + latest findings |
| `/v1/portfolios/:id` | DELETE | Remove portfolio |
| `/v1/portfolios/:id/schedule` | POST | Attach monitoring schedule |
| `/v1/portfolios/:id/findings` | GET | Get latest ranked findings across all polygons |
| `/v1/findings/:id/review` | POST | Submit review decision (approve/reject/uncertain) |
| `/v1/findings/:id/history` | GET | Get historical findings for same polygon+task |
| `/v1/portfolios/:id/feedback` | GET | Export all review decisions as JSON/CSV |
| `/v1/alerts/webhook` | POST | Register webhook URL for alerts |

### 3.3 Alert logic

```
On job completion:
  if finding.score >= portfolio.alert_threshold:
    if finding is NEW (not present in previous run for same polygon):
      POST webhook: { portfolio, polygon, finding, evidence_uris }
```

"New" means: the finding's geometry doesn't overlap with any previously-reviewed finding by >50%.

### 3.4 Historical comparison

When a new run completes for a portfolio polygon:
- Fetch the previous run's findings for the same polygon + task
- Spatial join: do any new findings overlap old findings?
- Mark each new finding as `new`, `recurring`, or `escalating` (higher score than before)
- Surface in the findings response

---

## 4. Exact changes

### 4.1 Rust control plane (008 codebase)
- `src/models/portfolio.rs` — Portfolio, Schedule, ReviewDecision structs
- `src/routes/portfolios.rs` — CRUD endpoints
- `src/routes/reviews.rs` — review state endpoints
- `src/routes/feedback.rs` — export endpoint
- `src/scheduler/mod.rs` — cron-like scheduler
- `src/alerts/webhook.rs` — webhook delivery

### 4.2 Python pipeline
- `src/oberon/core/__init__.py` — add `review_state` and `finding_type` (new/recurring/escalating) to Finding
- `src/oberon/cli/main.py` — add `oberon portfolio` subcommand group

### 4.3 Database migrations
- `migrations/001_portfolios.sql`
- `migrations/002_schedules.sql`
- `migrations/003_reviews.sql`

---

## 5. Risk register

| Risk | Mitigation |
|---|---|
| Scheduler misses runs (process restart) | On startup: check for overdue schedules, backfill missed runs |
| Review queue floods with false positives | Alert threshold configurable per portfolio; default conservative (0.7 score) |
| Webhook delivery failures | Retry with exponential backoff (3 attempts); mark as delivery_failed after |
| Spatial join for "new vs recurring" is expensive | Use bounding box pre-filter before geometry intersection |
| Feedback data accumulates without model improvement | Phase 6: export in format ready for calibration (005 follow-up) |

---

## 6. End-phase cleanup

- Update SYSTEM_DESIGN.md with monitoring system architecture
- Update DATA_FLOW.md with portfolio → schedule → job → finding → review flow
- Update AGENTS.md with scheduler configuration
- Document webhook payload schema in `docs/api/webhooks.md`
