# Plan — Data Plane Pipeline (Walking Vertical Slice)

**Parent**: [../README.md](../README.md)

Companion to [README.md](./README.md) (decisions + scope) and [tasks.md](./tasks.md) (checklist).

---

## 1. Repo facts (verified as of Phase 1 complete)

| Area | Current state | Source |
|------|--------------|--------|
| Python env | `uv sync --dev` installed; `pyproject.toml` with click, numpy, rasterio, shapely, scipy, pydantic, pystac-client | `pyproject.toml`, `uv.lock` |
| Package layout | `src/oberon/` with subpackages: core/ (domain, geometry, baselines, change_detection), pipeline/ (stac_discovery, scene_quality, cog_reader stub, preparation stub), cli/, artifacts/ | `find src/oberon -type f` |
| bounds | 4 subsystems (core, pipeline, cli, artifacts), 17 files owned, validate clean | `.bounds/root.yaml` |
| STAC catalog | Earth Search STAC at `https://earth-search.aws.element84.com/v1` | EO-federation docs |
| Sentinel-2 COGs | `https://sentinel-cogs.s3.us-west-2.amazonaws.com/sentinel-s2-l2a-cogs/` | AWS Registry of Open Data |
| Tests | 41 passing (geometry 15, stac_discovery 16, scene_quality 10) | `pytest tests/ -q` |
| Lint | `ruff check src/ tests/` → 0 exit | terminal output |
| Domain models | All data contracts defined in `core/__init__.py` as dataclasses | core/__init__.py |
| Geometry helpers | validate, bbox, planar area — complete | core/geometry.py |
| STAC discovery | search_catalog (sync), rank_by_scene_quality with period split — complete | pipeline/stac_discovery.py |
| Scene quality | compute_local_valid_fraction from SCL (pure NumPy) — complete; assess_scene bridge stub for Phase 2 (COG-dependent) | pipeline/scene_quality.py |
| Baselines (core) | NDVI, NBR, NDMI, pixel_delta, abstention — implemented, not yet wired to pipeline | core/baselines.py |
| Change detection | threshold, connected_components, finding extraction — implemented, not yet wired | core/change_detection.py |
| COG reader | Stub raising NotImplementedError | pipeline/cog_reader.py |
| Preparation | Stub raising NotImplementedError | pipeline/preparation.py |
| Evidence images | Stub raising NotImplementedError | artifacts/images.py |
| GeoJSON output | Stub raising NotImplementedError | artifacts/geojson.py |
| Provenance writer | Partial (write_provenance_manifest from dict) | artifacts/provenance.py |
| CLI | Stub click group, --help works | cli/main.py |
| Orchestrator | Stub | cli/orchestrator.py |

---

## 2. Execution order

```
Phase 1 [DONE]: STAC Discovery + Scene Quality
Phase 2 [NEXT]: COG Reading + SCL Masking + Image Preparation (<-- YOU ARE HERE)
Phase 3: Baseline Analytics + Change Detection (complete the existing stubs)
Phase 4: Evidence Bundles + Provenance (images, GeoJSON, manifest)
Phase 5: CLI Wiring + Pipeline Orchestration
Phase 6: Verify + QA (full suite, type check, bounds preflight)
Phase 7: Cleanup + Documentation (DRY sweep, docs sync, git squash)
```

---

## 3. Phase 2 — COG Reading + Preparation (complete design)

### 3.2.1 Purpose

Read only the required Sentinel-2 bands over the AOI bounding box from cloud-optimized GeoTIFFs. Apply SCL-based quality masks. Reproject, resample, and crop both before/after observations to a shared grid so they are pixel-comparable downstream.

### 3.2.2 Stage contract

**Input**: `SelectedScene` (from Phase 1) + `ChangeRequest`  
**Output**: `RasterWindow` per scene, then `PreparedPair` (aligned before + after + mask)  
**Abstention triggers** (any of these → no result):

- COG URL returns 404/403 → skip scene, try next-best candidate
- Fewer than 6 of the 11 standard bands available → abstain (insufficient spectral coverage)
- SCL band missing → degrade to scene-cloud proxy with warning (abstain only if cloud_pct > 30%)
- AOI window dimensions are zero (degenerate polygon edge case) → abstain
- Before or after window has no SelectedScene → abstain ("no suitable observation")
- All pixels masked after SCL → abstain ("AOI fully obstructed in selected scenes")

### 3.2.3 COG reading rules (from PDF roadmap)

1. **Windowed reads only** — use Rasterio window= parameter with the AOI bounding box transformed to the COG's native CRS. Never download a full scene. (Confirmed in PDF §1: "Windowed raster reads are the correct access pattern.")
2. **Buffer** — add 1 pixel buffer to the window to avoid edge effects during resampling.
3. **Band set** — read 10 Sentinel-2 L2A bands (B02, B03, B04, B05, B06, B07, B08, B8A, B11, B12). The 11th band (B01) is coastal aerosol at 60m — skip for vegetation monitoring, read only if task requires it.
4. **COG URL pattern**: `s3://sentinel-cogs/sentinel-s2-l2a-cogs/<tile>/<date>/<granule>/<band>.tif`
5. **Nodata** — Sentinel-2 L2A COGs use 0 for nodata. Override with `nodata=0` in Rasterio read, then mask nodata pixels alongside SCL.
6. **Data type** — L2A bands are uint16 (0-10000). Keep uint16 through pipeline; convert to float32 for index calculations only.

### 3.2.4 SCL masking rules

| SCL value | Class | Action |
|-----------|-------|--------|
| 0 | No data | mask |
| 1 | Saturated/Defective | mask |
| 2 | Dark area pixels | keep |
| 3 | Cloud shadow | mask |
| 4 | Vegetation | keep |
| 5 | Bare soils | keep |
| 6 | Water | keep |
| 7 | Cloud (low prob.) | keep (but flag; treat as warning) |
| 8 | Cloud (medium prob.) | mask |
| 9 | Cloud (high prob.) | mask |
| 10 | Cirrus | mask |
| 11 | Snow/Ice | mask |

**Composite mask construction**: `valid = ~np.isin(scl, CLOUD_BITS) & (band_data != 0)`

### 3.2.5 Preparation (reproject, resample, crop)

**Target CRS**: UTM zone of the AOI centroid. Use `rasterio.crs.CRS.from_epsg(utm_epsg)` where `utm_epsg = 32600 + zone` for N hemisphere, `32700 + zone` for S hemisphere.  
**Target resolution**: 10m (native 10m bands stay native; 20m bands are bilinearly upsampled).  
**Target bounds**: Intersection of both windows' geographic extents (the area both observations cover).  
**Resampling**: Bilinear (default). Nearest-neighbor for SCL band.

**Edge cases**:
- Before and after observations from different UTM zones (e.g., AOI spans a zone boundary) → reproject both to the zone of the AOI centroid. Both are recomputed; no "dominant" zone.
- One observation has significantly different native CRS → Rasterio handles CRS-aware reprojection transparently.
- After reprojection, the arrays have different shapes → crop to the minimum common shape.
- Any resampled dimension is < 10 pixels → abstain ("AOI too small for meaningful analysis at 10m resolution").

### 3.2.6 Output data contract

```python
@dataclass
class PreparedPair:
    before: dict[str, np.ndarray]   # keys: "B02".."B12", each (H, W) float32
    after: dict[str, np.ndarray]    # same keys, same shape
    mask: np.ndarray               # (H, W) bool, True = valid in BOTH
    crs: str                       # EPSG:XXXXX
    transform: tuple[float, ...]   # affine transform (a, b, c, d, e, f)
    bounds: tuple[float, float, float, float]  # (w, s, e, n)

    @property
    def valid_fraction(self) -> float:
        return float(self.mask.sum()) / self.mask.size

    @property
    def is_usable(self) -> bool:
        """At least 30% of the AOI must be valid in both observations."""
        return self.valid_fraction >= 0.30
```

### 3.2.7 File changes

| File | Change | Test file |
|------|--------|-----------|
| `src/oberon/pipeline/cog_reader.py` | Implement: `read_window(scene, aoi_geom, bands, buffer=1) -> RasterWindow` | `tests/pipeline/test_cog_reader.py` |
| `src/oberon/pipeline/preparation.py` | Implement: `build_valid_mask(window) -> tuple[mask, reason]`, `align_to_common_grid(before, after, target_crs, target_resolution=10) -> PreparedPair` | `tests/pipeline/test_preparation.py` |
| `src/oberon/pipeline/scene_quality.py` | Upgrade `assess_scene` from scene-level proxy to real SCL read via cog_reader | — |

### 3.2.8 Edge cases to test

- COG URL returns 404 → `read_window` raises `FileNotFoundError` with scene ID
- SCL band missing from assets → mask falls back to nodata-only (no SCL)
- AOI exactly 10x10 pixels at 10m resolution → minimum viable window
- Before/after from different UTM zones → both reprojected, shapes match
- All-pixel-masked after SCL → `is_usable` is False, callers abstain
- Empty dict for bands (no bands requested) → `read_window` raises `ValueError`

---

## 4. Phase 3 — Baseline Analytics + Change Detection (complete design)

### 4.1 Purpose

Compute deterministic spectral indices from the prepared before/after arrays. Apply difference thresholds, run connected-component extraction, score findings by magnitude and area, and rank them.

> Confirmed in PDF roadmap §Phase 3: "NDVI difference, NBR difference when burn or disturbance sensitivity is relevant, NDMI or another moisture-sensitive index, per-band differences, valid-pixel fraction, changed-pixel area, simple thresholding, connected-region or polygon extraction, ranking by changed area and change magnitude."

### 4.2 Stage contract

**Input**: `PreparedPair` (from Phase 2)  
**Output**: `list[Finding]` (ranked by score descending, may be empty)  
**Abstention triggers**:

- `PreparedPair.is_usable` is False → return empty list with abstention flag
- `BaselineResult.abstain` is True → return empty list with abstention reason

### 4.3 Index computation rules

| Index | Formula | Bands | Sensitivity |
|-------|---------|-------|-------------|
| NDVI | (NIR - R) / (NIR + R) | B08, B04 | Vegetation greenness |
| NBR | (NIR - SWIR2) / (NIR + SWIR2) | B08, B12 | Burn scars, disturbance |
| NDMI | (NIR - SWIR1) / (NIR + SWIR1) | B08, B11 | Moisture stress |

**Always compute NDVI** as the primary change signal. Compute NBR and NDMI if the required SWIR bands exist.

### 4.4 Change detection parameters

| Parameter | Default | When to change |
|-----------|---------|---------------|
| NDVI diff threshold | 0.15 | Lower for subtle degradation, higher for only-clearcuts |
| Min change area | 0.5 ha (50 pixels at 10m) | Set by task; smaller = more noise |
| Max findings | 20 | Bound output size; top 20 by score |
| Score formula | `score = min(abs(ndvi_delta_mean) / 0.5, 1.0) * sqrt(area_ha / max_area)` | Ponytail linear; calibrate against labeled dataset |

### 4.5 Finding deduplication and ranking

1. Run `threshold_change_map` on NDVI diff → binary mask
2. Run `ndimage.label` on binary mask → connected components
3. Filter components below `min_pixels`
4. For each surviving component: compute mean NDVI delta, area in ha, score
5. Sort by score descending, take top `max_findings`
6. Convert component matrices to GeoJSON Polygon geometry (pixel coords → CRS transform)
7. Return list of `Finding` objects

### 4.6 Abstention rules (detailed)

| Condition | Action | Abstention message |
|-----------|--------|-------------------|
| Valid fraction < 30% | Skip baseline entirely | "Insufficient valid pixels: N%" |
| No bands for any index | Skip | "No spectral bands available" |
| Change mask has 0 pixels | Return empty list (valid) | N/A — valid result |
| Total changed area < min_change_area | Return empty list | N/A — changes below reporting threshold |
| All scores are 0.0 | Return empty list | "No significant change detected" |

### 4.7 File changes

| File | Change | Test file |
|------|--------|-----------|
| `src/oberon/core/baselines.py` | Complete: wire abstention to `PreparedPair.is_usable`; add `compute_all(pair) -> BaselineResult` | `tests/core/test_baselines.py` |
| `src/oberon/core/change_detection.py` | Complete: wire `extract_findings` to CRS-transform geometry; add `deduplicate_and_rank(findings, max=20) -> list[Finding]`; replace bbox-polygon with `shapely.convex_hull` | `tests/core/test_change_detection.py` |

### 4.8 Edge cases to test

- NDVI of zero (all-bare-soil) → diff range is valid
- NIR band saturated → division guard fires (epsilon)
- Mask is all-False → `BaselineResult.abstain` is True
- Change mask has exactly 49 pixels (below 50-pixel threshold) → filtered
- All scores 0.0 → empty result (not an error)
- Exactly `max_findings` components found → no truncation
- One very large component + many small → ranking keeps large first
- Single-pixel spurious changes (isolated 1-pixel) → filtered by minimum area

---

## 5. Phase 4 — Evidence Bundles + Provenance (complete design)

### 5.1 Purpose

Package the analysis results into human-reviewable artifacts: true-color before/after PNGs, a change overlay, GeoJSON findings, and a provenance manifest that answers every question from the PDF roadmap ("Which source scenes were used? Which bands? What preprocessing version? Which thresholds?").

### 5.2 Stage contract

**Input**: `list[Finding]` (from Phase 3) + `PreparedPair` (from Phase 2) + `ChangeRequest` + `SelectedScene[]` (from Phase 1)  
**Output**: `EvidenceBundle` (paths to all artifacts on disk)  
**Abstention**: If `findings` is empty and no abstention was triggered, write an empty GeoJSON + provenance showing 0 findings. If abstention was triggered, write only the provenance manifest with `abstention` populated.

### 5.3 Artifact specification

**True-color PNG**: B04 (R), B03 (G), B02 (B) stacked, uint16 → 8-bit with 2%-98% linear percent clip. 8-bit PNG, no compression (fast). Written for both before and after.

**Change overlay PNG**: Before-image true-color base, with finding polygons rendered as semi-transparent red overlay (RGBA: 255, 0, 0, 100). Alpha-composited onto the base image.

**GeoJSON**: `FeatureCollection` where each `Feature` has:
- `geometry`: Polygon in WGS84 (EPSG:4326) — reprojected from the output CRS
- `properties`: `id`, `score`, `area_ha`, `ndvi_delta_mean`, `nbr_delta_mean` (or `null`), `valid_pixels`

**Provenance manifest** (JSON, per PDF §Provenance):

```json
{
  "oberon_version": "0.1.0",
  "change_request": {
    "aoi_bbox": [-84.2, 9.8, -83.7, 10.3],
    "before": {"from": "2026-01-01", "to": "2026-01-31"},
    "after": {"from": "2026-06-01", "to": "2026-06-30"},
    "task": "vegetation_disturbance",
    "thresholds": {"ndvi_delta": 0.15, "min_area_ha": 0.5}
  },
  "scenes": {
    "before": {"item_id": "...", "datetime": "2026-01-15T18:30:00Z",
               "cog_url": "...", "cloud_pct": 5.0, "local_valid_fraction": 0.95},
    "after": {"item_id": "...", "datetime": "2026-06-15T18:30:00Z",
              "cog_url": "...", "cloud_pct": 8.0, "local_valid_fraction": 0.91}
  },
  "processing": {
    "bands_used": ["B02","B03","B04","B08","B11","B12"],
    "target_crs": "EPSG:32616",
    "target_resolution_m": 10,
    "resampling": "bilinear",
    "mask_source": "SCL",
    "baselines_computed": ["NDVI","NBR","NDMI"],
    "change_threshold_policy": "abs(ndvi_diff) > 0.15 AND area >= 0.5ha",
    "ranking_formula": "score = min(abs(ndvi_delta_mean)/0.5, 1.0) * sqrt(area_ha/max_area)"
  },
  "findings": [
    {"id": 1, "score": 0.72, "area_ha": 2.3, "geometry_file": "findings.geojson",
     "metrics": {"ndvi_delta_mean": -0.32, "nbr_delta_mean": -0.18, "ndmi_delta_mean": null}}
  ],
  "artifacts": {
    "before_image": "before.png",
    "after_image": "after.png",
    "overlay": "overlay.png",
    "findings": "findings.geojson"
  },
  "software": {
    "oberon": "0.1.0",
    "python": "3.12.5",
    "rasterio": "1.5.0",
    "numpy": "1.26.4",
    "scipy": "1.18.0"
  },
  "abstention": null
}
```

### 5.4 Output directory structure

```
<output-dir>/
├── before.png
├── after.png
├── overlay.png
├── findings.geojson
└── provenance.json
```

### 5.5 File changes

| File | Change | Test file |
|------|--------|-----------|
| `src/oberon/artifacts/images.py` | Implement: `render_true_color(red, green, blue, path) -> Path`, `render_change_overlay(before_rgb, change_mask, path) -> Path` | `tests/artifacts/test_images.py` |
| `src/oberon/artifacts/geojson.py` | Implement: `write_findings_geojson(findings, output_path, out_crs="EPSG:4326") -> Path` | `tests/artifacts/test_geojson.py` |
| `src/oberon/artifacts/provenance.py` | Complete: `build_provenance(findings, bundle, request, scenes, oberon_version) -> dict` | `tests/core/test_provenance.py` |

### 5.6 Edge cases to test

- No findings → writes empty FeatureCollection (valid GeoJSON with 0 features)
- Abstention → only provenance.json written, abstention field populated
- Output directory doesn't exist → created automatically
- Image rendering with extreme values (all-0, all-10000) → clip handles gracefully
- Single-pixel finding → rendered as 1-pixel polygon in overlay
- Findings in different CRS than WGS84 → GeoJSON writer reprojects

---

## 6. Phase 5 — CLI Wiring + Pipeline Orchestration (complete design)

### 6.1 Purpose

Wire all stages into a runnable CLI command. The orchestrator calls stages in order, passes typed objects between them, handles abstention at any point, and writes the output bundle.

### 6.2 CLI interface

```bash
oberon analyze \
  --aoi path/to/polygon.geojson \
  --before 2026-01-01 \
  --after 2026-06-01 \
  --task vegetation_disturbance \
  --output ./oberon-output
```

### 6.3 Orchestration flow (pseudocode)

```python
def run_analysis(request: ChangeRequest, output_dir: Path) -> EvidenceBundle:
    # Phase 1: Discover scenes
    candidates = search_catalog(request)
    scenes = rank_by_scene_quality(candidates, before_window=request.before, after_window=request.after)
    if not scenes:
        return abstention_result("No suitable scenes found")

    # Separate before/after
    before_scene = next((s for s in scenes if s.period == "before"), None)
    after_scene = next((s for s in scenes if s.period == "after"), None)
    if not before_scene or not after_scene:
        return abstention_result(f"Missing {'before' if not before_scene else 'after'} scene")

    # Phase 2: Read + prepare
    before_window = read_window(before_scene.candidate, request.geometry)
    after_window = read_window(after_scene.candidate, request.geometry)
    pair = align_to_common_grid(before_window, after_window)
    if not pair.is_usable:
        return abstention_result(f"Insufficient valid pixels: {pair.valid_fraction:.0%}")

    # Phase 3: Baselines + change detection
    baseline = compute_baselines(pair)
    if baseline.abstain:
        return abstention_result(baseline.abstain_reason)
    findings = extract_findings(threshold_change_map(baseline.ndvi_diff), baseline.ndvi_diff)
    findings = deduplicate_and_rank(findings, max_findings=20)

    # Phase 4: Evidence
    bundle = build_evidence_bundle(findings, pair, request, scenes, output_dir)
    render_images(pair, findings, bundle)
    write_findings_geojson(findings, bundle.findings_geojson)
    provenance = build_provenance(findings, bundle, request, scenes)
    write_provenance_manifest(provenance, bundle.provenance_manifest)

    click.echo(f"Analysis complete: {len(findings)} findings → {output_dir}")
    return bundle
```

### 6.4 Error handling strategy

| Failure point | Behavior |
|---------------|----------|
| STAC API unreachable | Print error, exit code 2 |
| Invalid polygon file | Print geoJSON validation error, exit code 1 |
| No scenes found | Print "No suitable Sentinel-2 scenes for AOI/date range", exit code 0 (non-error) |
| COG read fails for one scene | Log error, try next-best candidate if available |
| Preparation fails | Print "Could not produce comparable before/after imagery", exit code 1 |
| All abstention paths | Exit code 0, provenance shows abstention reason |

### 6.5 File changes

| File | Change | Test file |
|------|--------|-----------|
| `src/oberon/cli/main.py` | Complete: click `analyze` command with all options, validation, error handling | `tests/cli/test_analyze.py` |
| `src/oberon/cli/orchestrator.py` | Implement: `run_analysis(request, output_dir) -> EvidenceBundle` with abstention handling | — (tested through CLI) |

---

## 7. Phase 6 — Verify & QA

| Gate | Command | Criteria |
|------|---------|----------|
| Lint | `ruff check src/ tests/` | 0 exit |
| Type check | `mypy src/` | 0 exit (allow `# type: ignore` on Rasterio/NumPy signatures) |
| Unit tests | `pytest tests/ -v --tb=short` | ≥ 41 (Phase 1 baseline) + new tests, 0 failures, 0 warnings |
| Integration tests | `pytest tests/ -v -m integration` | All green (requires network for STAC queries, uses mocked COG reads) |
| Bounds preflight | `bounds preflight --ci` | Green (no boundary violations, no orphan exports, no stale manifests) |
| Bounds validate | `bounds validate -H` | Fresh, 0 warnings |
| Ponytail audit | Manual check of `# ponytail:` comments | Every shortcut names the ceiling and upgrade path |
| Docs consistency | Manual review | CLAUDE.md, AGENTS.md, docs/architecture/ match actual code |

---

## 8. Phase 7 — Cleanup & Documentation (END)

| Task | Details |
|------|---------|
| DRY sweep | Check for duplicated mask logic across cog_reader, preparation, scene_quality; extract shared constants (SCL_CLOUD_BITS, BAND_LISTS) into core/__init__.py if repeated |
| Doc sync | Update AGENTS.md gotchas with any surprises from COG URL patterns, CRS handling, or abstention edge cases |
| README check | Verify quick-start command works end-to-end |
| Bounds re-baseline | `bounds calibrate --dump-baseline` after all new manifests |
| Git history | Squash feature commits into clean history; orphan-free |
| Output contract | EvidenceBundle output from Phase 4 must match the POST /v1/change response shape from the blueprint for forward-compatibility with the future API |

---

## 9. Data contract cross-reference

Every stage boundary in the pipeline uses typed dataclasses. The table below shows the shape contract between stages. Any change to a contract must update ALL consumers.

| Stage boundary | Output type | Consumer | Fields REQUIRED by next stage |
|---------------|-------------|----------|-------------------------------|
| STAC discovery → quality | `list[CandidateScene]` | scene_quality | `stac_item_id`, `datetime`, `assets` (with band URLs), `scene_cloud_pct` |
| Quality → COG reader | `SelectedScene` | cog_reader | `candidate.assets` (band COG URLs + SCL URL), `candidate.geometry` |
| COG reader → preparation | `RasterWindow` | preparation | `data[band]` (2D array), `crs`, `transform`, `scl_mask` |
| Preparation → baselines | `PreparedPair` | baselines | `before`/`after` (same keys), `mask` (bool, same shape) |
| Baselines → change detection | `BaselineResult` | change_detection | `ndvi_diff` (2D float, NaN where masked) |
| Change detection → evidence | `list[Finding]` | artifacts | `geometry` (GeoJSON), `score`, `area_ha`, `ndvi_delta_mean` |

---

## 10. Risk register (updated)

| Risk | Phase | Likelihood | Impact | Mitigation |
|------|-------|-----------|--------|------------|
| COG URL format changes (AWS S3 bucket restructure) | 2 | Low | High | Centralize URL construction in one function (`cog_url(band, tile, date)`). Update one function on upstream change. |
| Before/after observations have different CRS | 2 | Medium | Medium | Rasterio handles reprojection in `reproject()`; test with different-zone fixtures. |
| AOI spans UTM zone boundary | 2 | Low | Medium | Reproject both to zone of AOI centroid. Document as ponytail approximation. |
| Large AOI (> 1000 km²) memory exhaustion | 2,3 | Medium | High | First pass: full-AOI processing, documented limitation. Ponytail marker: "tiled processing for AOIs > 1000 km²". |
| SCL band missing from some items | 2 | Medium | Low | Fall back to nodata-only mask. Scene-cloud % as second proxy. |
| COG read timeouts (network flaky) | 2 | Medium | Medium | Add timeout + retry with exponential backoff (3 attempts, 2s/4s/8s). |
| Connected components over-segment large change regions | 3 | Medium | Low | Use scipy `ndimage.label` with structure element to merge adjacent pixels. Ponytail marker: "morphological closing for cohesive regions". |
| False positives from seasonal vegetation variation | 3 | High | High | NDVI diff threshold tuned empirically. Abstention for near-equal-date scenes. Documented as evaluation risk. |
| No labelled evaluation dataset | 3 | High | High | Walking slice is a technical benchmark, not production evaluation. Thresholds and scores are ponytail defaults. |
| Provenance JSON grows large for many findings | 4 | Low | Low | Max 20 findings per run; provenance stays under 50KB. |
| Image rendering with extreme radiance values | 4 | Low | Medium | Percentile-based clip (2%-98%) handles outliers. Test with edge-case arrays. |
| Dependencies pinning drifts over time | 6 | Medium | Medium | `uv.lock` committed. CI checks `uv sync --frozen`. |

---

## 11. End-phase cleanup (per-phase)

| Phase | Before moving on, verify |
|-------|--------------------------|
| Phase 2 | `pytest tests/pipeline/test_cog_reader.py tests/pipeline/test_preparation.py -v` green; `ruff` green; `bounds validate --quick` green |
| Phase 3 | `pytest tests/core/test_baselines.py tests/core/test_change_detection.py -v` green; `ruff` green |
| Phase 4 | `pytest tests/artifacts/ tests/core/test_provenance.py -v` green; manual check that output files are valid PNG/GeoJSON/JSON |
| Phase 5 | `oberon analyze --help` works; `oberon analyze --aoi tests/data/sample.geojson --before 2026-01-01 --after 2026-06-01` runs end-to-end with mocked COG |
| Phase 6 | Full suite: lint 0, mypy 0, pytest 0, bounds preflight 0 |
