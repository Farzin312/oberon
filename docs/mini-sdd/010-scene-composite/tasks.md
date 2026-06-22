# Tasks — Scene Composite + Cloud-Masked Mosaic

**Parent**: [../README.md](../README.md)

---

## Phase 0 — Composite builder
**Status:** [x] DONE

- [x] [TEST] `tests/pipeline/test_preparation.py` — build_composite on 2-scene synthetic input
- [x] [TEST] `tests/pipeline/test_preparation.py` — median blends correctly, ignores NaN
- [x] [TEST] `tests/pipeline/test_preparation.py` — valid mask is union of input masks
- [x] [TEST] `tests/pipeline/test_preparation.py` — rejects scenes with mismatched shapes
- [x] [BE] `src/oberon/pipeline/preparation.py` — implement build_composite()
- [x] [QA] ruff 0; pytest green; mypy 0

## Phase 1 — Auto-fallback
**Status:** [x] DONE

- [x] [TEST] `tests/cli/test_orchestrator.py` — fallback triggers when valid_fraction < 0.7
- [x] [TEST] `tests/cli/test_orchestrator.py` — fallback does NOT trigger when single scene sufficient
- [x] [TEST] `tests/cli/test_orchestrator.py` — force_composite always composites
- [x] [BE] `src/oberon/cli/orchestrator.py` — add COMPOSITE_THRESHOLD + fallback branch
- [x] [QA] ruff 0; pytest green

## Phase 2 — CLI flag
**Status:** [x] DONE

- [x] [BE] `src/oberon/cli/main.py` — add `--composite` flag (force composite mode)
- [x] [TEST] `tests/cli/test_analyze.py` — --composite flag exists
- [x] [QA] ruff 0; pytest green

## Phase 3 — Provenance
**Status:** [x] DONE

- [x] [BE] `src/oberon/artifacts/provenance.py` — support source_type: "single" | "composite"
- [x] [BE] `src/oberon/artifacts/provenance.py` — record all contributing scene IDs for composite
- [x] [BE] `src/oberon/artifacts/__init__.py` — thread source_info through build_evidence_bundle
- [x] [BE] `src/oberon/cli/orchestrator.py` — build source_info and pass to evidence bundle
- [x] [TEST] `tests/artifacts/test_provenance.py` — composite provenance has scene list
- [x] [TEST] `tests/artifacts/test_provenance.py` — no source_info omits sources key
- [x] [QA] ruff 0; pytest green; mypy 0

## Phase 4 — Verify
**Status:** [x] DONE

- [x] [QA] `ruff check src/ tests/` — 0 exit
- [x] [QA] `mypy src/` — 0 exit
- [x] [QA] `pytest tests/ -v --tb=short` — 128 pass (was 118, +10 new)
- [x] [QA] Commit

---

### Progress

Mini-SDD 010 complete. 118 -> 128 tests. build_composite adds cloud-masked
median mosaic capability. Auto-fallback at 0.7 valid fraction threshold.
--composite CLI flag forces composite mode. Provenance records all source
scene IDs and composite method.
