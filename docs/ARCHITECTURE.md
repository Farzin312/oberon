# Architecture

**Parent**: [README.md](../README.md)

Oberon's architecture follows a four-plane conceptual model. The MVP is a modular monolith: one Python process, clear stage boundaries, no distributed-system overhead.

---

## Four-plane model

### 1. Data Plane (`src/oberon/core/`, `src/oberon/pipeline/`)

The heart of Oberon. Satellite data becomes analysis-ready information.

| Subsystem | Module | Responsibility |
|-----------|--------|----------------|
| Portfolio input | `core/__init__.py` | Accept polygons, date windows, task configuration |
| Catalog discovery | `pipeline/stac_discovery.py` | Search STAC catalogs for candidate Sentinel-2 observations |
| Scene quality | `pipeline/scene_quality.py` | Determine which observations are locally usable over the AOI |
| Raster access | `pipeline/cog_reader.py` | Read only the required COG windows over the AOI |
| Preparation | `pipeline/preparation.py` | Mask invalid pixels, normalize bands, reproject, resample, align |
| Baseline analytics | `core/baselines.py` | Compute NDVI, NBR, NDMI, pixel deltas, valid-pixel fractions |
| AI inference | `ai/clay_adapter.py` | Produce embeddings, feature differences via versioned model adapter |
| Postprocessing | `core/change_detection.py` | Convert pixel output to polygons, areas, severity metrics |
| Evidence production | `artifacts/` | Before/after images, overlays, GeoJSON, provenance manifests |

### 2. Control Plane (`src/oberon/cli/`, `src/oberon/api/`)

Orchestrates work. Does NOT contain geospatial or model logic.

| Subsystem | Module | Responsibility |
|-----------|--------|----------------|
| CLI | `cli/main.py` | Accept analysis request via click commands |
| Orchestrator | `cli/orchestrator.py` | Call data-plane stages in order, manage abstention |
| API contracts | `api/contracts.py` | Pydantic v2 models matching Product Brief §5 |
| Serialization | `api/serialization.py` | Transform EvidenceBundle to API response shape |
| Request validation | `api/contracts.py` | Validate geometry, dates, task type (Pydantic validators) |

The Rust control plane (008, deferred) will own job state, persistence, and async orchestration. It spawns Python via subprocess with JSON contracts. Python owns all geospatial logic.

### 3. Trust and Decision Plane (`src/oberon/core/`, `src/oberon/artifacts/`)

What separates Oberon from a basic imagery script.

| Subsystem | Module | Responsibility |
|-----------|--------|----------------|
| Quality policy | `pipeline/preparation.py` | Decide whether inputs are good enough (valid-pixel fraction) |
| Abstention | `cli/orchestrator.py` | Refuse when evidence is unreliable (exit 0, "Abstained:" prefix) |
| Provenance | `artifacts/provenance.py` | Record exactly how each finding was produced |
| Evidence bundles | `artifacts/__init__.py` | Package everything needed to inspect a result |
| Evaluation | `ai/comparison.py` | Measure performance against labeled examples |
| Ranking | `core/change_detection.py` | Score and order findings by NDVI delta significance |
| Model registry | `config/model_registry.py` | Track model versions, artifacts, calibration state |

### 4. Commercial Operating Plane (future)

Accounts, auth, billing, alerts, enterprise integration. Not built during MVP.

---

## Pipeline flow

```
                    ChangeRequest (AOI + dates + thresholds)
                              |
                              v
                    +-------------------+
                    | STAC Discovery    |  search_catalog()
                    | (Earth Search)    |  -> list[CandidateScene]
                    +-------------------+
                              |
                              v
                    +-------------------+
                    | Scene Quality     |  rank_by_scene_quality()
                    | Assessment        |  -> list[SelectedScene]
                    +-------------------+
                              |
                    +---------+---------+
                    |                   |
                    v                   v
             +-----------+       +-----------+
             | Before    |       | After     |
             | COG Read  |       | COG Read  |  read_window()
             +-----------+       +-----------+
                    |                   |
                    |     (composite    |
                    |      if needed)   |
                    v                   v
                    +-------------------+
                    | Preparation       |  align_to_common_grid()
                    | (mask, reproject, |  -> PreparedPair
                    |  align)           |
                    +-------------------+
                              |
                    +---------+---------+
                    |                   |
                    v                   v
             +-----------+       +-----------+
             | Baselines |       | AI (opt)  |
             | NDVI/NBR  |       | Clay v1.5 |
             | NDMI      |       | embeddings|
             +-----------+       +-----------+
                    |                   |
                    +---------+---------+
                              |
                              v
                    +-------------------+
                    | Change Detection  |  extract_findings()
                    | (threshold + CC)  |  deduplicate_and_rank()
                    +-------------------+
                              |
                              v
                    +-------------------+
                    | Evidence Bundle   |  build_evidence_bundle()
                    | (GeoJSON, PNG,    |  -> EvidenceBundle
                    |  provenance)      |
                    +-------------------+
                              |
                              v
                    ChangeResponse (API shape)
                    or EvidenceBundle (CLI)
```

## Boundary: Rust vs Python (008, deferred)

```
Rust owns:                     Python owns:
- API contracts (serde)         - STAC interaction
- Job state machine             - Raster reads (COG)
- Orchestration                 - Masks + resampling
- Persistence (SQLite)          - Spectral calculations
- Request shape validation      - Clay/PyTorch inference
- Queue interaction             - Geospatial postprocessing
- Result delivery               - Artifact production
```

Communication: Rust spawns Python via subprocess, passing a JSON request file path. Python writes results to output dir. Rust reads the response and serves via HTTP. No FFI, no shared memory.

## Key design decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Language | Python-first | Mature EO ecosystem (Rasterio, GDAL, NumPy, Shapely). Rust control plane later. |
| Architecture | Modular monolith | Clear boundaries without distributed-system overhead. Deploy as one process + optional GPU worker. |
| Functional core | Pure functions | Deterministic, testable, no hidden state. Side effects only in the outer shell. |
| Idempotency | Every stage | Same inputs -> same outputs. Stable IDs + checksums. |
| Storage | Filesystem/object for data, SQLite for metadata | Don't put large raster payloads in operational database. |
| Provenance | First-class product data | Every finding answers: source scenes, bands, config, model, version. |
| Deterministic before AI | NDVI/NBR baseline is primary | AI must prove improvement over baseline before promotion. |
| Abstention over failure | Exit 0 with reason | Poor inputs are a valid analysis result, not an error. |

## Performance principles

- **Windowed COG reads only** — never download a full scene. Read the AOI-bounded window plus a small buffer.
- **Prepared chip cache** — cache analysis windows to avoid re-reading.
- **Pre-compute valid-pixel mask** — quality assessment reuses the same mask across all baselines.
- **Stage-level idempotency** — enables safe retry without re-reading upstream.
- **Array operations, not pixel loops** — use NumPy/Rasterio array ops, never Python pixel iteration.
- **256x256 chips for AI** — standard chip size for Clay v1.5, enables batching on GPU.

## Source layout

```
src/oberon/
  __init__.py              # version
  core/
    __init__.py            # All dataclass contracts (ChangeRequest, Finding, etc.)
    baselines.py           # NDVI, NBR, NDMI, pixel_delta computation
    change_detection.py    # Thresholding, connected components, finding extraction
    geometry.py            # AOI geometry helpers
  pipeline/
    stac_discovery.py      # STAC search + scene quality ranking
    scene_quality.py       # Local (over-AOI) quality assessment
    cog_reader.py          # Windowed COG reads + session cache
    preparation.py         # SCL masking, reprojection, alignment, composite
  ai/
    model_adapter.py       # ModelAdapter Protocol (runtime_checkable)
    clay_adapter.py        # ClayAdapter — Clay v1.5 encoder-only
    clay_config.py         # Clay-specific constants (bands, wavelengths, dims)
    tiled_inference.py     # Chip grid, extract, stitch embeddings
    comparison.py          # AI vs baseline evaluation
  artifacts/
    __init__.py            # build_evidence_bundle() orchestrator
    geojson.py             # GeoJSON findings writer
    images.py              # True-color + change overlay PNG rendering
    provenance.py          # Provenance manifest builder + writer
  api/
    contracts.py           # Pydantic v2 API models (Product Brief §5)
    serialization.py       # EvidenceBundle -> ChangeResponse transform
  cli/
    main.py                # CLI entry (analyze, health)
    orchestrator.py        # Full pipeline orchestration with abstention
  config/
    model_registry.py      # Model version tracking
  store/
    artifact_index.py      # Per-run artifact checksum index
  telemetry/
    logging.py             # Structured JSON logging (stdlib)
```
