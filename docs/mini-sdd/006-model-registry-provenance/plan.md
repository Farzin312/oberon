# Plan — Model Registry + Artifact Store

**Parent**: [../README.md](../README.md)

---

## 1. Repo facts

| Area | Current state | Source |
|---|---|---|
| Model registry | Does not exist — model info hardcoded in clay_config.py | `src/oberon/ai/clay_config.py` (after 003) |
| Artifact store | EvidenceBundle returns paths; no central artifact registry | `src/oberon/artifacts/` |
| Provenance | Has scene IDs, bands, config, software version. Missing: model version when no AI, artifact URIs | `src/oberon/artifacts/provenance.py` |
| Cache | COG windows fetched fresh every run — no session cache | `src/oberon/pipeline/cog_reader.py` |
| CLI output | Returns text summary; no --json output option | `src/oberon/cli/main.py` |

---

## 2. Execution order

1. **Phase 0 — Model registry** — `src/oberon/config/model_registry.py`
2. **Phase 1 — Artifact store index** — artifact manifest per run
3. **Phase 2 — Provenance enrichment** — add artifact URIs, deterministic model version
4. **Phase 3 — Session cache** — cache COG windows for same (scene, band, AOI) pair
5. **Phase 4 — API contract alignment** — compare EvidenceBundle to POST /v1/change shape, document gaps

---

## 3. Architecture

### 3.1 Model registry

```python
# src/oberon/config/model_registry.py
REGISTERED_MODELS: dict[str, ModelEntry] = {
    "deterministic-v1": ModelEntry(
        version="deterministic-v1",
        type="deterministic",
        stages=["ndvi", "nbr", "ndmi", "pixel_delta"]
    ),
    "clay-v1.5": ModelEntry(
        version="clay-v1.5",
        type="foundation_model",
        adapter="clay_adapter.ClayAdapter",
        required_bands=BANDS_10,
        chip_size=256
    ),
}
```

Each run records `model_versions: list[str]` in provenance (e.g., `["deterministic-v1", "clay-v1.5"]`).

### 3.2 Artifact index

EvidenceBundle already stores paths. Add a run-level artifact index JSON:
```json
{
  "run_id": "oberon-20260622T120000-abcd1234",
  "created_at": "2026-06-22T12:00:00Z",
  "artifacts": {
    "provenance": "output/provenance.json",
    "findings_geojson": "output/findings.geojson",
    "before_image": "output/before.png",
    "after_image": "output/after.png",
    "overlay_image": "output/overlay.png"
  },
  "checksums": {
    "provenance": "sha256:abc...",
    "findings_geojson": "sha256:def..."
  }
}
```

### 3.3 Session cache (COG)

Cache key = `(scene_id, band, row_off, col_off, width, height)`
Storage = `~/.cache/oberon/cog/{scene_id}/{band}_r{row}c{col}.npy`
TTL = None (allow user to `rm -rf ~/.cache/oberon/`)
Skip for small AOIs (< 100KB per window)

### 3.4 POST /v1/change alignment check

Compare EvidenceBundle fields against Product Brief API contract (lines 314-341):
- `geometry` in response → Finding.geometry ✓
- `change_score` → Finding.score ✓ (but called "score")
- `suggested_class` → Not present (no task head)
- `changed_area_m2` → Finding.area_m2 ✓
- `evidence.ndvi_delta` → Finding.ndvi_delta_mean ✓
- `model.encoder` → provenance (needs model_version field added)
- `artifacts.before/after/overlay` → bundle paths ✓
- `status` field → Missing entirely

Document gap: status field ("review_recommended" / "abstained" / "failed") should map to CLI exit behavior.

---

## 4. Exact changes

### 4.1 New files
- `src/oberon/config/model_registry.py`
- `src/oberon/store/artifact_index.py` — build_run_artifact_index()

### 4.2 Modified files
- `src/oberon/artifacts/provenance.py` — add model_versions, artifact URIs, checksums
- `src/oberon/cli/orchestrator.py` — record model_registry entries used in run
- `src/oberon/cli/main.py` — add `--json` output flag for structured results
- `src/oberon/pipeline/cog_reader.py` — add session cache layer
- `src/oberon/pipeline/preparation.py` — add cache key generation

---

## 5. Risk register

| Risk | Mitigation |
|---|---|
| Cache fills disk | TTL-free but document cache location; .gitignore ~/.cache/oberon/ |
| Checksums expensive for large rasters | Only checksum small JSON/GeoJSON artifacts |
| Model registry adds complexity for single model | Registry starts with 2 entries (deterministic, clay); designed for expansion |
| API contract mismatch discovered late | Phase 4 produces explicit gap document; fix deferred to 008 |

---

## 6. End-phase cleanup

- Document cache location and cache-clearing instructions in AGENTS.md
- Update DATA_FLOW.md with artifact index stage
- Commit artifact index schema as `docs/schemas/artifact_index.json`
