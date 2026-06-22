# Data Flow — Pipeline Architecture

**Parent**: [README.md](README.md)

## Core pipeline

The walking vertical slice follows this data flow:

```
                    ┌──────────────────┐
                    │  User provides   │
                    │  AOI + date      │
                    │  windows + task  │
                    └────────┬─────────┘
                             │
                             ▼
                    ┌──────────────────┐
                    │  Stage 1: STAC   │
                    │  Catalog Search  │
                    │  ─────────────── │
                    │  Input: GeoJSON  │
                    │  polygon, date   │
                    │  windows         │
                    │                  │
                    │  Output: STAC    │
                    │  Items (cand.    │
                    │  observations)   │
                    └────────┬─────────┘
                             │
                             ▼
                    ┌──────────────────┐
                    │  Stage 2: Scene  │
                    │  Quality         │
                    │  ─────────────── │
                    │  For each item:  │
                    │  compute valid-  │
                    │  pixel fraction  │
                    │  over AOI using  │
                    │  SCL mask        │
                    │                  │
                    │  Output: best    │
                    │  before/after    │
                    │  candidates      │
                    └────────┬─────────┘
                             │
                             ▼
                    ┌──────────────────┐
                    │  Stage 3: COG    │
                    │  Windowed Read   │
                    │  ─────────────── │
                    │  Read only AOI   │
                    │  window + buffer │
                    │  for required    │
                    │  bands           │
                    │                  │
                    │  Output: numpy   │
                    │  arrays per band │
                    └────────┬─────────┘
                             │
                             ▼
                    ┌──────────────────┐
                    │  Stage 4:        │
                    │  Preparation     │
                    │  ─────────────── │
                    │  Apply SCL mask  │
                    │  (cloud, shadow, │
                    │  snow, invalid), │
                    │  reproject to    │
                    │  common CRS,     │
                    │  resample to     │
                    │  common grid     │
                    │                  │
                    │  Output: aligned │
                    │  before/after    │
                    │  arrays + masks  │
                    └────────┬─────────┘
                             │
                             ▼
            ┌────────────────┴────────────────┐
            │                                 │
            ▼                                 ▼
    ┌──────────────────┐            ┌──────────────────┐
    │  Stage 5a:       │            │  Stage 5b:       │
    │  Baseline        │            │  AI Inference    │
    │  Analytics       │            │  (optional)      │
    │  ────────────    │            │  ────────────    │
    │  NDVI diff       │            │  Clay feature    │
    │  NBR diff        │            │  maps, embed     │
    │  NDMI diff       │            │  diffs, change   │
    │  Pixel delta     │            │  score map       │
    │  Valid fraction  │            │                  │
    └────────┬─────────┘            └────────┬─────────┘
             │                              │
             └──────────┬───────────────────┘
                        │
                        ▼
               ┌──────────────────┐
               │  Stage 6:        │
               │  Postprocessing  │
               │  ─────────────── │
               │  Threshold →     │
               │  polygons,       │
               │  ranking →       │
               │  severity,       │
               │  top-K findings  │
               └────────┬─────────┘
                        │
                        ▼
               ┌──────────────────┐
               │  Stage 7:        │
               │  Evidence        │
               │  Bundles         │
               │  ─────────────── │
               │  Before/after    │
               │  imagery (PNG),  │
               │  overlay, masks, │
               │  GeoJSON,        │
               │  provenance      │
               │  manifest        │
               └────────┬─────────┘
                        │
                        ▼
               ┌──────────────────┐
               │  Output to user  │
               │  or call abstain │
               └──────────────────┘
```

## Data contracts between stages

Each stage has a typed input and output. These contracts are the API between pipeline stages and are the primary reason for the subsystem boundaries enforced by bounds.

| Stage | Primary contract | Key validation |
|-------|-----------------|---------------|
| STAC discovery | `ChangeRequest` → `list[CandidateScene]` | Polygon validity, date order, CRS |
| Scene quality | `list[CandidateScene]` → `SelectedScene` | Valid-pixel fraction > threshold |
| COG read | `CandidateScene` → `RasterWindow` | Bands exist, window valid, nodata handled |
| Preparation | `RasterWindow` × 2 → `PreparedPair` | CRS match, grid match, mask consistency |
| Baselines | `PreparedPair` → `BaselineResult` | Array shapes match, division by zero guarded |
| AI inference | `PreparedPair` → `ModelResult` (future) | Chip size match, band order matches adapter |
| Postprocessing | `PreparedPair` → `list[Finding]` | Minimum area, abstention thresholds |
| Evidence | `list[Finding]` + `PreparedPair` → `EvidenceBundle` | All artifacts present, provenance complete |
