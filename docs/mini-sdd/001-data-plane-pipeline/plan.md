# Plan — Data Plane Pipeline (Walking Vertical Slice)

**Parent**: [../README.md](../README.md)

Companion to [README.md](./README.md) (decisions + scope) and [tasks.md](./tasks.md) (checklist).

---

## 1. Repo facts (verified)

| Area | Current state | Source |
|------|--------------|--------|
| Project dir | Bare repo at `~/oberon`, no source files yet | `git status` |
| Python env | No `pyproject.toml` or `uv.lock` yet | dir listing |
| Package layout | `src/oberon/` directories created, empty | `find src/oberon -type f` |
| bounds | Not initialized | `ls .bounds/` → doesn't exist |
| STAC catalog | Earth Search STAC at `https://earth-search.aws.element84.com/v1` | EO-federation docs |
| Sentinel-2 COGs | `https://sentinel-cogs.s3.us-west-2.amazonaws.com/sentinel-s2-l2a-cogs/` | AWS Registry of Open Data |

---

## 2. Execution order

1. **Phase 0 — Setup** — `bounds init`, domain models (`ChangeRequest`, `CandidateScene`, `SelectedScene`, `PreparedPair`, `BaselineResult`, `Finding`, `EvidenceBundle`)
2. **Phase 1 — STAC Discovery + Scene Quality** — catalog search, scene ranking, selection (gate: tests passing for STAC query, quality assessment)
3. **Phase 2 — COG Reading + Preparation** — windowed reads, SCL masking, reprojection, alignment (gate: tests passing for COG reads, mask application)
4. **Phase 3 — Baseline Analytics** — NDVI/NBR/NDMI computation, pixel diffs, thresholding, polygon extraction (gate: tests passing for index calc, change detection)
5. **Phase 4 — Evidence Bundles + Provenance** — imagery composites, overlay rendering, GeoJSON output, provenance manifest (gate: tests passing for artifact generation)
6. **Phase 5 — CLI Wiring** — click command, orchestration, console output, error handling (gate: full end-to-end test runs)
7. **Phase 6 — Verify** — full test suite, lint, bounds preflight, docs sync

---

## 3. Architecture / contracts

### 3.1 Domain models (core/domain.py)

```python
@dataclass
class ChangeRequest:
    geometry: dict  # GeoJSON Polygon geometry
    before: tuple[date, date]
    after: tuple[date, date]
    task: str  # e.g., "vegetation_disturbance"
    max_cloud_fraction: float = 0.15

@dataclass
class CandidateScene:
    stac_item_id: str
    datetime: datetime
    geometry: dict
    bbox: tuple[float, float, float, float]
    assets: dict[str, str]  # band -> COG URL
    scl_url: str | None
    scene_cloud_pct: float

@dataclass
class SelectedScene:
    candidate: CandidateScene
    local_valid_fraction: float
    period: str  # "before" or "after"

@dataclass
class RasterWindow:
    data: dict[str, np.ndarray]  # band -> 2D array
    crs: str
    transform: tuple[float, ...]
    bounds: tuple[float, float, float, float]
    scl_mask: np.ndarray | None

@dataclass
class PreparedPair:
    before: dict[str, np.ndarray]  # aligned bands
    after: dict[str, np.ndarray]
    mask: np.ndarray  # valid pixels (True = valid)
    crs: str
    transform: tuple[float, ...]
    bounds: tuple[float, float, float, float]

@dataclass
class BaselineResult:
    ndvi_diff: np.ndarray | None
    nbr_diff: np.ndarray | None
    ndmi_diff: np.ndarray | None
    pixel_delta_magnitude: np.ndarray | None
    valid_pixels_before: int
    valid_pixels_after: int
    abstain: bool = False
    abstain_reason: str | None = None

@dataclass
class Finding:
    geometry: dict  # GeoJSON Polygon
    score: float
    area_ha: float
    ndvi_delta_mean: float
    nbr_delta_mean: float
    valid_pixels_in_finding: int

@dataclass
class EvidenceBundle:
    before_image: Path  # True-color PNG
    after_image: Path
    overlay_image: Path
    findings_geojson: Path
    provenance: dict
```

### 3.2 Pipeline stage signatures

```
change_request → STACDiscoveryResult(candidates: list[CandidateScene])
candidates → SceneQualityResult(before: SelectedScene | None, after: SelectedScene | None)
selected_scene → RasterWindow
raster_window × 2 → PreparedPair
prepared_pair → BaselineResult
baseline_result → list[Finding]
findings + prepared_pair → EvidenceBundle
```

### 3.3 Provenance manifest schema

```json
{
  "oberon_version": "0.1.0",
  "change_request": { "aoi_bbox": [...], "before": "2026-01-01", "after": "2026-06-01" },
  "scenes": {
    "before": { "item_id": "...", "datetime": "...", "url": "...", "valid_pixels": 0.85 },
    "after": { "item_id": "...", "datetime": "...", "url": "...", "valid_pixels": 0.91 }
  },
  "bands_used": ["B02", "B03", "B04", "B08", "B11", "B12"],
  "processing": {
    "resampling": "bilinear",
    "target_resolution_m": 10,
    "mask_source": "SCL",
    "baselines": ["NDVI", "NBR", "NDMI", "pixel_delta"],
    "threshold_policy": "abs(ndvi_diff) > 0.15 AND area >= 0.5ha"
  },
  "findings": [
    {
      "id": 0,
      "score": 0.72,
      "area_ha": 2.3,
      "geometry_path": "findings/finding_0.geojson",
      "metrics": { "ndvi_delta_mean": -0.32, "nbr_delta_mean": -0.18 }
    }
  ],
  "software": {
    "oberon": "0.1.0",
    "python": "3.12",
    "rasterio": "1.4.x",
    "numpy": "1.26.x"
  },
  "abstention": null
}
```

---

## 4. Exact changes per area

### 4.1 Domain models (`src/oberon/core/`)
- Create `src/oberon/core/__init__.py` — export all public types
- Create `src/oberon/core/domain.py` — all dataclass models (ChangeRequest, CandidateScene, etc.)
- Create `src/oberon/core/geometry.py` — geometry validation, bbox calculation, reprojection helpers

### 4.2 STAC discovery (`src/oberon/pipeline/`)
- Create `src/oberon/pipeline/__init__.py`
- Create `src/oberon/pipeline/stac_discovery.py` — search STAC catalog, parse results into CandidateScene list
- Create `src/oberon/pipeline/scene_quality.py` — local quality assessment, scene ranking, best-per-period selection

### 4.3 COG reading (`src/oberon/pipeline/`)
- Create `src/oberon/pipeline/cog_reader.py` — windowed band reads from COG URLs
- Create `src/oberon/pipeline/preparation.py` — SCL masking, reprojection, resampling, alignment

### 4.4 Baseline analytics (`src/oberon/core/`)
- Create `src/oberon/core/baselines.py` — NDVI, NBR, NDMI, pixel delta, valid-fraction
- Create `src/oberon/core/change_detection.py` — threshold → binary mask → connected components → Finding polygons

### 4.5 Evidence artifacts (`src/oberon/artifacts/`)
- Create `src/oberon/artifacts/__init__.py`
- Create `src/oberon/artifacts/images.py` — true-color PNG composites, overlay rendering
- Create `src/oberon/artifacts/geojson.py` — GeoJSON FeatureCollection writing
- Create `src/oberon/artifacts/provenance.py` — provenance manifest building and writing

### 4.6 CLI (`src/oberon/cli/`)
- Create `src/oberon/cli/__init__.py`
- Create `src/oberon/cli/main.py` — click command group and `analyze` command
- Create `src/oberon/cli/orchestrator.py` — call pipeline stages in order, handle abstention

### 4.7 Tests
- Create `tests/conftest.py` — shared fixtures
- Create `tests/data/sample.geojson` — small test polygon
- Create `tests/core/test_geometry.py` — geometry helpers
- Create `tests/core/test_baselines.py` — NDVI/NBR/NDMI computation
- Create `tests/core/test_change_detection.py` — thresholding, connected components
- Create `tests/core/test_provenance.py` — manifest building
- Create `tests/pipeline/test_stac_discovery.py` — STAC query parsing (integration)
- Create `tests/pipeline/test_cog_reader.py` — windowed reads (integration)
- Create `tests/pipeline/test_preparation.py` — masking, alignment (integration)
- Create `tests/artifacts/test_images.py` — composite rendering
- Create `tests/artifacts/test_geojson.py` — GeoJSON output

---

## 5. Risk register

| Risk | Mitigation |
|---|---|
| STAC catalog changes its API | Use pystac-client with strongly typed parsing; catalog adapter interface will isolate upstream changes |
| COG URL format changes | Tested against known-good scenes in golden tests; URL construction is centralized in one function |
| Large AOIs exceed memory | First pass processes all in one array; documented limitation with `# ponytail: full-AOI, tiled for AOIs > 1000 km²` |
| SCL classification inconsistencies between processing baselines | Golden test against known-baseline scene; mask function validates expected SCL values |
| Network requests flaky | Timeout + retry on STAC queries; documented dependency on public internet |
| No ground truth for validation | Mini-SDD explicitly scoped as technical benchmark, not production evaluation. Evaluation metrics against simple cases only |

---

## 6. End-phase cleanup

- **DRY sweep:** Check for duplicated mask logic, repeated CRS transforms, shared constants
- **Docs sync:** Update AGENTS.md gotchas with any discovered surprises; update `docs/architecture/` if architecture changed during implementation
- **Bounds re-baseline:** `bounds calibrate --dump-baseline` after all manifests are created
