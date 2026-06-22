# Tasks — Security Hardening + Production Safeguards

**Parent**: [../README.md](../README.md)

---

## Phase 0 — API key auth
**Status:** [ ]

- [ ] [BE] `migrations/004_api_keys.sql` — api_keys table (key_hash, user_id, created_at, active)
- [ ] [BE] `src/auth/mod.rs` — auth middleware extracting X-API-Key header
- [ ] [BE] `src/auth/keys.rs` — create_key(), validate_key(), hash_key()
- [ ] [BE] `OBERON_AUTH_DISABLED=1` env var bypass for local dev
- [ ] [BE] `src/oberon/cli/main.py` — add `oberon auth create-key` subcommand
- [ ] [TEST] `cargo test` — valid API key passes through
- [ ] [TEST] `cargo test` — missing key returns 401
- [ ] [TEST] `cargo test` — invalid key returns 403
- [ ] [TEST] `cargo test` — auth disabled env var works
- [ ] [QA] cargo test green

## Phase 1 — Audit logging
**Status:** [ ]

- [ ] [BE] `migrations/005_audit_log.sql` — audit_log table (append-only)
- [ ] [BE] `src/middleware/audit.rs` — log every request after response
- [ ] [BE] `src/routes/audit.rs` — GET /v1/audit/export with date range filter
- [ ] [TEST] `cargo test` — audit entry created for API call
- [ ] [TEST] `cargo test` — export returns filtered results
- [ ] [QA] cargo test green

## Phase 2 — Resource limits
**Status:** [ ]

- [ ] [BE] `src/models/limits.rs` — ResourceLimits struct with defaults
- [ ] [BE] `src/middleware/limits.rs` — validate AOI area, band count before job creation
- [ ] [BE] Limits configurable via env vars and portfolio settings
- [ ] [TEST] `cargo test` — oversized AOI rejected with 422
- [ ] [TEST] `cargo test` — too many concurrent jobs rejected with 429
- [ ] [TEST] `cargo test` — limits configurable via env
- [ ] [QA] cargo test green

## Phase 3 — Docker hardening
**Status:** [ ]

- [ ] [BE] `Dockerfile` — add non-root user (UID 1000)
- [ ] [BE] `Dockerfile` — add `pip-licenses` step, output to /licenses.txt
- [ ] [BE] `docker-compose.yml` — resource limits (cpus, memory)
- [ ] [BE] `docker-compose.yml` — security_opt: no-new-privileges
- [ ] [BE] `docker-compose.yml` — read_only filesystem + tmpfs for /tmp
- [ ] [TEST] `docker compose config` — validates
- [ ] [QA] Docker container starts and serves API

## Phase 4 — SBOM + licenses
**Status:** [ ]

- [ ] [BE] Install `syft` in Docker build → generate `sbom.spdx.json`
- [ ] [DOC] `LICENSES.md` — manual inventory of all dependencies + licenses
- [ ] [DOC] `LICENSE` — Apache 2.0 at repo root (verify it exists)
- [ ] [DOC] `docs/deployment/sbom.md` — how SBOM is generated and where
- [ ] [QA] sbom.spdx.json generated successfully in Docker build

## Phase 5 — Documentation
**Status:** [ ]

- [ ] [DOC] `docs/deployment/security-guide.md` — auth setup, TLS termination, resource limits
- [ ] [DOC] README.md — auth setup section
- [ ] [DOC] AGENTS.md — security testing instructions
- [ ] [DOC] Update SYSTEM_DESIGN.md with security layer
- [ ] [QA] Commit

---

### Progress

_None yet. Depends on 008-rust-control-plane + 011-review-workflow-monitoring._
