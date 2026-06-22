# Tasks — Review Workflow + Monitoring System

**Parent**: [../README.md](../README.md)

---

## Phase 0 — Data model
**Status:** [ ]

- [ ] [BE] `migrations/001_portfolios.sql` — portfolios + portfolio_polygons tables
- [ ] [BE] `migrations/002_schedules.sql` — schedules table
- [ ] [BE] `migrations/003_reviews.sql` — reviews table
- [ ] [BE] `src/models/portfolio.rs` — Portfolio, MonitoringSchedule, ReviewDecision structs
- [ ] [BE] `src/oberon/core/__init__.py` — add review_state + finding_type to Finding
- [ ] [TEST] `cargo test` — Portfolio CRUD round-trip
- [ ] [TEST] `cargo test` — Review state transitions (pending → approved/rejected/uncertain)
- [ ] [QA] ruff 0; cargo test green

## Phase 1 — Portfolio API
**Status:** [ ]

- [ ] [BE] `src/routes/portfolios.rs` — POST /v1/portfolios (create with polygons)
- [ ] [BE] `src/routes/portfolios.rs` — GET /v1/portfolios/:id
- [ ] [BE] `src/routes/portfolios.rs` — DELETE /v1/portfolios/:id
- [ ] [BE] `src/routes/portfolios.rs` — GET /v1/portfolios/:id/findings
- [ ] [TEST] `cargo test` — create portfolio, add polygons, retrieve
- [ ] [TEST] `cargo test` — delete portfolio cascades to polygons + schedules
- [ ] [QA] cargo test green

## Phase 2 — Scheduler
**Status:** [ ]

- [ ] [BE] `src/scheduler/mod.rs` — cron expression parser + next-run calculator
- [ ] [BE] Background worker: poll schedules every 60s, create jobs for due schedules
- [ ] [BE] Startup backfill: check for missed runs, enqueue if overdue
- [ ] [BE] POST /v1/portfolios/:id/schedule — attach schedule to portfolio
- [ ] [TEST] `cargo test` — scheduler creates job when schedule is due
- [ ] [TEST] `cargo test` — scheduler skips disabled schedules
- [ ] [TEST] `cargo test` — backfill logic on startup
- [ ] [QA] cargo test green

## Phase 3 — Review states
**Status:** [ ]

- [ ] [BE] `src/routes/reviews.rs` — POST /v1/findings/:id/review
- [ ] [BE] Accept: state (approved/rejected/uncertain), reviewer_notes, reviewer_id
- [ ] [BE] `src/routes/reviews.rs` — GET /v1/findings/:id (includes current review state)
- [ ] [BE] New findings default to review_state = "pending"
- [ ] [TEST] `cargo test` — submit review, retrieve updated state
- [ ] [TEST] `cargo test` — reject invalid state transitions
- [ ] [QA] cargo test green

## Phase 4 — Alert webhook
**Status:** [ ]

- [ ] [BE] `src/alerts/webhook.rs` — webhook delivery with retry (3 attempts, backoff)
- [ ] [BE] POST /v1/alerts/webhook — register webhook URL
- [ ] [BE] On job completion: if score >= threshold AND finding is NEW, POST webhook
- [ ] [BE] "New" detection: bounding box pre-filter, then geometry intersection vs previous run
- [ ] [TEST] `cargo test` — webhook fires for new high-score finding
- [ ] [TEST] `cargo test` — webhook does NOT fire for recurring finding
- [ ] [TEST] `cargo test` — webhook retry on connection failure
- [ ] [DOC] `docs/api/webhooks.md` — webhook payload schema
- [ ] [QA] cargo test green

## Phase 5 — Historical comparison
**Status:** [ ]

- [ ] [BE] GET /v1/findings/:id/history — previous findings for same polygon + task
- [ ] [BE] Finding type classification: new / recurring / escalating
- [ ] [TEST] `cargo test` — history returns chronological list
- [ ] [TEST] `cargo test` — escalating flag when score > previous score + delta
- [ ] [QA] cargo test green

## Phase 6 — Feedback export
**Status:** [ ]

- [ ] [BE] GET /v1/portfolios/:id/feedback — export all reviews as JSON
- [ ] [BE] Accept `?format=csv` query param for CSV export
- [ ] [BE] Export includes: polygon, finding, review state, reviewer, notes, provenance link
- [ ] [TEST] `cargo test` — export returns all reviews for portfolio
- [ ] [TEST] `cargo test` — CSV format has correct columns
- [ ] [QA] cargo test green
- [ ] [QA] Commit

---

### Progress

_None yet. Depends on 008-rust-control-plane + 005-evaluation-harness._
