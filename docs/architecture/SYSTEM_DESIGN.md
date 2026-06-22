# System Design

**Parent**: [README.md](README.md)

## Four-plane architecture model

The four planes are a **conceptual planning model**, not a deployment architecture. The MVP is a modular monolith with Python responsible for all geospatial and ML logic.

### 1. Data Plane (oberon/core/)

The heart of Oberon — satellite data becomes analysis-ready information.

| Subsystem | Responsibility |
|-----------|---------------|
| Portfolio input | Accept polygons, date windows, task configuration |
| Catalog discovery | Search STAC catalogs for candidate Sentinel-2 observations |
| Scene quality | Determine which observations are locally usable over the AOI |
| Raster access | Read only the required COG windows over the AOI |
| Preparation | Mask invalid pixels, normalize bands, reproject, resample, crop, align dates |
| Baseline analytics | Compute NDVI, NBR, NDMI, pixel deltas, valid-pixel fractions |
| AI inference | Produce embeddings, feature differences via versioned model adapter |
| Postprocessing | Convert pixel output to polygons, areas, severity metrics |
| Evidence production | Before/after images, overlays, masks, GeoJSON, provenance manifests |

### 2. Control Plane (oberon/cli/, later Rust API)

Orchestrates work — does NOT contain geospatial or model logic.

| Subsystem | Responsibility |
|-----------|---------------|
| CLI/API | Accept analysis request |
| Request validation | Validate geometry, dates, task type, thresholds |
| Job state machine | Track pending → running → completed/failed/abstained |
| Orchestrator | Call data-plane stages in order |
| Queue | Async processing for long-running work |
| Metadata persistence | Store jobs, scene selections, outputs, provenance |

### 3. Trust & Decision Plane (oberon/core/)

What separates Oberon from a basic imagery script.

| Subsystem | Responsibility |
|-----------|---------------|
| Quality policy | Decide whether inputs are good enough |
| Abstention | Refuse when evidence is unreliable |
| Provenance | Record exactly how each finding was produced |
| Evidence bundles | Package everything needed to inspect a result |
| Evaluation | Measure performance against labeled examples |
| Ranking | Score and order findings by significance |

### 4. Commercial Operating Plane (future)

Accounts, auth, billing, alerts, enterprise — not built during MVP.

## Key design decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Language | Python-first | Mature EO ecosystem (Rasterio, GDAL, NumPy, Shapely). Rust control plane later. |
| Architecture | Modular monolith | Clear boundaries without distributed-system overhead. Deploy as one process + optional GPU worker. |
| Functional core | Pure functions | Deterministic, testable, no hidden state. Side effects only in outer shell. |
| Idempotency | Every stage | Same inputs → same outputs. Stable IDs + checksums. |
| Storage | Filesystem/object for data, SQLite for metadata | Don't put large raster payloads in operational database. |
| Provenance | First-class product data | Every finding answers: source scenes, bands, config, model, version. |

## Subsystem map

```
┌─────────────────────────────────────────────────────┐
│                   CLI (oberon.cli)                   │
│              accepts AOI + date windows              │
└────────────────────┬────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────┐
│              Orchestrator (oberon.pipeline)          │
│         calls stages in order, manages state         │
└──┬───────┬───────┬──────┬───────┬──────┬───────────┘
   │       │       │      │       │      │
   ▼       ▼       ▼      ▼       ▼      ▼
 STAC   Scene   COG   Prep   Base-   AI     Evidence
 Discov Quality  Read       lines  (opt)  Bundles
```

## Performance principles

- **Windowed COG reads only** — never download a full scene. Read the AOI-bounded window plus a small buffer.
- **Prepared chip cache** — cache analysis windows to avoid re-reading.
- **Pre-compute valid-pixel mask** — quality assessment reuses the same mask across all baselines.
- **Stage-level idempotency** — enables safe retry without re-reading upstream.
- **Array operations, not pixel loops** — use NumPy/Rasterio array ops, never Python pixel iteration.
- **256x256 chips for AI** — standard chip size for Clay v1.5, enables batching on GPU.

## Memory optimization

- Release intermediate arrays after each stage (del Python objects, let GC collect).
- Use memory-mapped reads for large COGs (Rasterio handles this natively).
- Process tiles, not full arrays, for polygons larger than a single chip.
- Stream evidence writes to disk instead of building full in-memory buffers.
- Profile with `memory_profiler` on real AOIs before optimizing.
