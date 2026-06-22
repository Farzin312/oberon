# Tasks — Rust Control Plane + Typed API

**Parent**: [../README.md](../README.md)

---

## Phase 0 — Rust scaffold
**Status:** [ ]

- [ ] [BE] `cd src && cargo init oberon-api` (or top-level workspace)
- [ ] [BE] `Cargo.toml` — axum, serde, sqlx, tokio, tracing
- [ ] [BE] `src/main.rs` — hello-world Axum server on :8080
- [ ] [QA] `cargo build` compiles
- [ ] [QA] `cargo test` passes

## Phase 1 — Domain types
**Status:** [x] DONE (Python-side pre-work)

- [x] [BE] `src/oberon/api/contracts.py` — ChangeRequestAPI, ChangeResponse, APIFinding, EvidenceMetrics, ModelInfo, ArtifactPaths, ResponseStatus (Pydantic v2)
- [x] [BE] `src/oberon/api/serialization.py` — serialize_findings(), serialize_bundle_to_response() — transforms internal Finding/EvidenceBundle to Product Brief §5 shape
- [x] [TEST] `tests/api/test_contracts.py` — 26 tests: request validation, response shape, serialization (ha->m2, score->change_score, ndvi_delta_mean->ndvi_delta)
- [ ] [BE] Rust `src/models/change_request.rs` — ChangeRequest, TimeWindow structs (Rust side deferred)
- [ ] [BE] Rust `src/models/change_response.rs` — ChangeResponse, Finding, Observations, ModelInfo (Rust side deferred)
- [ ] [BE] Serde derives + validation (dates valid, geometry non-empty) (Rust side deferred)

## Phase 2 — POST /v1/change
**Status:** [ ]

- [ ] [BE] `src/routes/change.rs` — POST handler
- [ ] [BE] Request validation: date order, geometry present, task in known list
- [ ] [BE] Response shape matches Product Brief
- [ ] [TEST] `cargo test` — test route returns 200 for valid request
- [ ] [TEST] `cargo test` — test route returns 422 for invalid request
- [ ] [QA] `cargo build`

## Phase 3 — Job state machine
**Status:** [ ]

- [ ] [BE] `src/jobs/state.rs` — JobState enum + transitions
- [ ] [BE] `src/jobs/store.rs` — SQLite schema + CRUD
- [ ] [BE] Table: `jobs(id, state, request_json, result_json, created_at, updated_at)`
- [ ] [TEST] Test state transitions: queued→running→completed
- [ ] [TEST] Test invalid transitions (completed→running) rejected
- [ ] [TEST] Test SQLite round-trip

## Phase 4 — Python subprocess
**Status:** [ ] (Rust executor deferred)

Python-side CLI wiring done:

- [x] [BE] `src/oberon/cli/main.py` — add `--request <path>` flag (reads ChangeRequestAPI JSON)
- [x] [BE] `--request` and `--aoi` are mutually exclusive (enforced via _build_request)
- [x] [BE] `--json` output upgraded to full ChangeResponse shape via serialize_bundle_to_response()
- [x] [TEST] `tests/cli/test_request_json.py` — 10 tests: request parsing, mutual exclusion, JSON shape
- [ ] [BE] Rust `src/executor.rs` — spawn python -m oberon.cli analyze --request /tmp/input.json (deferred)

## Phase 5 — Durable queue
**Status:** [ ]

- [ ] [BE] `src/jobs/queue.rs` — dequeues next pending job, marks queued→running
- [ ] [BE] Background worker: poll queue every 5s
- [ ] [BE] Lock (skip) jobs started > timeout_sec ago
- [ ] [TEST] Test queue: 2 jobs submitted, worker processes first, second stays queued
- [ ] [TEST] Test timeout: job times out then returns as failed

## Phase 6 — GET /v1/jobs/:id
**Status:** [ ]

- [ ] [BE] `src/routes/jobs.rs` — GET handler
- [ ] [BE] Returns job status + result JSON (if completed)
- [ ] [BE] Returns 404 for unknown job
- [ ] [TEST] Test GET returns job state
- [ ] [TEST] Test GET returns 404
- [ ] [QA] Full integration: POST → GET → completed (with Python subprocess)
- [ ] [QA] `cargo test` — all 008 tests pass

## Phase 7 — Build + docs
**Status:** [ ]

- [ ] [BE] `Dockerfile.rust` — multi-stage Rust build (compile → runtime)
- [ ] [BE] `docker-compose.yml` — add Rust + Python services for split deployment
- [ ] [DOC] Update SYSTEM_DESIGN.md with Rust control plane architecture
- [ ] [DOC] Update README.md with "API Server" section
- [ ] [DOC] Update AGENTS.md with Rust build/run instructions
- [ ] [QA] `cargo build --release` — passes
- [ ] [QA] Commit

---

### Progress

_Python-side API contracts done (Phase 1 pre-work): Pydantic models matching Product Brief §5, serialization layer resolving gaps 1,2,4,5,6,8,9,10. 26 tests. Rust control plane (Phases 0, 2-7) remains deferred._
