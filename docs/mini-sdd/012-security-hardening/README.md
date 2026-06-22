# 012 — Security Hardening + Production Safeguards

**Parent**: [../README.md](../README.md)

Product Brief Section 10 (lines 763-776): "Minimum production safeguards" for hosted deployments. The brief lists specific requirements: signed images, SBOM, auth, audit logging, resource limits, telemetry-off-by-default, and license records.

This mini-SDD makes Oberon safe to operate as a shared or hosted service. It is NOT needed for self-hosted single-user deployment.

- **Reference:** Product Brief §10, Blueprint §6 operational design principles
- **Prerequisite:** 008-rust-control-plane (API exists), 011-review-workflow-monitoring (multi-user data exists)

> **Hard rules:**
> 1. Telemetry disabled by default. No outbound analytics, no usage tracking, no phone-home.
> 2. Authentication is API-key based (simple, not OAuth). OAuth/SSO is enterprise (out of scope).
> 3. Resource limits (CPU, memory, job timeout) are enforced per request to prevent abuse.
> 4. Every API call is logged to an audit table with method, path, user, timestamp, response code.
> 5. The open-source core (Apache 2.0) must remain fully functional WITHOUT any of these security features. They are deployment-time additions, not compile-time requirements.

---

## Locked decisions

| # | Decision | Choice |
|---|----------|--------|
| 1 | Auth model | API keys (header: `X-API-Key`), stored hashed in SQLite |
| 2 | Audit log | SQLite table, append-only, exportable as JSON |
| 3 | Resource limits | Per-job: max AOI area (100 km²), max bands (11), timeout (300s), memory limit via Docker |
| 4 | Telemetry | Structured logs to stdout/stderr only. NO external telemetry. Configurable to file. |
| 5 | SBOM | `syft` generates SBOM at Docker build time; committed as `sbom.spdx.json` |
| 6 | License records | `LICENSES.md` at repo root listing all dependencies + their licenses |

---

## In scope vs NOT in scope

### IN SCOPE
- API key authentication middleware (Rust)
- Audit logging table + export endpoint
- Per-request resource limits (AOI size, band count, timeout)
- Docker resource constraints in docker-compose.yml
- SBOM generation in Dockerfile
- LICENSES.md with all dependency licenses
- Signed Docker images (cosign) — documented but not automated in CI

### NOT in scope
- OAuth2 / SSO / SAML (enterprise, post-pilot)
- Rate limiting (needs Redis or similar — defer)
- TLS termination (handled by reverse proxy / Caddy / nginx — documented)
- Multi-tenant data isolation (single deployment assumption)
- Secrets management (Vault, etc. — environment variables only)
- Automated vulnerability scanning CI (documented, not automated)

---

## Risk warnings

- Adding auth middleware to the Rust API changes every endpoint. Do this carefully with integration tests.
- Resource limits that are too aggressive will reject legitimate large-portfolio requests. Make limits configurable.
- SBOM tools (syft) may not catch transitive Python dependencies from the venv. Document the gap.
