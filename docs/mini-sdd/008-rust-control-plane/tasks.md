# Tasks — Rust Control Plane + Typed API

**Parent**: [../README.md](../README.md)

---

## Phase 0 — Rust scaffold
**Status:** [x] DONE

- [x] [BE] `control-plane/` workspace created (Axum, serde, rusqlite, tokio, tracing, reqwest)
- [x] [BE] `control-plane/Cargo.toml` — axum, serde, rusqlite, tokio, tracing, reqwest, tower-http
- [x] [BE] `control-plane/src/main.rs` — clap CLI (serve, auth create-key), telemetry init
- [x] [QA] `cargo build` compiles
- [x] [QA] `cargo test` passes (8 tests)

## Phase 1 — Domain types
**Status:** [x] DONE

- [x] [BE] `src/oberon/api/contracts.py` — ChangeRequestAPI, ChangeResponse, APIFinding, EvidenceMetrics, ModelInfo, ArtifactPaths, ResponseStatus (Pydantic v2)
- [x] [BE] `src/oberon/api/serialization.py` — serialize_findings(), serialize_bundle_to_response() — transforms internal Finding/EvidenceBundle to Product Brief §5 shape
- [x] [TEST] `tests/api/test_contracts.py` — 26 tests: request validation, response shape, serialization (ha->m2, score->change_score, ndvi_delta_mean->ndvi_delta)
- [x] [BE] Rust `control-plane/src/models.rs` — Portfolio, Polygon, Run, Review, ChangeRequest, ChangeResponse serde structs matching Python Pydantic contracts

## Phase 2 — POST /v1/change
**Status:** [x] DONE

- [x] [BE] `control-plane/src/routes/change.rs` — POST handler (async job spawn)
- [x] [BE] Request validation: date order, geometry present, task in known list
- [x] [BE] Response shape matches Product Brief
- [x] [BE] GET /v1/jobs/{id} status endpoint
- [x] [BE] Artifact serving (GET /v1/jobs/{id}/artifacts/{name})

## Phase 3 — Job state machine
**Status:** [x] DONE

- [x] [BE] `control-plane/src/db.rs` — SQLite schema (6 tables: portfolios, polygons, runs, reviews, api_keys, audit_log), WAL mode, FK enforcement
- [x] [BE] Job states: pending -> running -> completed | abstained | failed
- [x] [TEST] `control-plane/tests/db_test.rs` — 8 TDD tests for CRUD operations

## Phase 4 — Python subprocess bridge
**Status:** [x] DONE

Python-side CLI wiring:

- [x] [BE] `src/oberon/cli/main.py` — `--request <path>` flag (reads ChangeRequestAPI JSON)
- [x] [BE] `--request` and `--aoi` are mutually exclusive (enforced via _build_request)
- [x] [BE] `--json` output upgraded to full ChangeResponse shape via serialize_bundle_to_response()

Rust-side executor:

- [x] [BE] `control-plane/src/pipeline.rs` — spawns Python subprocess via tokio::spawn_blocking, writes request JSON, parses --json output

## Phase 5 — Portfolio + review routes
**Status:** [x] DONE

- [x] [BE] `control-plane/src/routes/portfolio.rs` — CRUD + run (loop polygons) + findings GeoJSON endpoint
- [x] [BE] `control-plane/src/routes/review.rs` — Review lifecycle + feedback export endpoint

## Phase 6 — Auth + audit middleware
**Status:** [x] DONE

- [x] [BE] `control-plane/src/middleware/auth.rs` — X-API-Key SHA-256 validation, OBERON_AUTH_DISABLED bypass
- [x] [BE] `control-plane/src/middleware/audit.rs` — every request logged to audit_log table
- [x] [BE] `control-plane/src/main.rs` — `auth create-key` CLI subcommand

## Phase 7 — Dashboard + alerts + resource tracking
**Status:** [x] DONE

- [x] [BE] `control-plane/src/routes/dashboard.rs` — static file serving (index.html, app.js, style.css)
- [x] [BE] `control-plane/src/alerts.rs` — webhook delivery with retry (reqwest)
- [x] [BE] `control-plane/src/telemetry.rs` — JobMetrics (AtomicU64), ResourceSnapshot (mem/disk/RSS)
- [x] [BE] `control-plane/src/routes/health.rs` — GET /v1/health with resource metrics

## Phase 8 — Build + docs
**Status:** [x] DONE

- [x] [BE] `Dockerfile.server` — multi-stage Rust + Python build
- [x] [BE] `docker-compose.yml` — `--profile server up` one-liner
- [x] [DOC] GETTING_STARTED.md with API server + dashboard walkthrough
- [x] [DOC] README.md with self-hosted server section
- [x] [DOC] LOGGING_STANDARD.md (unified Python + Rust event vocabulary)
- [x] [QA] `cargo build --release` — passes
- [x] [QA] `cargo clippy` — 0 warnings

---

### Progress

All phases complete. Rust control plane built with Axum server, SQLite (6 tables, WAL, FK-enforced), API key auth, audit middleware, pipeline subprocess bridge, portfolio/polygon/run/review CRUD, web dashboard (vanilla JS + Leaflet), webhook alerts, resource tracking, unified logging standard. 287 Python tests + 8 Rust tests.
