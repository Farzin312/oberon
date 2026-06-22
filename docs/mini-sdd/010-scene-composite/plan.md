# Plan — Scene Composite + Cloud-Masked Mosaic

**Parent**: [../README.md](./README.md)

---

## 1. Repo facts

| Area | Current state | Source |
|---|---|---|
| Scene selection | Picks best single scene per period by valid-pixel fraction | `scene_quality.py`, `orchestrator.py` |
| COG reader | Reads windowed bands from a single scene | `cog_reader.py` |
| Preparation | Aligns before/after single scenes | `preparation.py` |
| Provenance | Records single scene ID per period | `provenance.py` |

---

## 2. Execution order

1. **Phase 0 — Composite builder** — `build_composite()` in preparation.py
2. **Phase 1 — Auto-fallback logic** — orchestrator triggers composite when single scene insufficient
3. **Phase 2 — CLI flag** — `--composite` flag for forced composite
4. **Phase 3 — Provenance** — record all contributing scene IDs
5. **Phase 4 — Verify**

---

## 3. Architecture

### 3.1 Composite algorithm

```
1. Select top-N candidate scenes from ranked list (N <= 3)
2. For each scene: read COG windows, apply SCL mask
3. Stack all valid pixels per band: shape (N_scenes, H, W)
4. Per-band median along scene axis, ignoring NaN
5. Union of valid masks across all scenes = composite valid mask
6. Result: (H, W) per band + composite valid_fraction
```

### 3.2 Integration point

```python
# orchestrator.py
if composite_mode or best_scene.valid_fraction < COMPOSITE_THRESHOLD:
    scenes = ranked[:3]
    prepared = build_composite(scenes, aoi, bands)
else:
    prepared = align_to_common_grid(read_scene(best_scene), read_scene(best_scene_after))
```

### 3.3 Provenance

```json
{
  "before_source_type": "composite",
  "before_source_scenes": ["S2A_...", "S2B_...", "S2A_..."],
  "before_composite_method": "median",
  "before_composite_valid_fraction": 0.92
}
```

---

## 4. Exact changes

### 4.1 preparation.py
- Add `build_composite(scenes: list[CandidateScene], aoi_bounds, bands) -> PreparedPair`
- Per-band median blending with NaN masking

### 4.2 orchestrator.py
- Add `COMPOSITE_THRESHOLD = 0.7` constant
- Branch: if best_scene.valid_fraction < threshold, trigger composite
- Or if `--composite` flag set, always composite

### 4.3 cli/main.py
- Add `--composite` flag

### 4.4 artifacts/provenance.py
- Support multi-scene source recording

---

## 5. Risk register

| Risk | Mitigation |
|---|---|
| Reading 3 scenes triples COG fetch time | Acceptable — document ~3x latency in AGENTS.md |
| Median blending across scenes with different sun angles introduces artifacts | Acceptable for monitoring (not precision measurement); document limitation |
| Scenes from different UTM zones | Guard: reject scenes with mismatched CRS before compositing |
