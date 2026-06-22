# Tasks — Docker Packaging + Reproducible Deployment

**Parent**: [../README.md](../README.md)

---

## Phase 0 — CPU Docker
**Status:** [ ]

- [ ] [BE] `Dockerfile` — python:3.12-slim + uv + install + entrypoint
- [ ] [BE] `.dockerignore` — exclude git, tests, docs, cache
- [ ] [QA] `docker build -t oberon:cpu .` — clean build
- [ ] [QA] `docker run --rm oberon:cpu oberon analyze --help` — works

## Phase 1 — Docker Compose
**Status:** [ ]

- [ ] [BE] `docker-compose.yml` — CPU profile with volume mounts
- [ ] [QA] `docker compose run oberon analyze --help` — works
- [ ] [QA] `docker compose run oberon analyze --aoi /input/sample.geojson ...` — runs
- [ ] [DOC] Update README.md with Docker quick start

## Phase 2 — GPU variant
**Status:** [ ]

- [ ] [BE] `Dockerfile.gpu` — CUDA base + torch + Clay
- [ ] [BE] `docker-compose.yml` — GPU profile with runtime: nvidia
- [ ] [QA] `docker build -f Dockerfile.gpu -t oberon:gpu .` — clean build (skip if no GPU available)
- [ ] [DOC] GPU deployment section in README.md

## Phase 3 — Observability
**Status:** [ ]

- [ ] [BE] `src/oberon/__init__.py` — add `__version__ = "0.1.0"`
- [ ] [BE] `src/oberon/telemetry/logging.py` — structured logging config (structlog)
- [ ] [BE] `src/oberon/cli/main.py` — replace click.echo with structured logging
- [ ] [BE] `src/oberon/cli/main.py` — add `oberon health` command
- [ ] [TEST] `tests/cli/test_analyze.py` — test health command
- [ ] [TEST] `tests/cli/test_analyze.py` — test JSON log format
- [ ] [TEST] `tests/cli/test_analyze.py` — test version in output
- [ ] [QA] ruff 0; pytest green; mypy 0

## Phase 4 — External reproducibility test
**Status:** [ ]

- [ ] [TEST] Run CLI analysis from Docker on a fresh directory (no local deps)
- [ ] [TEST] Verify golden tests from 004 pass in Docker: `docker compose run oberon pytest tests/integration/ --run-integration`
- [ ] [TEST] On macOS: `docker run` with volume mounting the benchmark dataset
- [ ] [DOC] Verify reproduction steps: 1) docker compose build 2) docker compose run oberon pytest --run-integration

## Phase 5 — Documentation
**Status:** [ ]

- [ ] [DOC] README.md: "Quick start with Docker" section
- [ ] [DOC] README.md: "CPU vs GPU deployment" section
- [ ] [DOC] README.md: "Volume mounts" section (input, output, cache)
- [ ] [DOC] README.md: "Running tests" section with `--run-integration` flag
- [ ] [DOC] Update AGENTS.md with Docker build/run gotchas
- [ ] [QA] `ruff check src/ tests/` — 0 exit
- [ ] [QA] Commit

---

### Progress

_None yet. Depends on 002-baseline-fixes (deterministic pipeline complete)._
