# AGENTS.md — AI Assistant Quick Reference

**Parent**: [README.md](README.md)

## Before any change

1. Read [docs/CONTRIBUTING.md](docs/CONTRIBUTING.md) — full contribution workflow
2. Read [docs/mini-sdd/README.md](docs/mini-sdd/README.md) — when to use mini-SDD vs full SDD
3. Read the active mini-SDD in `docs/mini-sdd/<NNN>-<name>/` if one exists
4. Run `bounds describe <subsystem>` for the subsystem you're editing
5. Run `bounds validate --quick` after every change

## Documentation hierarchy

- `README.md` — top-level project index
- `docs/` — domain groupings (architecture, mini-sdd, sdd, planning)
- Every doc states its **Parent** (linking upward) unless it's a catalog/listing page which lists **Children**

## Key quality gates (never skip)

| Gate | Command / check |
|------|----------------|
| TDD | Write failing test first, watch it fail, then implement |
| Lint | `ruff check src/ tests/` |
| Type check | `mypy src/` |
| Tests | `pytest tests/ -q` ≥ baseline count |
| Bounds | `bounds preflight --ci` — no boundary violations, no orphan exports |
| Provenance | Every finding records source scenes, config, model version, artifacts |
| Docs sync | Update mini-SDD tasks.md + docs/ changes IN THE SAME change |

## Ponytail rules (lazy senior dev mode)

1. Does this need to exist? (YAGNI) — skip it, say so in one line.
2. Stdlib does it? Use it.
3. Native Python feature covers it? (`dataclasses` over custom, `pathlib` over `os.path`)
4. Already-installed dep solves it? Use it. No new deps for what a few lines can do.
5. One line? One line.
6. Only then: minimum code that works.

Mark shortcuts: `# ponytail: <name of ceiling>, <upgrade path if throughput matters>`.

## Project gotchas

- **Clay adapter must be versioned** — band ordering, chip size, metadata format specific to v1.5. Future models get a new adapter.
- **No global state** — each pipeline stage is a pure function receiving its inputs and returning typed outputs. Side effects only in the outer shell.
- **Idempotent stages** — running the same stage twice with the same inputs must not corrupt state or create conflicting results. Stable IDs + input/output checksums.
- **COG reads are windowed** — never download an entire scene. Read only the AOI-bounded window.
- **Scene-level cloud % is not local quality** — always compute quality over the AOI polygon, not the whole scene.
- **Pillow required for PNG output** — `render_true_color` and `render_change_overlay` need Pillow. Added as core dependency in pyproject.toml.
- **CLI exits 0 for abstention** — abstention (no suitable scenes, insufficient pixels) is a valid analysis result, not an error. Exit code 0, message prefixed with "Abstained:".
- **Default date windows are 30 days** — both `--before` and `--after` default to a 30-day lookback from the given date. `--before-start` / `--after-start` override the start date explicitly.
- **pixel_delta is secondary** — Euclidean band magnitude is a secondary ranking signal at 0.3 weight. NDVI stays primary. See [docs/TASK_CONTRACT.md](docs/TASK_CONTRACT.md) for the full contract. pixel_delta includes seasonal variation in non-vegetation bands (e.g. SWIR moisture), which is why it's capped.
- **mypy strictness** — Some dict types are `dict[str, Any]` for GeoJSON geometry dicts (mixed-type shapes). Use `cast()` for narrowing, not `# type: ignore`.
- **Docker GDAL deps** — `python:3.12-slim` doesn't include GDAL system libraries. The Dockerfile installs `libgdal36 libgeos-c1t64 libexpat1 libspatialindex-c8` in the runtime stage. If rasterio fails with `.so` errors, check these packages.
- **uv project install** — `uv sync --no-install-project` installs deps only. The console script (`oberon`) requires a second `uv sync --no-editable` after copying source.
- **Structured logging** — Use `extra={"key": value}` with stdlib logger, not kwargs. mypy strict rejects bare kwargs on `logger.info()`. Set `OBERON_LOG_FORMAT=console` for dev.

## Build/test commands

```bash
# Dev install
uv sync

# Run all tests
pytest tests/ -v

# Run specific test
pytest tests/core/test_scene_selection.py::test_ranks_by_local_quality -v

# Lint
ruff check src/ tests/

# Type check
mypy src/

# Bounds checks
bounds validate --quick
bounds preflight --ci

# Run the CLI
python -m oberon.cli analyze --aoi sample-aoi.geojson \
  --before-start 2024-01-01 --before 2024-03-01 \
  --after-start 2024-07-01 --after 2024-09-01
```

## Version warnings

- Python 3.12+ (match your runtime; no setup.py, use pyproject.toml)
- Rasterio 1.4+ for COG windowed reads
- PySTAC Client 1.0+ for STAC search
- PyTorch 2.6+ (matching Clay requirements)
- Clay v1.5 (specific 10-band 256x256 chip format)
- UV 0.6+ for package management
