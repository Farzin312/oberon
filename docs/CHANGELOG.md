# Changelog

**Parent**: [README.md](../README.md)

All notable changes to Oberon are documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- API contract layer (`src/oberon/api/`) with Pydantic v2 models matching Product Brief section 5
- Serialization layer transforming internal EvidenceBundle to API ChangeResponse shape
- `--request <path>` CLI flag for JSON request file input (ChangeRequestAPI schema)
- `--json` CLI output upgraded to full ChangeResponse shape (status, findings, artifacts)
- ARCHITECTURE.md with four-plane model and pipeline flow diagram
- ROADMAP.md with build sequence, decision gates, and current status
- CLI reference (`docs/api/cli.md`) and usage examples (`docs/api/examples.md`)
- SDK example (`examples/sdk_demo.py`)
- CI workflow (`.github/workflows/ci.yml`) - ruff + mypy + pytest on push/PR
- CHANGELOG.md, CITATION.cff, CODE_OF_CONDUCT.md

### Changed
- README rewritten for public OSS release (product statement, quick start, Docker, CLI examples)
- `--aoi`, `--before`, `--after` no longer individually required (use `--request` as alternative)
- Error messages now reference `--help` and suggest fixes

### Removed
- Private planning PDFs from repo (go-to-market strategy stays internal)

## [0.1.0] - 2026-06-22

### Added
- Core data-plane pipeline: STAC discovery, scene quality assessment, windowed COG reads, SCL cloud/shadow masking, reprojection/resampling/alignment
- Deterministic baselines: NDVI, NBR, NDMI, pixel delta magnitude
- Change detection: thresholding, connected components, finding extraction, deduplication and ranking
- Evidence bundles: true-color before/after PNGs, change overlay, findings GeoJSON, provenance manifest
- Clay v1.5 model adapter with tiled inference (256x256 chips, reflect-pad, stitch)
- `--use-ai` flag for parallel AI feature extraction alongside deterministic baseline
- Cloud-masked median composite when single scene insufficient (up to 3 scenes per period)
- Model registry with artifact index and checksums
- Docker packaging: multi-stage build with uv + GDAL, CPU and GPU profiles
- Structured JSON logging (stdlib, no external deps)
- `--json`, `--cache`, `--composite` CLI flags
- 262 tests (unit + benchmark + comparison + integration golden)
