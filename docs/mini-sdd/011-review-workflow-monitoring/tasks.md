# Tasks — Review Workflow + Monitoring System (Python/SQLite)

**Parent**: [./README.md](./README.md)

---

## Phase 1 — DB layer + models

- [ ] [BE] Create `src/oberon/store/db.py` — SQLite connection, schema init, WAL mode
- [ ] [BE] Create `src/oberon/portfolio/models.py` — Portfolio, Polygon, Run, ReviewDecision dataclasses
- [ ] [BE] Write tests for db.py (schema creation, idempotent migrations, connection handling)

Status: [ ]

## Phase 2 — Portfolio CRUD

- [ ] [BE] Create `src/oberon/portfolio/manager.py` — CRUD operations
- [ ] [BE] Create `src/oberon/portfolio/cli.py` — click subcommands (create, list, add-polygon, status)
- [ ] [BE] Write tests for CRUD operations

Status: [ ]

## Phase 3 — Portfolio run

- [ ] [BE] Implement `portfolio run <id>` — loop polygons, call run_analysis, store runs + reviews
- [ ] [BE] Implement `portfolio status <id>` — show latest runs + pending review counts
- [ ] [BE] Write tests for run + status

Status: [ ]

## Phase 4 — Review states

- [ ] [BE] Implement `review list` — list findings by portfolio + state
- [ ] [BE] Implement `review update` — submit review decision
- [ ] [BE] Write tests for review lifecycle

Status: [ ]

## Phase 5 — Feedback export + webhook alerts

- [ ] [BE] Implement `portfolio export-feedback` — JSON + CSV export
- [ ] [BE] Implement webhook alert delivery (with retry/backoff)
- [ ] [BE] Write tests for export + alerts

Status: [ ]

## QA Gate

- [ ] `uv run ruff check src/ tests/` => clean
- [ ] `uv run mypy src/` => clean
- [ ] `uv run pytest tests/ --ignore=tests/integration --ignore=tests/cli/test_request_json.py -q` => all pass
- [ ] `uv run bounds preflight --ci` => clean

Status: [ ]
