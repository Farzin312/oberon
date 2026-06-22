# Plan — Rust Control Plane + Typed API

**Parent**: [../README.md](../README.md)

---

## 1. Repo facts

| Area | Current state | Source |
|---|---|---|
| CLI interface | Python click | `src/oberon/cli/` |
| Pipeline contracts | EvidenceBundle, Finding, ChangeRequest, etc. | `src/oberon/core/__init__.py` |
| Provenance + artifacts | Python | `src/oberon/artifacts/` |
| Cache | COG session cache (Python) | `src/oberon/pipeline/cog_reader.py` (after 006) |
| Python/Rust boundary | None — all Python | N/A |

---

## 2. Execution order

1. **Phase 0 — Rust project scaffold** — Cargo workspace, Axum boilerplate
2. **Phase 1 — Domain types in Rust** — match Python contracts
3. **Phase 2 — POST /v1/change endpoint** — typed request/response
4. **Phase 3 — Job state machine** — pending → running → completed/failed/abstained
5. **Phase 4 — Python subprocess** — call Python pipeline from Rust
6. **Phase 5 — Durable queue** — SQLite-backed job persistence
7. **Phase 6 — GET /v1/jobs/:id + artifact retrieval**
8. **Phase 7 — Integration test** — full Rust → Python → response path

---

## 3. Architecture

### 3.1 Boundary (Roadmap PDF lines 666-705)

```
Rust owns:                   Python owns:
├── API contracts            ├── STAC interaction
├── Job state machine        ├── Raster reads (COG)
├── Orchestration            ├── Masks + resampling
├── Persistence (SQLite)     ├── Spectral calculations
├── Request validation       ├── Clay/PyTorch inference
├── Queue interaction        ├── Geospatial postprocessing
└── Result delivery          └── Artifact production
```

Communication: Rust spawns Python via subprocess, passing a JSON request file path. Python writes results to output dir. Rust reads the results and serves them via API.

### 3.2 Typed request/response (from Product Brief §5)

```rust
// POST /v1/change
struct ChangeRequest {
    geometry: GeoJsonGeometry,      // Polygon or MultiPolygon
    before: TimeWindow,             // { from: NaiveDate, to: NaiveDate }
    after: TimeWindow,
    task: String,                   // "vegetation_disturbance"
    max_cloud_fraction: Option<f32>,
}

struct ChangeResponse {
    status: String,                 // "review_recommended" | "abstained" | "failed"
    findings: Vec<Finding>,
    observations: Observations,
    model: ModelInfo,
    artifacts: ArtifactPaths,
}

struct Finding {
    geometry: GeoJsonGeometry,
    change_score: f32,
    suggested_class: Option<String>,
    changed_area_m2: f64,
    evidence: EvidenceMetrics,
}
```

### 3.3 Job state machine

```
         ┌─→ queued ─→ running ─→ completed
         │                        ├── abstained
request ─┤                        └── failed
         ├── invalid (validation error)
         └── rejected (policy)
```

States stored in SQLite. Transitions are idempotent.

### 3.4 Python subprocess call

```rust
// Rust sends a request.json to /tmp/oberon/{job_id}/
// Spawns: python -m oberon.cli analyze --request /tmp/oberon/{job_id}/request.json --output /tmp/oberon/{job_id}/output/
// Reads: /tmp/oberon/{job_id}/output/index.json
// Returns: GET /v1/jobs/{id}
```

The CLI already supports `--aoi` and `--output`. Add `--request` mode that reads a JSON file instead of parsing --aoi/--before/--after flags. This is simpler than FFI.

---

## 4. Exact changes

### 4.1 Rust project
- `Cargo.toml` — workspace with `oberon-api` crate
- `src/main.rs` — Axum server boilerplate
- `src/routes/change.rs` — POST /v1/change handler
- `src/routes/jobs.rs` — GET /v1/jobs/:id handler
- `src/models/` — ChangeRequest, ChangeResponse, Finding, etc.
- `src/jobs/` — state machine, SQLite persistence
- `src/executor.rs` — Python subprocess manager

### 4.2 Python changes
- `src/oberon/cli/main.py` — add `--request` flag (read JSON request, run analysis)
- Keep all existing CLI flags working

### 4.3 Build infrastructure
- `Dockerfile.rust` — Rust API build stage (if different from Python Dockerfile)
- `docker-compose.yml` — add Rust service alongside Python (for split deployment)

---

## 5. Risk register

| Risk | Mitigation |
|---|---|
| Python-subprocess boundary fragile | Path-based JSON contract; validate JSON schema on both sides |
| Rust Axum knowledge gap for solo founder | Keep Rust API minimal; Python CLI as fallback. Don't ship Rust until it works reliably |
| Python subprocess too slow for interactivity | Acceptable at this stage — the queue is async |
| Duplicating Python validation in Rust | Rust validates only request shape; Python validates geospatial content |
| Cargo build slow (first time) | Phase 0: document expected build time (~5 min on M-series) |

---

## 6. End-phase cleanup

- Update `docs/architecture/SYSTEM_DESIGN.md` with Rust control plane
- Update `docs/mini-sdd/README.md` with reference to Rust/Python boundary
- Update AGENTS.md with Rust build/run instructions
- Update README.md with "API Server" section
