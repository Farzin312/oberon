# Tasks — Review Workflow + Monitoring System

**Parent**: [./README.md](./README.md)

> **Implementation note:** Originally planned as Python/SQLite. Re-decided in
> favor of Rust control plane (see Gate 9 in mini-SDD README index). All
> phases implemented in `control-plane/` Rust codebase.

---

## Phase 1 — DB layer + models
**Status:** [x] DONE (Rust)

- [x] [BE] `control-plane/src/db.rs` — SQLite schema (portfolios, polygons, runs, reviews tables), WAL mode, FK enforcement
- [x] [BE] `control-plane/src/models.rs` — Portfolio, Polygon, Run, Review serde structs
- [x] [TEST] `control-plane/tests/db_test.rs` — TDD tests for CRUD operations

## Phase 2 — Portfolio CRUD
**Status:** [x] DONE (Rust)

- [x] [BE] `control-plane/src/routes/portfolio.rs` — POST/GET/DELETE portfolios, POST polygons, GET findings GeoJSON
- [x] [BE] Portfolio run endpoint: POST /v1/portfolios/{id}/run (loops polygons, spawns Python subprocess per polygon)

## Phase 3 — Portfolio run
**Status:** [x] DONE (Rust)

- [x] [BE] `control-plane/src/pipeline.rs` — subprocess bridge: spawns Python, writes request JSON, parses --json output
- [x] [BE] Run results stored in runs table with status tracking

## Phase 4 — Review states
**Status:** [x] DONE (Rust)

- [x] [BE] `control-plane/src/routes/review.rs` — POST /v1/reviews (submit review decision)
- [x] [BE] Review states: pending, approved, rejected, uncertain
- [x] [BE] GET /v1/reviews/export?portfolio={id} — feedback export endpoint

## Phase 5 — Webhook alerts
**Status:** [x] DONE (Rust)

- [x] [BE] `control-plane/src/alerts.rs` — webhook delivery with retry (reqwest), configurable per-portfolio alert_webhook_url

## QA Gate
**Status:** [x] DONE

- [x] `cargo build` — passes
- [x] `cargo test` — 8 tests pass
- [x] `cargo clippy` — 0 warnings
- [x] Dashboard tested: portfolio creation, polygon addition, run, findings display all verified via curl
