# 007 — Docker Packaging + Reproducible Deployment

**Parent**: [../README.md](../README.md)

Product Brief Week 8: Docker Compose packaging for CPU and GPU profiles, structured logging, health check, and an external reproducibility test. The Week 8 gate: "Can someone who is not you deploy the service and reproduce the benchmark?"

- **Week:** Product Brief Week 8
- **Reference:** Product Brief §10 (Deployment Profiles), Roadmap PDF Phase 6 (lines 614-639)
- **Prerequisite:** 002-baseline-fixes (complete deterministic pipeline)

> **Hard rules:**
> 1. The CPU Dockerfile must be buildable with zero external dependencies (no API keys, no model download) — the pipeline abstains gracefully when STAC is unreachable.
> 2. GPU variant is a separate Dockerfile. CPU build must not include torch.
> 3. `oberon health` must work before `oberon analyze` — verifies the container is correctly configured.
> 4. External reproducibility: someone who is NOT you must be able to run the golden tests from 004.

---

## Locked decisions

| # | Decision | Choice |
|---|----------|--------|
| 1 | Base image | `python:3.12-slim` (official, small) |
| 2 | Package install | `uv sync --no-dev` (CPU) / `uv sync --extra ai` (GPU) |
| 3 | Logging | `structlog` with JSON output — switchable to console format |
| 4 | Health endpoint | `oberon health` CLI command, not HTTP endpoint |
| 5 | External test | Tested on fresh macOS + Linux environment |

---

## In scope vs NOT in scope

### IN SCOPE
- Dockerfile (CPU) + Dockerfile.gpu
- docker-compose.yml with both profiles
- `oberon health` CLI command
- Structured JSON logging
- Verification on clean environment
- Deployment docs in README.md

### NOT in scope
- Rust control plane (008)
- Orchestrated multi-container setup (Postgres, queue, separate workers)
- Kubernetes manifests (future)
- Signed container images (future)
- Air-gapped deployment (post-pilot)

---

## Risk warnings

- uv is required in the Docker image. Pin uv version in Dockerfile for reproducibility.
- GPU Docker build with CUDA requires nvidia-docker runtime. Document as a hard requirement for GPU profile.
- External user with different hardware may have different STAC access speeds. Set realistic expectations.
