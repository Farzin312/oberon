# Tasks — Scene Composite + Cloud-Masked Mosaic

**Parent**: [../README.md](../README.md)

---

## Phase 0 — Composite builder
**Status:** [ ]

- [ ] [TEST] `tests/pipeline/test_preparation.py` — build_composite on 2-scene synthetic input
- [ ] [TEST] `tests/pipeline/test_preparation.py` — median blends correctly, ignores NaN
- [ ] [TEST] `tests/pipeline/test_preparation.py` — valid mask is union of input masks
- [ ] [TEST] `tests/pipeline/test_preparation.py` — rejects scenes with mismatched shapes
- [ ] [BE] `src/oberon/pipeline/preparation.py` — implement build_composite()
- [ ] [QA] ruff 0; pytest green; mypy 0

## Phase 1 — Auto-fallback
**Status:** [ ]

- [ ] [TEST] `tests/cli/test_orchestrator.py` — fallback triggers when valid_fraction < 0.7
- [ ] [TEST] `tests/cli/test_orchestrator.py` — fallback does NOT trigger when single scene sufficient
- [ ] [BE] `src/oberon/cli/orchestrator.py` — add COMPOSITE_THRESHOLD + fallback branch
- [ ] [QA] ruff 0; pytest green

## Phase 2 — CLI flag
**Status:** [ ]

- [ ] [BE] `src/oberon/cli/main.py` — add `--composite` flag (force composite mode)
- [ ] [TEST] `tests/cli/test_analyze.py` — --composite flag exists
- [ ] [QA] ruff 0; pytest green

## Phase 3 — Provenance
**Status:** [ ]

- [ ] [BE] `src/oberon/artifacts/provenance.py` — support source_type: "single" | "composite"
- [ ] [BE] `src/oberon/artifacts/provenance.py` — record all contributing scene IDs for composite
- [ ] [TEST] `tests/artifacts/test_provenance.py` — composite provenance has scene list
- [ ] [QA] ruff 0; pytest green; mypy 0

## Phase 4 — Verify
**Status:** [ ]

- [ ] [QA] `ruff check src/ tests/` — 0 exit
- [ ] [QA] `mypy src/` — 0 exit
- [ ] [QA] `pytest tests/ -v --tb=short` — all pass
- [ ] [QA] Commit

---

### Progress

_None yet. Depends on 001-data-plane-pipeline._
