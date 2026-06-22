# 012 — Security Hardening + FastAPI Server (Python)

**Parent**: [../README.md](../README.md)

Wraps the CLI pipeline in a FastAPI HTTP server with API key authentication and audit logging. Makes Oberon deployable as a service for shared/hosted use.

The open-source core (Apache 2.0) remains fully functional WITHOUT the HTTP server. All pipeline features work via CLI without auth. This mini-SDD adds the optional server layer.

- **Reference:** Product Brief §10 (deployment + security), Blueprint §6 operational design
- **Prerequisite:** Pipeline validated (005 gate run, 013+014 calibration). Input validation already done (security audit fixes).

> **Hard rules:**
> 1. Telemetry disabled by default. No outbound analytics, no usage tracking, no phone-home.
> 2. Authentication is API-key based (header: `X-API-Key`), stored hashed in SQLite.
> 3. Resource limits (AOI area, timeout) are enforced per request.
> 4. Every API call is logged to an audit table with method, path, status, duration.
> 5. The CLI works WITHOUT any of these features. They are deployment-time additions.
> 6. FastAPI is an optional dependency (`pip install oberon[server]`).

---

## Locked decisions

| # | Decision | Choice |
|---|----------|--------|
| 1 | HTTP framework | FastAPI (uvicorn ASGI). Optional `[server]` extra in pyproject.toml. |
| 2 | Auth model | API keys (header `X-API-Key`), SHA-256 hashed, stored in SQLite |
| 3 | Audit log | SQLite table, append-only, exportable as JSON |
| 4 | Resource limits | Already enforced in orchestrator (AOI area cap, file size limit). Add request timeout. |
| 5 | Telemetry | Structured logs to stdout only. NO external telemetry. |
| 6 | Docker | Non-root user, resource limits, security_opt in docker-compose.yml |
