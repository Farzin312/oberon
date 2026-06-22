# 010 — Scene Composite + Cloud-Masked Mosaic

**Parent**: [../README.md](../README.md)

Roadmap PDF correction #2 (lines 50-54): "A robust monitoring system should be able to create a small cloud-masked composite or select multiple observations when no single acquisition is sufficiently clean." Currently the pipeline picks ONE scene per period. This mini-SDD adds composite capability.

- **Reference:** Roadmap PDF correction #2, Product Brief §6 data handling rules
- **Prerequisite:** 001-data-plane-pipeline (scene_quality, cog_reader, preparation)

> **Hard rules:**
> 1. Single-scene selection stays the default. Composite is opt-in via `--composite` flag or automatic fallback when no single scene meets quality threshold.
> 2. Composite merges 2-3 acquisitions per period, never more. Computing median across dozens of scenes is expensive and unnecessary for monitoring.
> 3. Composite uses median pixel blending within the valid-pixel mask. Cloud/shadow pixels are excluded, not averaged in.
> 4. Provenance must record ALL source scenes used in the composite, not just one.

---

## Locked decisions

| # | Decision | Choice |
|---|----------|--------|
| 1 | Composite trigger | Automatic when best single-scene valid-pixel fraction < threshold (default: 0.7) |
| 2 | Max scenes per composite | 3 |
| 3 | Blending method | Per-band median within valid-pixel union |
| 4 | SCL mask priority | If any scene marks pixel as cloud/shadow, pixel is excluded from that scene's contribution |

---

## In scope vs NOT in scope

### IN SCOPE
- `build_composite(scenes, aoi, bands) -> PreparedPair-like` function
- Automatic fallback when single-scene quality insufficient
- `--composite` CLI flag for forced composite mode
- Provenance records all contributing scene IDs

### NOT in scope
- Time-series analysis (BAP, temporal gap fill)
- Commercial imagery composites (Sentinel-2 only)
- Multi-tile mosaicking across UTM zone boundaries
