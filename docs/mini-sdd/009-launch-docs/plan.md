# Plan — CLI Docs + SDK Example + Launch

**Parent**: [../README.md](../README.md)

---

## 1. Repo facts

| Area | Current state | Source |
|---|---|---|
| CLI docs | --help output only | `cli/main.py` |
| README.md | Minimal (scaffold-level) | repo root |
| Python SDK example | Not built | N/A |
| Benchmark report | Produced by 005 | `docs/EVALUATION_REPORT.md` |
| API contract gap doc | Produced by 006 | `docs/api/gaps_vs_product_brief.md` |
| Product Brief PDFs | Desktop-only | `/Users/farzin/Desktop/Oberon/` |
| Design partners | Not contacted | N/A |

---

## 2. Execution order

1. **Phase 0 — README overhaul** — from scaffold to product README
2. **Phase 1 — CLI documentation** — `--help` improvements + examples
3. **Phase 2 — SDK example** — Python notebook or script showing full workflow
4. **Phase 3 — Public report** — benchmark + evaluation reports committed to repo
5. **Phase 4 — Design partner prep** — outreach materials from PDFs
6. **Phase 5 — PDF vaulting** — Desktop PDFs moved to vault as reference

---

## 3. Deliverables

### 3.1 README.md structure (strict separation per user's OSS standards)

| File | Audience | Content |
|---|---|---|
| README.md | Users/marketing | What, why, quick start, Docker, CLI example |
| CLAUDE.md | AI agents | Gotchas, build instructions, test commands |
| ARCHITECTURE.md | Engineers | System design, contracts, stage boundaries |
| ROADMAP.md | Community | Phased build plan, current status, decision gates |

### 3.2 CLI examples

```bash
# Basic analysis
oberon analyze --aoi aoi.geojson --before 2026-06-01 --after 2026-06-30 -o output/

# With AI (if enabled)
oberon analyze --aoi aoi.geojson --before 2026-06-01 --after 2026-06-30 --use-ai

# Json output for programmatic use
oberon analyze --aoi aoi.geojson --before 2026-06-01 --after 2026-06-30 --json

# From Docker
docker compose run oberon analyze ...
```

### 3.3 SDK example script

```python
# examples/sdk_demo.py
import oberon

result = oberon.analyze(
    geometry=load_geojson("aoi.geojson"),
    before=("2026-04-01", "2026-05-01"),
    after=("2026-06-01", "2026-07-01"),
    task="vegetation_disturbance",
)
print(f"Findings: {len(result.findings)}")
for f in result.findings:
    print(f"  Score: {f.score:.2f}, Area: {f.area_m2:.0f}m²")
```

### 3.4 Design partner deck outline (from Blueprint §4)

- Osa Conservation (Costa Rica) — benchmark one restoration corridor
- Mast Reforestation — backtest post-wildfire recovery
- Blue Forest — portfolio evidence pilot
- Regional land trusts — repeated parcel review

---

## 4. Exact changes

### 4.1 Docs
- `README.md` — full rewrite (product, quick start, CLI, Docker, benchmarks)
- `ARCHITECTURE.md` — from SYSTEM_DESIGN.md content
- `ROADMAP.md` — from mini-SDD overview
- `docs/api/cli.md` — CLI reference
- `docs/api/examples.md` — usage examples

### 4.2 SDK
- `oberon/__init__.py` — `analyze(...)` convenience function wrapping CLI
- `examples/sdk_demo.py` — full workflow demo

### 4.3 Vault
- Copy PDFs to `docs/planning/` (vaulted reference)

---

## 5. Risk register

| Risk | Mitigation |
|---|---|
| README overpromises before evaluation | Match claims to evaluation results (005); nothing unverified |
| SDK example breaks with package changes | Include in CI (pytest markers) |
| Design partner outreach premature | Phase 4: write materials but don't send until 005 gate passes |
| PDFs lost if not vaulted | Phase 5: committed to repo |

---

## 6. End-phase cleanup

- Remove scaffold boilerplate from README
- Ensure all four OSS docs files exist (README, CLAUDE, ARCHITECTURE, ROADMAP)
- Commit vaulted PDFs
- Final git log review: clean history
