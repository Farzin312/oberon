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

Pre-MVP. First milestone: walking vertical slice that accepts one polygon and produces one reviewable vegetation-change result. See [docs/mini-sdd/001-data-plane-pipeline/](docs/mini-sdd/001-data-plane-pipeline/) for current work.

## Quick start

```bash
# Install
uv sync

# Analyze an area of interest
python -m oberon.cli analyze \
  --aoi path/to/polygon.geojson \
  --before 2026-01-01 --after 2026-06-01 \
  --task vegetation_disturbance
```

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
