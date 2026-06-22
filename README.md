# Oberon

**Open, self-hostable Earth observation monitoring engine.**

Oberon turns public satellite imagery (Sentinel-2 L2A) into ranked, evidence-backed change findings for defined land portfolios. Users supply an area of interest and before/after time windows. Oberon returns ranked change polygons, spectral evidence, before/after imagery, and full provenance for every finding.

[Installation](#installation) | [Quick Start](#quick-start) | [Architecture](#architecture) | [Roadmap](#roadmap) | [Contributing](#contributing)

---

## Why Oberon?

Existing EO tools either dump raw imagery (too low-level) or lock change detection behind a paid API (too opaque). Oberon is the middle path:

- **Deterministic by default** — spectral baselines (NDVI, NBR, NDMI) are the primary signal. No black-box dependency for the core workflow.
- **Optional AI triage** — Clay v1.5 foundation model embeddings run alongside baselines. AI must prove it improves over the deterministic path before promotion.
- **Abstention over confident failure** — when inputs are poor (cloud cover, insufficient pixels), Oberon says so explicitly instead of producing a garbage result.
- **Provenance is product data** — every finding records source scenes, bands, processing config, model version, software version, and artifact paths. Not a log line. A verifiable record.
- **Self-hostable** — runs on your machine or in Docker. No telemetry, no API keys required for the core pipeline.

## What it does

```
AOI polygon + before/after date windows
  -> STAC catalog search (Sentinel-2 L2A, Earth Search / Element84)
  -> Scene quality assessment (over the AOI, not scene-level)
  -> Windowed COG read + SCL cloud/shadow masking
  -> Reprojection, resampling, alignment
  -> Deterministic baselines (NDVI, NBR, NDMI, pixel deltas)
  -> Optional AI branch (Clay v1.5 feature extraction)
  -> Cloud-masked composite (when single scene is insufficient)
  -> Change detection (thresholding, connected components)
  -> Ranked GeoJSON findings + evidence bundles (PNG, provenance manifest)
  -> Explicit abstention when evidence is weak
```

## Installation

### Prerequisites

- Python 3.12+
- [uv](https://docs.astral.sh/uv/) package manager
- GDAL system libraries (included in Docker image; for local install see [CONTRIBUTING.md](docs/CONTRIBUTING.md))

### Local (uv)

```bash
git clone https://github.com/farzin/oberon.git
cd oberon
uv sync
```

### Docker (recommended for first run)

```bash
docker build -t oberon:cpu .
```

## Quick start

### Analyze an area of interest

```bash
# Provide a GeoJSON polygon and before/after dates
oberon analyze \
  --aoi path/to/polygon.geojson \
  --before 2026-01-01 --after 2026-06-01 \
  --task vegetation_disturbance \
  -o output/
```

Output in `output/`:
- `before.png`, `after.png`, `overlay.png` — true-color imagery + change overlay
- `findings.geojson` — ranked change polygons with NDVI/NBR deltas and area
- `provenance.json` — full provenance manifest (scenes, config, model versions)

### With AI triage (requires torch + Clay checkpoint)

```bash
uv sync --extra ai
oberon analyze \
  --aoi path/to/polygon.geojson \
  --before 2026-01-01 --after 2026-06-01 \
  --use-ai -o output/
```

### Cloud-masked composite

When the best single scene has too much cloud cover over the AOI, Oberon can merge up to 3 scenes per period:

```bash
oberon analyze \
  --aoi path/to/polygon.geojson \
  --before 2026-01-01 --after 2026-06-01 \
  --composite -o output/
```

### JSON output (for programmatic use)

```bash
oberon analyze \
  --aoi path/to/polygon.geojson \
  --before 2026-01-01 --after 2026-06-01 \
  --json
```

Outputs the full Product Brief section 5 response shape (status, findings with change_score/changed_area_m2/evidence, artifacts).

### Request file mode (API contract input)

```bash
# Run from a JSON request file (ChangeRequestAPI schema)
oberon analyze --request request.json -o output/
```

The request JSON format:
```json
{
  "geometry": {"type": "Polygon", "coordinates": [[[...]]]},
  "before": {"from": "2026-01-01", "to": "2026-02-01"},
  "after": {"from": "2026-06-01", "to": "2026-07-01"}
}
```

This is the same shape the Rust control plane will use. `--request` cannot be combined with `--aoi`.

### Docker

```bash
# CPU
docker run --rm \
  -v "$PWD/input:/input:ro" \
  -v "$PWD/output:/output" \
  oberon:cpu analyze \
    --aoi /input/polygon.geojson \
    --before 2026-01-01 --after 2026-06-01 \
    -o /output

# GPU (requires nvidia-docker runtime)
docker compose --profile gpu run --rm oberon-gpu analyze \
  --aoi /input/polygon.geojson \
  --before 2026-01-01 --after 2026-06-01 \
  --use-ai -o /output
```

### Health check

```bash
oberon health          # CLI
oberon health --json   # programmatic
```

## Architecture

Oberon follows a four-plane conceptual model. See [ARCHITECTURE.md](ARCHITECTURE.md) for the full system design.

```
Data Plane        -> STAC discovery, COG reads, spectral baselines, AI inference
Control Plane     -> CLI orchestration, API contracts, job state
Trust Plane       -> Abstention, provenance, evidence bundles, evaluation
Commercial Plane  -> (future) accounts, auth, billing
```

Key design decisions:
- **Modular monolith** — one Python process, clear stage boundaries, no microservices.
- **Python-first** — Rust control plane deferred until pipeline contracts are stable.
- **Functional core** — pipeline stages are pure functions. Side effects only in the outer shell.
- **Windowed reads only** — never download a full scene. Read only the AOI-bounded window.

## Roadmap

See [ROADMAP.md](ROADMAP.md) for the phased build plan and current status.

| Layer | Status |
|-------|--------|
| Core pipeline (STAC -> baselines -> findings) | **Done** |
| Clay AI experiment + evaluation harness | **Gate run: AI_ties** — AI remains experimental |
| Model registry, provenance, artifact index | **Done** |
| Docker packaging, structured logging | **Done** |
| Scene composite + cloud-masked mosaic | **Done** |
| API contracts (Pydantic, Product Brief shape) | **Done** |
| Baseline calibration (signed threshold, closing) | **Done** — 12/12 golden tests |
| Spatial-variance seasonal detection | **Done** |
| Rust control plane (Axum API) | Deferred |
| Review workflow, monitoring, alerts | Deferred |

## Documentation

| Doc | Audience | Description |
|-----|----------|-------------|
| [ARCHITECTURE.md](ARCHITECTURE.md) | Engineers | Four-plane model, stage boundaries, design decisions |
| [ROADMAP.md](ROADMAP.md) | Community | Phased build plan, decision gates, current status |
| [CLAUDE.md](CLAUDE.md) | AI agents | Project context, build commands, gotchas |
| [docs/CONTRIBUTING.md](docs/CONTRIBUTING.md) | Contributors | Development workflow, setup, testing rules |
| [docs/architecture/SYSTEM_DESIGN.md](docs/architecture/SYSTEM_DESIGN.md) | Engineers | Detailed subsystem design |
| [docs/TASK_CONTRACT.md](docs/TASK_CONTRACT.md) | Contributors | Formal definition of the vegetation_disturbance task |
| [docs/mini-sdd/README.md](docs/mini-sdd/README.md) | Contributors | Bounded-change documentation approach |
| [docs/api/gaps_vs_product_brief.md](docs/api/gaps_vs_product_brief.md) | Engineers | API contract gap analysis |

## Configuration

Oberon works out of the box with sensible defaults. Override via environment variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `OBERON_STAC_URL` | `https://earth-search.aws.element84.com/v1` | STAC catalog endpoint |
| `OBERON_STAC_TIMEOUT` | `30` | STAC API connection timeout (seconds) |
| `OBERON_STAC_RETRIES` | `3` | Max retry attempts for STAC failures |
| `OBERON_COG_TIMEOUT` | `60` | GDAL HTTP timeout for COG reads (seconds) |
| `OBERON_COG_RETRIES` | `3` | GDAL HTTP max retries for COG reads |
| `OBERON_LOG_FORMAT` | `console` | Logging format (`console` or `json`) |
| `OBERON_CACHE_DIR` | `~/.cache/oberon` | Disk cache directory |

## Contributing

Contributions welcome. Read [docs/CONTRIBUTING.md](docs/CONTRIBUTING.md) first.
We follow the [Contributor Covenant Code of Conduct](CODE_OF_CONDUCT.md).

All code (human or AI) must pass: TDD, ruff, mypy strict, pytest, provenance checks.

## Status

Pre-MVP. The core pipeline is functional and tested (287 unit tests, 12 golden integration tests). The live 005 benchmark gate was run on 2026-06-22: Clay AI tied the deterministic baseline (`precision_at_k` 0.1266 vs 0.1266, delta +0.0000), so AI is **not** promoted to the default path. Oberon remains deterministic-first with `--use-ai` as an experimental flag.

Baseline calibration (013) brought golden integration tests from 1/12 to 12/12 passing via signed threshold, morphological closing, and cross-season annotation. Spatial-variance seasonal detection (014) adds a coefficient-of-variation check to distinguish uniform seasonal senescence from patchy real disturbance.

## License

Apache 2.0 — see [LICENSE](LICENSE).

## Changelog

See [CHANGELOG.md](CHANGELOG.md) for version history.

## Citation

If you use Oberon in research, see [CITATION.cff](CITATION.cff) for citation information.

---

Oberon is a project by [Farzin Shifat](https://farzinbuilds.com).
