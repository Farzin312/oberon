# 001 — Data Plane Pipeline (Walking Vertical Slice) — Pipeline Build

**Parent**: [../README.md](../README.md)

Build the walking vertical slice of the Oberon data plane: a local Python pipeline that accepts one AOI, discovers Sentinel-2 scenes, assesses quality over the AOI, reads COG windows, produces aligned before/after arrays, computes deterministic baselines, and outputs evidence bundles with full provenance.

**Branch:** `feat/001-data-plane-pipeline`
**Status tracking:** see [`tasks.md`](./tasks.md)
**Strategy / contracts:** see [`plan.md`](./plan.md)

> ⚠️ **Hard rules:**
> 1. No AI during this slice. Deterministic baselines only — Clay inference is a separate mini-SDD.
> 2. Provenance is first-class product data, not logging. Every finding records source scenes, bands, processing config, and software version.
> 3. Abstention over confident failure. If inputs are poor, return explicit abstention — never a fake result.
> 4. COG reads are windowed over the AOI only — never download full scenes.
> 5. Every non-trivial logic path has a failing test before implementation (TDD).

---

## Locked decisions

| # | Decision | Choice |
|---|----------|--------|
| 1 | First task | **Material vegetation disturbance** — clear before/after signal, easier to define/evaluate than recovery |
| 2 | Sentinel-2 data source | **AWS Open Data Registry** (sentinel-2-l2a-cogs) — no API key required, direct COG range reads |
| 3 | STAC catalog | **Earth Search** (stac-index-alpha) or Microsoft Planetary Computer — both public, both support `intersects` and datetime range |
| 4 | Scene selection | **One-best-per-period** for the first benchmark — choose single best before and after acquisition by local valid-pixel fraction |
| 5 | Local quality | **Valid-pixel fraction over AOI** computed from SCL (cloud/shadow/snow = invalid) — not scene-level cloud % |
| 6 | Band set | **10 Sentinel-2 L2A bands** (B01, B02, B03, B04, B05, B06, B07, B08, B8A, B11, B12 — the standard 10-m/20-m stack) |
| 7 | CRS / grid | **UTM zone** of the AOI centroid (native Sentinel-2 CRS per tile), **10m** output resolution for all bands |
| 8 | Abstention threshold | **< 30% valid pixels** in either before or after observation → abstain |
| 9 | Minimum change area | **0.5 ha** (50+ 10m pixels) for a finding polygon — smaller than this is noise |
| 10 | Default output dir | `./oberon-output/<job-id>/` with subdirs for artifacts, evidence, and provenance |
| 11 | Package manager | **UV** (uv sync, uv add, uv lock) |
| 12 | Python src layout | `src/oberon/` with namespace subpackages under `core/`, `pipeline/`, `cli/`, `artifacts/` |

---

## In scope vs. NOT in scope

### ✅ IN SCOPE
- CLI command: `oberon analyze --aoi <file> --before <date> --after <date> [--task vegetation_disturbance] [--output <dir>]`
- STAC catalog discovery (Earth Search or Planetary Computer)
- Scene quality assessment (valid-pixel fraction over AOI via SCL)
- Windowed COG read (required bands over AOI bbox with 1-pixel buffer)
- SCL-based cloud, shadow, snow, no-data masking
- Reprojection to common CRS + resampling to common 10m grid
- NDVI, NBR difference computation
- Valid-pixel fraction change measurement
- Simple threshold-based change polygon extraction (connected components)
- Before/after true-color PNG composites
- Change overlay PNG (red highlight on before image)
- GeoJSON finding polygons with score, area, change metrics
- Provenance manifest (JSON) per finding
- Abstention result when inputs are poor
- CLI output to console summary + disk artifacts
- Tests: unit (index calc, masks, geometry, provenance), golden (fixed fixtures), integration (STAC query, COG read)
- `tests/data/` — sample geojson, small COG fixture

### ❌ NOT in scope / preserved as-is
- AI inference (Clay) — separate mini-SDD
- Rust control plane — future milestone
- Docker packaging — Phase 6 mini-SDD
- Web dashboard — out of MVP scope
- Multiple tasks (only `vegetation_disturbance`)
- Multi-polygon portfolios — Phase 9+ mini-SDD
- Scheduled monitoring — future
- Review queue / human approval workflow — future
- Object storage abstraction — local disk only for MVP

---

## Risk warnings

- ⚠️ **STAC catalog availability** — Earth Search and Planetary Computer are both public but have rate limits. Mitigated by caching STAC responses per session and failing with a clear message on timeout.
- ⚠️ **COG URL stability** — AWS S3 bucket structure for Sentinel-2 COGs could change. Mitigated by using the standard `sentinel-cogs.s3.us-west-2.amazonaws.com` pattern + documented dependency.
- ⚠️ **SCL band variations** — Different processing baselines (COPC vs PDGS) may use different SCL classification values. Tested via golden fixture against known-good scenes.
- ⚠️ **Large AOIs** — Polygons > 1000 km² will produce large arrays and slow processing. First implementation processes the full AOI in one pass; tiling is a future optimization. Documented limitation.

## Repos touched

1. `~/oberon` (this repo) — branch `feat/001-data-plane-pipeline`
