# Plan — Security Hardening + Production Safeguards

**Parent**: [../README.md](./README.md)

---

## 1. Repo facts

| Area | Current state | Source |
|---|---|---|
| Auth | None — open API | Rust API (008) |
| Audit log | Structured logs only | `structlog` output |
| Resource limits | Job timeout (300s) only | orchestrator.py |
| Docker constraints | None | docker-compose.yml |
| SBOM | None | N/A |
| License records | pyproject.toml has license field only | repo root |

---

## 2. Execution order

1. **Phase 0 — API key auth** — middleware + key storage
2. **Phase 1 — Audit logging** — append-only table + export
3. **Phase 2 — Resource limits** — AOI size, band count, timeout enforcement
4. **Phase 3 — Docker hardening** — resource constraints, non-root user
5. **Phase 4 — SBOM + licenses** — syft, LICENSES.md
6. **Phase 5 — Documentation** — deployment security guide

---

## 3. Architecture

### 3.1 API key auth (Rust middleware)

```rust
// Middleware: extract X-API-Key header, validate against SQLite
async fn auth_middleware(req: Request, next: Next) -> Response {
    let key = req.headers().get("X-API-Key")?;
    let user = validate_key(key)?;  // SELECT FROM api_keys WHERE key_hash = ?
    req.extensions().insert(user);
    next.run(req).await
}
```

Keys stored as SHA-256 hashes. Created via CLI: `oberon auth create-key --user "name"`.

### 3.2 Audit log

```sql
CREATE TABLE audit_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    method TEXT NOT NULL,
    path TEXT NOT NULL,
    user_id TEXT,
    status_code INTEGER NOT NULL,
    duration_ms INTEGER NOT NULL,
    request_body_hash TEXT
);
```

Export: `GET /v1/audit/export?from=2026-01-01&to=2026-06-30` → JSON array.

### 3.3 Resource limits

| Limit | Default | Configurable |
|---|---|---|
| Max AOI area | 100 km² | Yes, per portfolio |
| Max bands requested | 11 (all S-2) | No |
| Job timeout | 300s | Yes |
| Concurrent jobs per user | 3 | Yes |
| Max polygons per portfolio | 1000 | Yes |
| Max findings returned | 50 | Yes |

Enforced in Rust API before job creation.

### 3.4 Docker hardening

```yaml
# docker-compose.yml additions
services:
  oberon-api:
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 4G
    user: "1000:1000"   # non-root
    read_only: true
    tmpfs:
      - /tmp
    security_opt:
      - no-new-privileges:true
```

### 3.5 SBOM

```dockerfile
# In Dockerfile
RUN syft dir:/app -o spdx-json > /sbom.spdx.json
```

---

## 4. Exact changes

### 4.1 Rust control plane
- `src/auth/mod.rs` — API key middleware
- `src/auth/keys.rs` — key creation, validation, hashing
- `src/routes/audit.rs` — audit export endpoint
- `src/middleware/limits.rs` — request validation against limits
- `src/models/limits.rs` — ResourceLimits struct

### 4.2 Database
- `migrations/004_api_keys.sql`
- `migrations/005_audit_log.sql`

### 4.3 Infrastructure
- `Dockerfile` — add non-root user, syft SBOM step
- `docker-compose.yml` — resource constraints, security_opt
- `LICENSES.md` — manual inventory of all dependencies

### 4.4 Python CLI
- `src/oberon/cli/main.py` — add `oberon auth create-key` subcommand

---

## 5. Risk register

| Risk | Mitigation |
|---|---|
| Auth breaks existing API consumers | Phase 0: allow `OBERON_AUTH_DISABLED=1` env var for local dev |
| Audit table grows unbounded | Document retention policy (90 days default); add cleanup job |
| Resource limits reject legitimate use | All limits configurable; document how to raise |
| SBOM incomplete for Python deps | Use `pip-licenses` for Python layer; syft for Docker layer; document gap |
| Non-root Docker breaks file permissions | Volume mount ownership documented in README |

---

## 6. End-phase cleanup

- `docs/deployment/security-guide.md` — comprehensive security configuration
- Update README.md with auth setup instructions
- Update AGENTS.md with security testing notes
- All open-source core features work WITHOUT auth (auth is middleware, not core)
