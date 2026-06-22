# Roadmap

**Parent**: [README.md](../README.md)

Oberon is built in layers. Each layer must pass quality gates (ruff, mypy strict, pytest, provenance checks) before the next begins. Decision gates mark go/no-go points.

---

## Current status

| Layer | Mini-SDD | Status | Tests |
|-------|----------|--------|-------|
| Core pipeline | 001, 002, 010 | **Done** | 118 |
| AI experiment + evaluation | 003, 004, 005 | **Gate run: AI_ties** — AI remains experimental | 82 |
| Stability (registry, packaging) | 006, 007 | **Done** | 95 |
| Control plane (API contracts) | 008 | **Phase 1 (Python) done** — Rust deferred | 26 |
| Baseline calibration | 013 | **Done** — 12/12 golden tests | 277 |
| Spatial-variance seasonal detection | 014 | **Done** | 287 |
| Product (launch docs) | 009 | **Phase 0-3 done** — Phase 4 (partner prep) deferred | - |
| Review workflow | 011, 012 | Deferred (requires 008 Rust control plane) | - |

Total: 287 unit tests, 12 golden integration tests (live STAC, ~11 min).

---

## Build sequence

### Layer 1: Core pipeline (DONE)

| ID | Title | Outcome |
|----|-------|---------|
| 001 | Data plane pipeline | STAC -> baselines -> findings -> evidence bundles -> CLI. Full end-to-end. |
| 002 | Baseline fixes | Complete pixel_delta stub, write task contract, close 001 Phase 7. |
| 010 | Scene composite | Cloud-masked median composite when single scene insufficient. |

### Layer 2: AI experiment + evaluation (GATE RUN)

| ID | Title | Outcome |
|----|-------|---------|
| 003 | Clay experiment | Clay v1.5 adapter, tiled inference, `--use-ai` flag. Encoder-only feature extraction. |
| 004 | Benchmark dataset | 12 reviewed before/after pairs, golden integration test harness. |
| 005 | Evaluation harness | Live 12-example gate run: AI_ties, `precision_at_k` 0.1266 for both baseline and AI, no promotion. |

**Decision gate**: Clay did not improve over the deterministic NDVI/NBR baseline on the current 12-example benchmark. AI stays behind `--use-ai`; the next product work is baseline calibration, materiality filtering, and seasonal/no-change handling.

### Layer 3: Stability (DONE)

| ID | Title | Outcome |
|----|-------|---------|
| 006 | Model registry + provenance | Model version tracking, artifact index with checksums, provenance enrichment, COG cache, `--json`/`--cache` flags, API gap analysis. |
| 007 | Packaging + deployment | Docker Compose (CPU+GPU), multi-stage Dockerfile with uv + GDAL, structured JSON logging, health check. |

### Layer 4: Control plane (PHASE 1 DONE)

| ID | Title | Outcome |
|----|-------|---------|
| 008 | Rust control plane | Python-side API contracts complete (Pydantic v2). Serialization layer resolves 8 of 10 API gaps. Rust Axum server deferred until pipeline contracts proven. |

**Decision gate**: Only build the Rust control plane after the 005 evaluation gate passes and the Python pipeline contracts are stable. The Python CLI continues to work independently.

### Layer 5: Calibration (DONE)

| ID | Title | Outcome |
|----|-------|---------|
| 013 | Baseline calibration | Signed threshold (veg_disturbance = NDVI loss only), morphological closing (25x25, 250m), cross-season annotation. Golden tests 1/12 -> 12/12. |
| 014 | Spatial-variance seasonal detection | CV of NDVI loss distinguishes uniform seasonal senescence from patchy real disturbance. Abstains only when uniform AND broad. Annotates seasonal_risk in provenance otherwise. |

### Layer 6: Product (IN PROGRESS)

| ID | Title | Outcome |
|----|-------|---------|
| 009 | Launch docs | README/ARCHITECTURE/ROADMAP rewrite, SDK example, CLI reference. Phase 4 (partner prep) deferred. |

### Future layers (DEFERRED)

| ID | Title | Description |
|----|-------|-------------|
| 011 | Review workflow + monitoring | Portfolios, scheduled reruns, review states, alerts, feedback export. Requires 008 Rust control plane. |
| 012 | Security hardening | API auth, rate limiting, input sanitization, audit logging, SBOM. Requires 008 + 011. |

---

## Decision gates

1. **AI earns its place?** (005): The deterministic baseline must be the default. Clay AI promotion requires measurable improvement over NDVI/NBR on the benchmark dataset. If marginal, README describes Oberon as "deterministic-first with optional AI."

2. **Rust control plane?** (008): Only after the Python pipeline is proven (005 gate passed, contracts stable). Rust owns orchestration only — all geospatial logic stays in Python.

3. **Public launch?** (009+): Requires 005 gate resolved, 006 contracts stable, 007 Docker verified.

---

## Design principles (non-negotiable)

These principles govern every build decision:

1. **Deterministic baseline before AI** — AI must prove improvement over NDVI/NBR before promotion.
2. **Abstention over confident failure** — poor inputs produce explicit abstention, not fake results.
3. **Provenance is product data** — every finding records source scenes, config, model version, software version, artifacts.
4. **No microservices at MVP** — modular monolith. Separate processes only when demonstrated need.
5. **Python-first for geospatial/ML** — Rust control plane only after pipeline contracts are stable.
6. **TDD for any non-trivial logic** — write failing test first, watch it fail, then implement.

---

## Tech stack

- **Language**: Python 3.12+
- **Package manager**: uv
- **Geospatial**: rasterio, GDAL, shapely, geopandas
- **STAC**: pystac-client (Earth Search / Element84)
- **Array**: NumPy, SciPy
- **Imagery**: Pillow (PNG output)
- **AI (optional)**: torch, Clay v1.5 (in `[ai]` extras)
- **CLI**: click
- **API models**: Pydantic v2
- **Linting/types**: ruff (strict), mypy (strict)
- **Testing**: pytest
- **Packaging**: Docker (multi-stage, CPU + GPU profiles)
