# Tasks — Model Registry + Artifact Store

**Parent**: [../README.md](../README.md)

---

## Phase 0 — Model registry
**Status:** [ ]

- [ ] [BE] `src/oberon/config/model_registry.py` — ModelEntry dataclass + REGISTERED_MODELS dict
- [ ] [BE] deterministic-v1 entry (stages: ndvi, nbr, ndmi, pixel_delta)
- [ ] [BE] clay-v1.5 entry (if 003 completed)
- [ ] [TEST] `tests/ai/test_model_adapter.py` — test every registered model has an adapter class
- [ ] [QA] ruff 0; pytest green

## Phase 1 — Artifact index
**Status:** [ ]

- [ ] [BE] `src/oberon/store/artifact_index.py` — build_run_artifact_index()
- [ ] [BE] Includes: run_id, timestamp, artifact paths, checksums
- [ ] [BE] Wire into orchestrator after evidence bundle generation
- [ ] [TEST] `tests/artifacts/test_artifact_index.py` — index JSON has required fields
- [ ] [TEST] `tests/artifacts/test_artifact_index.py` — checksums match SHA256 file hashes
- [ ] [QA] ruff 0; pytest green

## Phase 2 — Provenance enrichment
**Status:** [ ]

- [ ] [BE] `src/oberon/artifacts/provenance.py` — add model_versions list to manifest
- [ ] [BE] `src/oberon/artifacts/provenance.py` — add artifact URIs (relative paths)
- [ ] [BE] `src/oberon/artifacts/provenance.py` — add checksums for text artifacts
- [ ] [BE] `src/oberon/cli/orchestrator.py` — pass model_registry entries used
- [ ] [TEST] `tests/artifacts/test_provenance.py` — provenance has model_versions
- [ ] [TEST] `tests/artifacts/test_provenance.py` — provenance has artifact URIs
- [ ] [TEST] `tests/artifacts/test_provenance.py` — deterministic run uses "deterministic-v1"
- [ ] [QA] ruff 0; pytest green; mypy 0

## Phase 3 — COG session cache
**Status:** [ ]

- [ ] [BE] `src/oberon/pipeline/cog_reader.py` — cache key = (scene_id, band, row, col, w, h)
- [ ] [BE] Cache directory: `~/.cache/oberon/cog/{scene_id}/{band}_r{row}c{col}.npy`
- [ ] [BE] Cache behind `--cache` flag (default: off for CLI, on for golden tests)
- [ ] [BE] `src/oberon/cli/main.py` — add `--cache` / `--no-cache` flag
- [ ] [TEST] `tests/pipeline/test_cog_reader.py` — second read with cache returns same array
- [ ] [TEST] `tests/pipeline/test_cog_reader.py` — cache miss falls through to network
- [ ] [QA] ruff 0; pytest green

## Phase 4 — API contract alignment
**Status:** [ ]

- [ ] [DOC] Compare EvidenceBundle vs Product Brief POST /v1/change response shape
- [ ] [DOC] Document each gap: missing status field, renamed fields, absent model field
- [ ] [DOC] Record gap doc in `docs/api/gaps_vs_product_brief.md`
- [ ] [BE] `src/oberon/cli/main.py` — add `--json` flag for structured CLI output
- [ ] [QA] `ruff check src/ tests/` — 0 exit
- [ ] [QA] `mypy src/` — 0 exit
- [ ] [QA] Commit

---

### Progress

_None yet. Depends on 002-baseline-fixes + 003-clay-experiment._
