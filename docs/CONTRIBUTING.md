# Contributing

**Parent**: [README.md](../README.md)

## Collaboration model

Oberon uses Spec-Driven Development (SDD) for complex features and mini-SDDs for bounded changes. See [SPEC_DRIVEN_DEVELOPMENT.md](SPEC_DRIVEN_DEVELOPMENT.md) and [mini-sdd/README.md](mini-sdd/README.md).

**Both AI agents and human contributors follow the same workflow.** CLAUDE.md and AGENTS.md are the AI entry points; this doc is the shared workflow.

## Before making any change

1. Read the relevant mini-SDD or SDD spec for what you're changing.
2. Run `bounds validate --quick` to baseline the subsystem state.
3. Record baseline test count: `pytest tests/ -q --tb=no | tail -1`.

## How to run

```bash
# Prerequisites: Python 3.12+, uv, GDAL system libraries
uv sync

# Optional: enable AI inference
uv sync --extra ai

# Run the CLI
python -m oberon.cli analyze \
  --aoi sample-aoi.geojson \
  --before-start 2024-01-01 --before 2024-03-01 \
  --after-start 2024-07-01 --after 2024-09-01 \
  --task vegetation_disturbance
```

### GDAL installation

Oberon uses rasterio which requires GDAL system libraries. Install per platform:

**macOS (Homebrew):**
```bash
brew install gdal
```

**Ubuntu/Debian:**
```bash
sudo apt install libgdal-dev
```

**Or skip the install — use Docker:**
```bash
docker build -t oberon:cpu .
docker run --rm -v "$PWD:/data" oberon:cpu analyze \
  --aoi /data/sample-aoi.geojson \
  --before-start 2024-01-01 --before 2024-03-01 \
  --after-start 2024-07-01 --after 2024-09-01 -o /data/output
```

## Workflow

1. **Branch**: `git checkout -b feat/<NNN>-<slug>` or `fix/<NNN>-<slug>`
2. **Document**: Create/update mini-SDD in `docs/mini-sdd/<NNN>-<slug>/`
3. **TDD**: Write failing test → verify RED → implement → verify GREEN → refactor
4. **Quality gates**: lint → type check → tests → bounds preflight
5. **Docs sync**: Update affected docs IN THE SAME change (not follow-up)
6. **Commit**: `git commit -m "type(scope): message"`
7. **PR**: Open pull request with summary of changes, test results, docs updated

## Quality gates (never skip)

| Gate | Command |
|------|---------|
| Lint | `ruff check src/ tests/` |
| Type check | `mypy src/` |
| Unit tests | `pytest tests/ -q` |
| Integration tests | `pytest tests/ -q --integration` |
| Bounds validate | `bounds validate --quick` |
| Bounds preflight | `bounds preflight --ci` |

## Commit conventions

```
type(scope): message

- type: feat | fix | refactor | test | docs | chore
- scope: core | cli | pipeline | model-adapter | artifacts | docs
- message: present tense, no period
```

## Code standards (ponytail)

See AGENTS.md for the full Ponytail ruleset. TL;DR:
- YAGNI. No speculative abstractions, no factory for one product, no config for a value that never changes.
- Stdlib first. `pathlib` over `os.path`, `dataclasses` over custom classes.
- One line over fifty. Shortest working diff wins.
- Mark simplifications: `# ponytail: <ceiling>, <upgrade path>`.
- Never simplify away: input validation at trust boundaries, error handling that prevents data loss, TDD.

## Documentation parent/child rules

- Every doc states its **Parent** at the top (linking upward).
- Only index/catalog pages list **Children**.
- When adding a doc, add a link from its parent and state the parent in the new doc.
