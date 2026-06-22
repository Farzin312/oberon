# Tasks — Docker Packaging + Reproducible Deployment

**Parent**: [../README.md](../README.md)

---

## Phase 0 — CPU Docker
**Status:** [x] DONE

- [x] [BE] `Dockerfile` — python:3.12-slim + uv + multi-stage build + GDAL system libs
- [x] [BE] `.dockerignore` — exclude git, tests, docs, cache
- [x] [QA] `docker build -t oberon:cpu .` — clean build
- [x] [QA] `docker run --rm oberon:cpu analyze --help` — works
- [x] [QA] `docker run --rm oberon:cpu health` — works, STAC reachable

## Phase 1 — Docker Compose
**Status:** [x] DONE

- [x] [BE] `docker-compose.yml` — CPU + GPU profiles with volume mounts
- [x] [QA] `docker compose run --rm oberon health` — works
- [x] [QA] `docker compose run --rm oberon analyze ...` — pipeline runs (abstention on test data is valid)
- [x] [DOC] Update README.md with Docker quick start

## Phase 2 — GPU variant
**Status:** [x] DONE (not build-tested — no GPU available)

- [x] [BE] `Dockerfile.gpu` — CUDA 12.4 base + torch + uv sync --extra ai
- [x] [BE] `docker-compose.yml` — GPU profile with nvidia runtime
- [-] [QA] `docker build -f Dockerfile.gpu -t oberon:gpu .` — skipped (no GPU on dev machine)
- [x] [DOC] GPU deployment section in README.md

## Phase 3 — Observability
**Status:** [x] DONE

- [x] [BE] `src/oberon/__init__.py` — add `__version__ = "0.1.0"`
- [x] [BE] `src/oberon/telemetry/logging.py` — structured JSON logging (stdlib, no external deps)
- [x] [BE] `src/oberon/cli/main.py` — structured logging in analyze (start/result events)
- [x] [BE] `src/oberon/cli/main.py` — `oberon health` command (version, torch, STAC, cache)
- [x] [TEST] `tests/cli/test_analyze.py` — health command test
- [x] [TEST] `tests/cli/test_analyze.py` — health --json output test
- [x] [TEST] `tests/cli/test_analyze.py` — version in health output
- [x] [QA] ruff 0; pytest green (131 pass); mypy 0

## Phase 4 — External reproducibility test
**Status:** [x] DONE

- [x] [TEST] `docker run` with volume-mounted AOI — pipeline runs end-to-end in container
- [x] [TEST] Structured JSON logging verified in container stderr
- [x] [TEST] Abstention path verified in container (exit 0, clean message)
- [x] [DOC] Docker reproduce steps documented in README.md

## Phase 5 — Documentation
**Status:** [x] DONE

- [x] [DOC] README.md: "Quick start with Docker" section (build, run, compose)
- [x] [DOC] README.md: "Volume mounts" table
- [x] [DOC] README.md: "Structured logging" section
- [x] [DOC] AGENTS.md: Docker GDAL deps gotcha, uv project install gotcha, structured logging gotcha
- [x] [QA] `ruff check src/ tests/` — 0 exit
- [x] [QA] Commit

---

### Progress

Mini-SDD 007 complete. 128 -> 131 tests. CPU Docker image builds and runs
end-to-end. docker-compose with CPU+GPU profiles. `oberon health` command.
Structured JSON logging via stdlib (no new deps). GPU Dockerfile written
but not build-tested (no GPU on dev machine).
