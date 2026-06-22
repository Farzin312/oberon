# 012 — Security Hardening

**Parent**: [../README.md](../README.md)

Security hardening for the Oberon control plane: API key authentication, audit
logging, Docker hardening, and Python-side pipeline security (input validation,
timeouts, RCE mitigation).

> **Implementation note:** Originally planned as Python/FastAPI. Re-decided in
> favor of Rust control plane (Gate 9). The HTTP server, auth, and audit
> middleware are implemented in Rust (Axum). Python-side security hardening
> (STAC timeout/retry, COG timeout, AOI cap, input validation, torch.load RCE
> mitigation) was done during the post-014 security audit and remains in Python.

The open-source core (Apache 2.0) remains fully functional WITHOUT the server.
All pipeline features work via CLI without auth.

- **Reference:** Product Brief §10 (deployment + security), Blueprint §6 operational design
- **Prerequisite:** Pipeline validated (005 gate run, 013+014 calibration). Input validation already done (security audit fixes).
- **Status:** DONE — Rust control plane has auth, audit, non-root Docker. Python pipeline has input validation, timeouts, cache eviction.

> **Hard rules:**
> 1. Telemetry disabled by default. No outbound analytics, no usage tracking, no phone-home.
> 2. Authentication is API-key based (header: `X-API-Key`), stored hashed (SHA-256) in SQLite.
> 3. Resource limits (AOI area, timeout) are enforced per request.
> 4. Every API call is logged to an audit table with method, path, status, duration.
> 5. The CLI works WITHOUT any of these features. They are deployment-time additions.

---

## Locked decisions

| # | Decision | Choice |
|---|----------|--------|
| 1 | HTTP framework | Axum (Rust). Server in `control-plane/` directory. |
| 2 | Auth model | API keys (header `X-API-Key`), SHA-256 hashed, stored in SQLite. OBERON_AUTH_DISABLED=1 for local dev. |
| 3 | Audit log | SQLite audit_log table, append-only, exportable via GET /v1/audit/export |
| 4 | Resource limits | AOI area cap (50k ha), file size limit (10 MB), STAC/COG timeouts. Enforced in Python orchestrator + Rust config. |
| 5 | Telemetry | Structured logs to stdout only (tracing in Rust, stdlib logging in Python). NO external telemetry. |
| 6 | Docker | Non-root user, resource limits, multi-stage build (Dockerfile.server) |
