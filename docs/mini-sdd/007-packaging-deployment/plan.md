# Plan — Docker Packaging + Reproducible Deployment

**Parent**: [../README.md](../README.md)

---

## 1. Repo facts

| Area | Current state | Source |
|---|---|---|
| Dockerfile | Does not exist | N/A |
| docker-compose.yml | Does not exist | N/A |
| uv.lock | Committed (pins all deps) | repo root |
| pyproject.toml | Has CPU deps; `[ai]` extra for torch | repo root |
| CLI entry | `oberon analyze --help` works | `pyproject.toml` |
| Observability | Stdout logging only | `cli/*.py` |
| CPU/GPU split | Not separate profiles | N/A |

---

## 2. Execution order

1. **Phase 0 — Dockerfile** — CPU-only first
2. **Phase 1 — Docker Compose** — single service, volume mounts
3. **Phase 2 — GPU profile** — torch + Clay variant
4. **Phase 3 — Observability** — structured logging, health check
5. **Phase 4 — External reproducibility test** — verify on clean machine
6. **Phase 5 — Document** — deployment guide, requirements

---

## 3. Architecture

### 3.1 Two Dockerfiles

- `Dockerfile` — CPU runtime (lightweight, ~500MB)
- `Dockerfile.gpu` — GPU runtime with torch + CUDA runtime (~3GB)

Both based on `python:3.12-slim`. Install via `uv sync --no-dev` (CPU) or `uv sync --extra ai` (GPU).

### 3.2 docker-compose.yml

```yaml
version: "3.9"
services:
  oberon:
    build: .
    command: ["oberon", "analyze", "--help"]
    volumes:
      - ./output:/output
      - ./input:/input
      - ./cache:/root/.cache/oberon
    environment:
      - OBERON_CACHE_DIR=/root/.cache/oberon
```

GPU variant via profiles:
```yaml
profiles:
  - cpu
  - gpu
```

### 3.3 Observability

Add structured JSON logging (replace `click.echo` with `structlog` or Python `logging` with JSON formatter):
- `oberon.analyze.start` — AOI, dates, task
- `oberon.analyze.stage.{name}` — stage start + duration
- `oberon.analyze.result` — outcome, finding count, duration

```python
import logging, structlog
logger = structlog.get_logger()
logger.info("analyze.start", aoi_bbox=bbox, before=before, after=after)
```

### 3.4 Health check

```python
# oberon health -- returns JSON with version, torch available, cache status
{
  "status": "healthy",
  "version": "0.1.0",
  "stac_reachable": true,
  "torch_available": false,
  "cache_size_mb": 123
}
```

---

## 4. Exact changes

### 4.1 Docker infrastructure
- `Dockerfile` — CPU build
- `Dockerfile.gpu` — GPU build (includes torch + CUDA)
- `.dockerignore` — git, tests, docs, cache
- `docker-compose.yml` — both profiles
- `scripts/docker_build.sh` — convenience script

### 4.2 Source changes
- `src/oberon/cli/main.py` — add `oberon health` command
- `src/oberon/cli/__init__.py` — no version yet; read from `__version__` or pyproject.toml
- `src/oberon/__init__.py` — add `__version__ = "0.1.0"`
- `src/oberon/telemetry/logging.py` (NEW) — structured logging config
- `pyproject.toml` — add `[project.version]` or update existing version

---

## 5. Risk register

| Risk | Mitigation |
|---|---|
| Docker image too large (GPU) | Multi-stage build; separate Dockerfile.gpu with smaller base |
| Permission issues with volume mounts | Document UID/GID handling in docker-compose.yml |
| uv not available in slim image | Install uv in Dockerfile; or pre-install Python deps via pip |
| Health check reaches STAC API | Non-blocking; timeout after 5s |
| External user cannot reproduce | Phase 4: test on fresh VM or Codespace |

---

## 6. End-phase cleanup

- Update README.md with Docker instructions
- Add "Quick start" section: `docker compose run oberon analyze ...`
- Update binding mounts doc
- Push and test from a fresh clone
