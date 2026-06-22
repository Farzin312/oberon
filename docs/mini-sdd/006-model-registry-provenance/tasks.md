# Tasks — Model Registry + Artifact Store

**Parent**: [../README.md](../README.md)

---

## Phase 0 — Model registry
**Status:** [x] DONE

- [x] [BE] `src/oberon/config/model_registry.py` — ModelEntry dataclass + REGISTERED_MODELS dict
- [x] [BE] deterministic-v1 entry (stages: ndvi, nbr, ndmi, pixel_delta)
- [x] [BE] clay-v1.5 entry (adapter, required_bands, chip_size)
- [x] [TEST] `tests/config/test_model_registry.py` — 9 tests: registry entries, lookup, serialization, frozen
- [x] [QA] ruff 0; pytest green

## Phase 1 — Artifact index
**Status:** [x] DONE

- [x] [BE] `src/oberon/store/artifact_index.py` — build_run_artifact_index(), compute_sha256()
- [x] [BE] Includes: run_id, timestamp, artifact paths, checksums (JSON/GeoJSON only), file_sizes
- [x] [BE] Wired into orchestrator after evidence bundle generation
- [x] [TEST] `tests/store/test_artifact_index.py` — 10 tests: checksums, index fields, disk write, relative paths
- [x] [QA] ruff 0; pytest green

## Phase 2 — Provenance enrichment
**Status:** [x] DONE

- [x] [BE] `src/oberon/artifacts/provenance.py` — add model_versions list to manifest
- [x] [BE] `src/oberon/artifacts/__init__.py` — pass model_versions through build_evidence_bundle
- [x] [BE] `src/oberon/cli/orchestrator.py` — record model_registry entries used (deterministic-v1, clay-v1.5 if AI)
- [x] [TEST] `tests/artifacts/test_provenance.py` — 3 new tests: default model_versions, AI run, custom
- [x] [QA] ruff 0; pytest green; mypy 0

## Phase 3 — COG session cache
**Status:** [x] DONE

- [x] [BE] `src/oberon/pipeline/cog_reader.py` — session-level in-memory cache keyed by (scene, bands, AOI)
- [x] [BE] enable_cache() / disable_cache() / clear_cache() / get_cache_size() API
- [x] [BE] `src/oberon/cli/main.py` — add `--cache` flag
- [x] [TEST] `tests/pipeline/test_cog_cache.py` — 8 tests: cache key determinism, enable/disable lifecycle
- [x] [QA] ruff 0; pytest green

## Phase 4 — API contract alignment
**Status:** [x] DONE

- [x] [DOC] `docs/api/gaps_vs_product_brief.md` — 10-row gap analysis vs POST /v1/change shape
- [x] [BE] `src/oberon/cli/main.py` — add `--json` flag for structured CLI output (status, findings, model_versions, artifacts)
- [x] [TEST] `tests/cli/test_analyze.py` — --cache and --json in help output assertion
- [x] [QA] `ruff check src/ tests/ scripts/` — 0 exit
- [x] [QA] `mypy src/` — 0 exit
- [x] [QA] Commit

---

### Progress

All 5 phases complete. 226 tests passing (196 from 004+005 + 9 registry + 10 artifact index + 3 provenance + 8 COG cache).
29 source files, ruff 0, mypy 0.

New packages: src/oberon/config/, src/oberon/store/
Modified: provenance.py (model_versions), orchestrator.py (model tracking + artifact index), main.py (--cache, --json flags), cog_reader.py (session cache)
