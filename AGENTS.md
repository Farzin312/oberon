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
python -m oberon.cli analyze --aoi tests/data/sample.geojson --before 2026-01-01 --after 2026-06-01
```

## Version warnings

- Python 3.12+ (match your runtime; no setup.py, use pyproject.toml)
- Rasterio 1.4+ for COG windowed reads
- PySTAC Client 1.0+ for STAC search
- PyTorch 2.6+ (matching Clay requirements)
- Clay v1.5 (specific 10-band 256x256 chip format)
- UV 0.6+ for package management
