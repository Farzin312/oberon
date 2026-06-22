# Tasks — Security Hardening + FastAPI Server (Python)

**Parent**: [./README.md](./README.md)

---

## Phase 1 — FastAPI skeleton

- [ ] [BE] Add `fastapi`, `uvicorn` to `[server]` optional dependency in pyproject.toml
- [ ] [BE] Create `src/oberon/server/app.py` — app factory, health endpoint, route registration
- [ ] [BE] Create `src/oberon/server/__init__.py` — exports create_app()
- [ ] [BE] Write tests for health endpoint

Status: [ ]

## Phase 2 — API key auth

- [ ] [BE] Create `src/oberon/server/auth.py` — middleware, key hashing, validation
- [ ] [BE] Add `api_keys` table to db.py schema
- [ ] [BE] Add `oberon auth create-key` CLI subcommand
- [ ] [BE] Write tests for auth (valid key, missing key, invalid key)

Status: [ ]

## Phase 3 — Audit logging

- [ ] [BE] Create `src/oberon/server/audit.py` — middleware, SQLite insert, export
- [ ] [BE] Add `audit_log` table to db.py schema
- [ ] [BE] Add `GET /v1/audit/export` endpoint
- [ ] [BE] Write tests for audit logging

Status: [ ]

## Phase 4 — POST /v1/change endpoint

- [ ] [BE] Wire POST /v1/change to orchestrator (async via thread pool)
- [ ] [BE] Add GET /v1/jobs/{id} status endpoint
- [ ] [BE] Write integration tests for the change endpoint

Status: [ ]

## Phase 5 — Docker hardening

- [ ] [INFRA] Update docker-compose.yml with resource limits, non-root user, security_opt
- [ ] [DOC] Document server deployment in README

Status: [ ]

## QA Gate

- [ ] `uv run ruff check src/ tests/` => clean
- [ ] `uv run mypy src/` => clean
- [ ] `uv run pytest tests/ --ignore=tests/integration --ignore=tests/cli/test_request_json.py -q` => all pass
- [ ] `uv run bounds preflight --ci` => clean

Status: [ ]
