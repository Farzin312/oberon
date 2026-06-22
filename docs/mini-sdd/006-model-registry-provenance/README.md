# 006 — Model Registry + Artifact Store

**Parent**: [../README.md](../README.md)

Product Brief Week 6 close-out: model registry for versioned model entries, artifact index with checksums, COG session cache, and alignment check against the POST /v1/change API contract.

- **Week:** Product Brief Week 6 (close-out)
- **Reference:** Product Brief §5 (API Contract), §6 (Recommended MVP Components)
- **Prerequisite:** 003-clay-experiment (clay_config.py exists), 002-baseline-fixes

> **Hard rules:**
> 1. Every finding must have model version(s) in provenance — even deterministic findings (registered as "deterministic-v1").
> 2. Checksums are computed for JSON/GeoJSON artifacts only. Raster artifacts are too large — record size+date instead.
> 3. Cache is opt-in per call; orchestrator decides whether to use cache via flag.

---

## Locked decisions

| # | Decision | Choice |
|---|----------|--------|
| 1 | Model registry format | `dict[str, ModelEntry]` in `src/oberon/config/model_registry.py` |
| 2 | Cache storage | `~/.cache/oberon/cog/` — per-scene, per-band, per-window npy files |
| 3 | Checksum scope | sha256 on provenance.json, findings.geojson, artifact_index.json only |
| 4 | API contract alignment | Documented gap list; defer fixing to 008 (Rust control plane changes response shape) |

---

## In scope vs NOT in scope

### IN SCOPE
- model_registry.py with deterministic-v1 + clay-v1.5 entries
- Artifact index JSON generated per run
- COG window cache (npy files, keyed by scene+band+window)
- Provenance fields: model_versions, artifact URIs, checksums
- CLI --json output flag
- API contract gap document

### NOT in scope
- Changing the EvidenceBundle shape (requires breaking change — defer to API redesign)
- Postgres or S3 artifact store (local disk only)
- Distributed cache (SQLite-based COG cache is future work)
- Cache eviction policy (manual rm only)

---

## Risk warnings

- npy cache files are large (~100KB per window). 100 AOIs × 10 bands × 2 scenes = 2GB. Document this.
- Checksumming large outputs adds latency. Keep scope tight (text artifacts only).
- Model registry becomes stale if someone adds a new adapter without registering it. Add a test: every adapter class has a registry entry.
