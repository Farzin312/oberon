# Plan — Security Hardening + FastAPI Server (Python)

**Parent**: [./README.md](./README.md)

---

## 1. Repo facts

| Area | Current state | Source |
|---|---|---|
| HTTP server | None — CLI only | `cli/main.py` |
| Auth | None | N/A |
| Input validation | DONE — AOI cap, file size limit, geometry validation, cloud fraction range | `orchestrator.py`, `contracts.py`, `main.py` |
| Rate limiting | DONE — STAC timeout + retry | `stac_discovery.py` |
| Audit log | Structured JSON logging to stdout | `telemetry/logging.py` |

---

## 2. Architecture

### 2.1 Module layout

```
src/oberon/server/
    __init__.py
    app.py              (FastAPI app factory, route definitions)
    auth.py             (API key middleware, key hashing)
    audit.py            (Audit log middleware, SQLite append-only)
    schemas.py          (Pydantic models for API requests/responses — reuse api/contracts.py)
```

### 2.2 API surface

| Endpoint | Method | Auth | Purpose |
|---|---|---|---|
| `/v1/health` | GET | None | Health check |
| `/v1/change` | POST | Required | Run change analysis |
| `/v1/jobs/{id}` | GET | Required | Get job status |
| `/v1/audit/export` | GET | Required | Export audit log |

### 2.3 Auth flow

```
Request → middleware extracts X-API-Key header
       → SHA-256(key) looked up in api_keys table
       → If valid: attach user to request state
       → If invalid: 401 Unauthorized
       → If missing: 401 Unauthorized
```

Key creation: `oberon auth create-key --user "name"` → prints key once.

### 2.4 SQLite schema (shared with 011)

```sql
CREATE TABLE IF NOT EXISTS api_keys (
    key_hash TEXT PRIMARY KEY,
    user_name TEXT NOT NULL,
    created_at TEXT NOT NULL,
    last_used TEXT
);

CREATE TABLE IF NOT EXISTS audit_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    method TEXT NOT NULL,
    path TEXT NOT NULL,
    user_name TEXT,
    status_code INTEGER NOT NULL,
    duration_ms INTEGER NOT NULL,
    request_body_hash TEXT
);
```

---

## 3. Execution order

1. **Phase 1 — FastAPI skeleton** — app factory, health endpoint, uvicorn entry point
2. **Phase 2 — API key auth** — middleware, key creation/hashing, `oberon auth create-key`
3. **Phase 3 — Audit logging** — middleware, SQLite table, export endpoint
4. **Phase 4 — POST /v1/change** — wire to orchestrator with async job execution
5. **Phase 5 — Docker hardening** — non-root user, resource limits, security_opt

---

## 4. Risk register

| Risk | Mitigation |
|---|---|
| FastAPI adds heavy dependency | Optional `[server]` extra. Core CLI has no FastAPI dependency. |
| Long-running analysis blocks event loop | Run pipeline in thread pool or subprocess, return job ID |
| Auth breaks existing CLI users | CLI never requires auth. Auth only on HTTP layer. |
