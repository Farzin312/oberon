# 008 — Rust Control Plane + Typed API

**Parent**: [../README.md](../README.md)

Product Brief Week 5: Rust Axum control plane with typed job contracts, SQLite-backed state machine, and Python subprocess execution. This is deliberately delayed until after the pipeline contracts are stable (Roadmap PDF Phase 7 guidance: "Only after the local workflow is credible should you add the control plane").

- **Week:** Product Brief Week 5 (moved after pipeline stabilization)
- **Reference:** Product Brief §6 (Technical Architecture), Blueprint §6, Roadmap PDF Phase 7 (lines 643-706)
- **Prerequisite:** 006-model-registry-provenance (stable contracts), 007-packaging-deployment (Docker)

> **Hard rules:**
> 1. Rust and Python communicate via file-based JSON contracts — NO FFI, NO shared memory.
> 2. Rust owns orchestration only. All geospatial logic stays in Python.
> 3. The Python CLI continues to work without the Rust API. Rust is an optional control plane.
> 4. Do not duplicate geospatial validation in Rust. Rust validates request shape, Python validates spatial content.

---

## Locked decisions

| # | Decision | Choice |
|---|----------|--------|
| 1 | Framework | Axum (Rust web framework) |
| 2 | Persistence | SQLite via sqlx |
| 3 | Python integration | Subprocess with JSON request/response files |
| 4 | Request contract | `POST /v1/change` matching Product Brief §5 |
| 5 | Job states | queued → running → completed | abstained | failed | invalid |
| 6 | Async model | tokio with blocking thread for subprocess |

---

## In scope vs NOT in scope

### IN SCOPE
- Axum server + routes (POST /v1/change, GET /v1/jobs/:id)
- ChangeRequest + ChangeResponse Rust types
- SQLite-backed job state machine
- Python subprocess execution (via --request flag)
- Error handling: validation errors, timeouts, Python crashes

### NOT in scope
- HTTP health endpoint (covered by 007 `oberon health`)
- Authentication/authorization (future)
- Multi-user isolation (future)
- WebSocket streaming (future)
- Model registry in Rust (Python-owned, accessed via subprocess)
- Artifact serving (Nginx or separate file server)
- Scheduled monitoring (future)

---

## Risk warnings

- Rust compilation is slow. Expect 3-5 min for first cargo build.
- The Python subprocess approach means Rust cannot stream results. Acceptable for a batch-oriented MVP.
- If the pipeline contracts change, Rust types must be updated. Lock contracts via the model registry (006) first.
- This is the highest-risk mini-SDD for a solo founder. Only proceed if the Python pipeline is proven (005 evaluation gate passed).
