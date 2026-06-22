# Tasks — Security Hardening

**Parent**: [./README.md](./README.md)

> **Implementation note:** Originally planned as Python/FastAPI. Re-decided
> in favor of Rust control plane (see Gate 9 in mini-SDD README index). All
> phases implemented in `control-plane/` Rust codebase. Python-side security
> hardening (STAC timeout/retry, COG timeout, AOI cap, input validation,
> torch.load RCE mitigation) was done during the post-014 security audit.

---

## Phase 1 — HTTP server
**Status:** [x] DONE (Rust)

- [x] [BE] `control-plane/src/main.rs` — Axum server with clap CLI (serve, auth create-key)
- [x] [BE] `control-plane/src/routes/health.rs` — GET /v1/health with resource metrics
- [x] [BE] `control-plane/src/config.rs` — env var config (bind addr, DB path, python path, auth toggle, dashboard dir)

## Phase 2 — API key auth
**Status:** [x] DONE (Rust)

- [x] [BE] `control-plane/src/middleware/auth.rs` — X-API-Key SHA-256 validation, OBERON_AUTH_DISABLED=1 bypass for local dev
- [x] [BE] api_keys table in SQLite (SHA-256 hashed keys)
- [x] [BE] `auth create-key --user <name>` CLI subcommand (generates oberon_<32 hex> keys)

## Phase 3 — Audit logging
**Status:** [x] DONE (Rust)

- [x] [BE] `control-plane/src/middleware/audit.rs` — every request logged to audit_log table (method, path, status, duration)
- [x] [BE] GET /v1/audit/export endpoint

## Phase 4 — Pipeline security (Python-side, post-014 audit)
**Status:** [x] DONE (Python)

- [x] [BE] STAC timeout + retry: `Client.open(STAC_URL, timeout=STAC_TIMEOUT)` with exponential backoff
- [x] [BE] COG read timeout: GDAL_HTTP_TIMEOUT, GDAL_HTTP_MAX_RETRY via env vars
- [x] [BE] AOI area cap: 50,000 ha limit in orchestrator Phase 0
- [x] [BE] Input file size limit: 10 MB GeoJSON rejection in cli/main.py
- [x] [BE] Geometry type validation: Pydantic field_validator restricts to Polygon/MultiPolygon
- [x] [BE] torch.load weights_only=True first (RCE mitigation)
- [x] [BE] COG cache LRU eviction: 100 entry cap

## Phase 5 — Docker hardening
**Status:** [x] DONE (Rust)

- [x] [INFRA] `Dockerfile.server` — multi-stage Rust + Python build, non-root user
- [x] [INFRA] `docker-compose.yml` — resource limits, named volumes, server profile

## QA Gate
**Status:** [x] DONE

- [x] `cargo build` — passes
- [x] `cargo test` — 8 tests pass
- [x] `cargo clippy` — 0 warnings
- [x] Python: ruff + mypy + pytest + bounds preflight all clean (287 tests)
