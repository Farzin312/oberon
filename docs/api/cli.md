# CLI Reference

**Parent**: [../../README.md](../../README.md)

## Commands

### `oberon analyze`

Analyze a land area for vegetation change between two date windows.

#### Input modes

| Mode | Required flags | Description |
|------|---------------|-------------|
| Flag mode | `--aoi` + `--before` + `--after` | Point to a GeoJSON file and specify dates |
| Request mode | `--request` | Point to a JSON file with the full ChangeRequestAPI schema |

These two modes are mutually exclusive. Using `--request` with `--aoi` is an error.

#### Options

| Flag | Type | Default | Description |
|------|------|---------|-------------|
| `--aoi` | FILE | (required*) | Path to GeoJSON file with AOI polygon |
| `--before` | TEXT | (required*) | Before date window end (YYYY-MM-DD) |
| `--after` | TEXT | (required*) | After date window end (YYYY-MM-DD) |
| `--before-start` | TEXT | auto | Before window start. Defaults to 30 days before `--before`. |
| `--after-start` | TEXT | auto | After window start. Defaults to `--after`. |
| `--request` | FILE | (alt*) | Path to JSON request file (ChangeRequestAPI schema) |
| `--task` | TEXT | `vegetation_disturbance` | Task type |
| `-o`, `--output` | DIR | `./oberon-output` | Output directory for artifacts |
| `--max-cloud` | FLOAT | `15.0` | Maximum scene cloud cover % (0-100) |
| `--min-valid` | FLOAT | `0.30` | Minimum valid pixel fraction (0-1) |
| `--composite` | flag | off | Force cloud-masked composite (merge up to 3 scenes per period) |
| `--use-ai` | flag | off | Run Clay v1.5 feature extraction alongside baseline |
| `--cache` | flag | off | Enable session-level COG window cache |
| `--json` | flag | off | Output full API response as JSON |

*Required in flag mode only. In request mode, all fields come from the JSON file.

#### Output artifacts

When analysis completes, the output directory contains:

| File | Description |
|------|-------------|
| `before.png` | True-color Sentinel-2 image of the AOI before window |
| `after.png` | True-color Sentinel-2 image of the AOI after window |
| `overlay.png` | Before image with change mask overlaid in red |
| `findings.geojson` | Ranked change polygons with NDVI/NBR deltas and area |
| `provenance.json` | Full provenance manifest (scenes, config, model versions) |
| `artifact_index.json` | Per-artifact checksum index |

#### Exit codes

| Code | Meaning |
|------|---------|
| 0 | Analysis complete (with findings) OR abstained (insufficient data) |
| 1 | Error (invalid input, missing dependency) |
| 2 | CLI usage error (missing required flags) |

Abstention is a valid result, not an error. The CLI exits 0 and prefixes the message with "Abstained:".

#### `--json` output shape

When `--json` is set, stdout is pure JSON matching the Product Brief section 5 ChangeResponse shape:

```json
{
  "status": "review_recommended",
  "findings": [
    {
      "geometry": {"type": "Polygon", "coordinates": [[...]]},
      "change_score": 0.72,
      "suggested_class": null,
      "changed_area_m2": 23000.0,
      "evidence": {"ndvi_delta": -0.32, "nbr_delta": -0.45},
      "model": {"encoder": "deterministic-v1", "confidence": null}
    }
  ],
  "artifacts": {
    "before": "/path/to/before.png",
    "after": "/path/to/after.png",
    "overlay": "/path/to/overlay.png"
  }
}
```

Possible status values: `review_recommended`, `abstained`, `failed`.

#### `--request` JSON schema

```json
{
  "geometry": {"type": "Polygon", "coordinates": [[[lon, lat], ...]]},
  "before": {"from": "2026-01-01", "to": "2026-02-01"},
  "after": {"from": "2026-06-01", "to": "2026-07-01"},
  "task": "vegetation_disturbance",
  "max_cloud_fraction": 0.15
}
```

Only `geometry`, `before`, and `after` are required. `task` defaults to `vegetation_disturbance`, `max_cloud_fraction` defaults to `0.15`.

---

### `oberon health`

Check system health: version, torch availability, STAC reachability, cache status.

```bash
oberon health          # human-readable
oberon health --json   # JSON output
```

Output fields:

| Field | Description |
|-------|-------------|
| `status` | Always `healthy` if the command runs |
| `version` | Oberon package version |
| `torch_available` | Whether PyTorch is installed (for AI mode) |
| `stac_reachable` | Whether the STAC API endpoint responds |
| `cache_dir` | COG cache directory path |
| `cache_size_mb` | Cache directory size in MB |
