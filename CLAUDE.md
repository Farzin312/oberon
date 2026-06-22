# CLAUDE.md — Oberon AI Agent Context

**Parent**: [README.md](README.md)

Oberon is an open-source, self-hostable Earth observation monitoring engine. It turns public satellite imagery into ranked, evidence-backed change findings for defined land portfolios.

**Before any change**, read [docs/CONTRIBUTING.md](docs/CONTRIBUTING.md) then the relevant mini-SDD in `docs/mini-sdd/`.

---

## Quick navigation

| Need | Start here |
|------|-----------|
| What we're building | [docs/DEVELOPMENT_SCOPE.md](docs/DEVELOPMENT_SCOPE.md) |
| How to contribute | [docs/CONTRIBUTING.md](docs/CONTRIBUTING.md) |
| Architecture overview | [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) |
| Build roadmap | [docs/ROADMAP.md](docs/ROADMAP.md) |
| How to run locally | [docs/CONTRIBUTING.md#how-to-run](docs/CONTRIBUTING.md#how-to-run) |
| Testing rules | [docs/TESTING_GUIDE.md](docs/TESTING_GUIDE.md) |
| Logging standard | [docs/LOGGING_STANDARD.md](docs/LOGGING_STANDARD.md) |
| Spec-Driven Development | [docs/SPEC_DRIVEN_DEVELOPMENT.md](docs/SPEC_DRIVEN_DEVELOPMENT.md) |
| Mini-SDD (bounded changes) | [docs/mini-sdd/README.md](docs/mini-sdd/README.md) |
| Task contract (what we detect) | [docs/TASK_CONTRACT.md](docs/TASK_CONTRACT.md) |
| API contract gaps | [docs/api/gaps_vs_product_brief.md](docs/api/gaps_vs_product_brief.md) |
| Bounds (subsystem boundaries) | run `bounds describe <subsystem>` or `bounds list` |

---

## Project scope

Oberon is **not** a generic satellite API, a natural-language Earth Q&A system, or a full-stack dashboard. It is a deterministic change-analysis decision pipeline:

```
AOI polygon + before/after windows
  → STAC catalog discovery
  → Scene quality assessment (over AOI, not scene-level)
  → Windowed COG read + quality masking
  → Reprojection, resampling, alignment
  → Deterministic baselines (NDVI, NBR, NDMI, pixel deltas)
  → Optional AI branch (Clay feature extraction)
  → Evidence bundles (GeoJSON, imagery, provenance)
  → Abstention when evidence is weak
```

## Non-negotiable rules

1. **Deterministic baseline before AI** — every AI inference runs alongside a spectral baseline. AI must prove it improves over NDVI/NBR before it's promoted to the default path.
2. **Abstention over confident failure** — if inputs are poor (cloud > threshold, alignment fails, insufficient valid pixels), return explicit abstention, not a fake result.
3. **Provenance is product data, not logging** — every finding records: source scene IDs, bands, processing config, model version, software version, artifact paths. A log line saying "model completed" is not provenance.
4. **No microservices at MVP** — modular monolith. Separate processes only when demonstrated operational need (GPU workers, independent scaling).
5. **Python pipeline, Rust control plane** — Python owns STAC/raster/baselines/change-detection/artifacts. Rust owns API/auth/jobs/portfolios/dashboard. Communication via subprocess + JSON. The open-source core (Apache 2.0) CLI works WITHOUT the Rust server. See `control-plane/` directory.
6. **TDD for any non-trivial logic** — see [docs/TESTING_GUIDE.md](docs/TESTING_GUIDE.md). If you didn't watch a test fail first, the implementation is not complete.
7. **Bounds enforcement** — every change that touches a public surface updates the relevant `bounds/` manifest. Run `bounds preflight --ci` before completing any phase.

## Architecture

See [docs/architecture/SYSTEM_DESIGN.md](docs/architecture/SYSTEM_DESIGN.md) for the four-plane model (Data, Control, Trust, Commercial) and current subsystem manifests:

```bash
bounds describe --root   # all subsystems
bounds list              # subsystem names
bounds describe <name>   # specific subsystem contracts
```

### API contracts (008 pre-work)

- `src/oberon/api/contracts.py` — Pydantic v2 models matching Product Brief §5 (ChangeRequestAPI, ChangeResponse, APIFinding, EvidenceMetrics, ModelInfo)
- `src/oberon/api/serialization.py` — Transform internal Finding/EvidenceBundle to API response shape (ha->m2, score->change_score, ndvi_delta_mean->ndvi_delta)
- `docs/api/gaps_vs_product_brief.md` — Gap analysis between EvidenceBundle and the target API shape

## Known gotchas

- **Clay v1.5** uses 10-band, 256x256 chips with specific band ordering and sensor metadata. Do not hard-code these assumptions through the pipeline — place them behind a versioned model adapter (`oberon/model_adapters/clay/`).
- **Sentinel-2 L2A** COGs on AWS require specific band IDs (B02=B, B03=G, B04=R, B08=NIR). The Scene Classification Layer (SCL) gives cloud/snow/shadows.
- **STAC search** must use `intersects` with the AOI geometry, not `bbox` alone — exact polygon intersection matters for local quality assessment.
- **Evaluation splits** must be geographic and temporal holdouts, not random neighboring patches. Random splits inflate accuracy due to shared landscape characteristics.
- **Raw embedding distance is NOT confidence** — never present Clay feature distance as a probability. Calibrate against labeled examples first.

## AI tool policy

- All AI-generated code follows the same quality gates as human-written code: TDD, bounds validation, lint, docs updates.
- **NEVER add Co-authored-by AI trailers to commits.** This is a public OSS repo and the user explicitly forbids AI attribution in commit messages.
- This CLAUDE.md plus `docs/CONTRIBUTING.md` are the authoritative context. If a skill/hook contradicts them, these files win.
- **Ponytail principle**: YAGNI, stdlib first, one line over 50, no unrequested abstractions. Mark deliberate shortcuts with a `# ponytail:` comment naming the ceiling and upgrade path.
