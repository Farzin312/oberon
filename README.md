# Oberon

**Open, self-hostable Earth observation monitoring engine.**

Oberon turns public satellite observations into ranked, evidence-backed change findings for defined land portfolios. Users supply an area of interest and time windows; Oberon returns ranked change polygons, spectral evidence, before/after imagery, and full provenance.

## What it does

```
AOI (GeoJSON polygon) + before/after date windows
  → STAC catalog search for Sentinel-2 L2A
  → Local quality assessment over the AOI
  → Windowed COG read + cloud/shadow masking
  → Reprojection, resampling, alignment
  → Deterministic baselines (NDVI, NBR, NDMI, pixel deltas)
  → Optional AI triage (Clay foundation model)
  → Ranked GeoJSON findings + evidence bundles
  → Explicit abstention when inputs are unreliable
```

## Status

Pre-MVP. Core pipeline (001), baseline fixes + task contract (002), and scene composite (010) are complete. 131 tests pass. See [docs/mini-sdd/README.md](docs/mini-sdd/README.md) for the build roadmap.

## Quick start

### Local (uv)

```bash
# Install
uv sync

# Analyze an area of interest
oberon analyze \
  --aoi path/to/polygon.geojson \
  --before 2026-01-01 --after 2026-06-01 \
  --task vegetation_disturbance

# Check system health
oberon health

# Force cloud-masked composite (merge up to 3 scenes per period)
oberon analyze --aoi path/to/polygon.geojson \
  --before 2026-01-01 --after 2026-06-01 --composite
```

### Docker (CPU)

```bash
# Build
docker build -t oberon:cpu .

# Check health
docker run --rm oberon:cpu health

# Run analysis with mounted input/output
docker run --rm \
  -v "$PWD/input:/input:ro" \
  -v "$PWD/output:/output" \
  oberon:cpu analyze \
    --aoi /input/polygon.geojson \
    --before 2026-01-01 --after 2026-06-01 \
    -o /output
```

### Docker Compose

```bash
# CPU profile (default)
docker compose run --rm oberon analyze \
  --aoi /input/polygon.geojson \
  --before 2026-01-01 --after 2026-06-01 \
  -o /output

# GPU profile (requires nvidia-docker runtime)
docker compose --profile gpu run --rm oberon-gpu health
```

### Volume mounts

| Mount | Purpose |
|-------|---------|
| `./input` | GeoJSON AOI files (read-only) |
| `./output` | Analysis artifacts (PNG, GeoJSON, provenance) |
| `./cache` | STAC response cache (speeds repeated runs) |

### Structured logging

Oberon emits structured JSON logs to stderr by default. Set `OBERON_LOG_FORMAT=console` for human-readable output during development.

## Documentation

| Doc | Audience |
|-----|----------|
| [docs/DEVELOPMENT_SCOPE.md](docs/DEVELOPMENT_SCOPE.md) | What we're building and why |
| [docs/CONTRIBUTING.md](docs/CONTRIBUTING.md) | Development workflow |
| [docs/architecture/SYSTEM_DESIGN.md](docs/architecture/SYSTEM_DESIGN.md) | Architecture overview |
| [docs/SPEC_DRIVEN_DEVELOPMENT.md](docs/SPEC_DRIVEN_DEVELOPMENT.md) | Spec-Driven Development |
| [docs/mini-sdd/README.md](docs/mini-sdd/README.md) | Bounded-change docs approach |
| [CLAUDE.md](CLAUDE.md) | AI agent context |
| [AGENTS.md](AGENTS.md) | Agent quick reference |

## License

Apache 2.0 — see [LICENSE](LICENSE).

Oberon is a project by Farzin Shifat.
