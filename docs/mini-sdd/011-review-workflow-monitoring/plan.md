# Plan — Review Workflow + Monitoring System (Python/SQLite)

**Parent**: [./README.md](./README.md)

---

## 1. Repo facts

| Area | Current state | Source |
|---|---|---|
| Pipeline | Full CLI: `oberon analyze` → EvidenceBundle | `cli/main.py`, `cli/orchestrator.py` |
| Persistence | None — filesystem only | N/A |
| Finding model | Finding dataclass (geometry, score, evidence) | `core/__init__.py` |
| CLI framework | click 8+ | `cli/main.py` |

---

## 2. Architecture

### 2.1 SQLite schema

```sql
CREATE TABLE IF NOT EXISTS portfolios (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    task TEXT NOT NULL DEFAULT 'vegetation_disturbance',
    max_cloud_fraction REAL NOT NULL DEFAULT 0.15,
    alert_webhook_url TEXT,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS portfolio_polygons (
    id TEXT PRIMARY KEY,
    portfolio_id TEXT NOT NULL REFERENCES portfolios(id) ON DELETE CASCADE,
    geometry_json TEXT NOT NULL,
    label TEXT,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS runs (
    id TEXT PRIMARY KEY,
    portfolio_id TEXT NOT NULL REFERENCES portfolios(id),
    polygon_id TEXT NOT NULL REFERENCES portfolio_polygons(id),
    output_dir TEXT NOT NULL,
    findings_count INTEGER NOT NULL DEFAULT 0,
    abstained INTEGER NOT NULL DEFAULT 0,
    ran_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS reviews (
    id TEXT PRIMARY KEY,
    run_id TEXT NOT NULL REFERENCES runs(id),
    finding_idx INTEGER NOT NULL,
    portfolio_id TEXT NOT NULL REFERENCES portfolios(id),
    state TEXT NOT NULL CHECK(state IN ('pending','approved','rejected','uncertain')),
    reviewer_notes TEXT,
    reviewed_at TEXT,
    created_at TEXT NOT NULL,
    UNIQUE(run_id, finding_idx)
);
```

### 2.2 CLI surface

| Command | Purpose |
|---|---|
| `oberon portfolio create --name "Amazon" --task vegetation_disturbance` | Create portfolio |
| `oberon portfolio list` | List all portfolios |
| `oberon portfolio add-polygon <id> --aoi aoi.geojson --label "Plot A"` | Add polygon to portfolio |
| `oberon portfolio run <id>` | Run analysis for all polygons in portfolio |
| `oberon portfolio status <id>` | Show latest runs + findings per polygon |
| `oberon review list --portfolio <id> --state pending` | List findings awaiting review |
| `oberon review update --run <run_id> --idx 1 --state approved` | Submit review |
| `oberon portfolio export-feedback <id>` | Export all review decisions as CSV/JSON |

### 2.3 Module layout

```
src/oberon/store/
    __init__.py
    artifact_index.py     (existing)
    db.py                 (NEW — SQLite connection, schema init, migrations)
src/oberon/portfolio/
    __init__.py
    models.py             (NEW — Portfolio, Polygon, Run, ReviewDecision dataclasses)
    manager.py            (NEW — CRUD operations via db.py)
    cli.py                (NEW — click subcommands for portfolio/review)
    alerts.py             (NEW — webhook delivery)
    feedback.py           (NEW — CSV/JSON export)
```

---

## 3. Execution order

1. **Phase 1 — DB layer + models** — SQLite schema, connection management, dataclasses
2. **Phase 2 — Portfolio CRUD** — Create/list/delete portfolios, add/remove polygons
3. **Phase 3 — Portfolio run** — Execute pipeline for all polygons, store runs + findings
4. **Phase 4 — Review states** — Finding lifecycle: pending → approved/rejected/uncertain
5. **Phase 5 — Feedback export + webhook alerts**

---

## 4. Risk register

| Risk | Mitigation |
|---|---|
| SQLite not suitable for concurrent writes | Document WAL mode + single-writer assumption for OSS |
| Review queue floods with false positives | Alert threshold configurable; default conservative |
| Webhook delivery failures | Retry 3x with backoff; mark as delivery_failed |
