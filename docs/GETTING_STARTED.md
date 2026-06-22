# Getting Started

**Parent**: [README.md](../README.md)

This guide covers the three ways to use Oberon: CLI (zero cost), API server
(self-hosted), and Docker. Pick your path and follow the steps.

---

## Prerequisites

- Python 3.12+
- [uv](https://docs.astral.sh/uv/) package manager
- GDAL system libraries (macOS: `brew install gdal`, Ubuntu: `sudo apt install libgdal-dev`)
- Optional: Rust toolchain for the API server (`rustup.rs`)
- Optional: Docker for containerized deployment

---

## Path 1: CLI (zero cost, zero hosting)

### Install

```bash
git clone https://github.com/farzin/oberon.git
cd oberon
uv sync
```

### First run

```bash
# Verify setup (checks Python, GDAL, STAC reachability)
oberon init

# Run analysis on the sample AOI
# Sample AOI: Amazon deforestation arc (Para, Brazil)
oberon analyze \
  --aoi sample-aoi.geojson \
  --before-start 2024-01-01 --before 2024-03-01 \
  --after-start 2024-07-01 --after 2024-09-01 \
  -o output/
```

### What you get

Output directory contains:
- `before.png`, `after.png`, `overlay.png` — true-color imagery + change overlay
- `findings.geojson` — ranked change polygons with NDVI/NBR deltas and area
- `provenance.json` — full provenance (source scenes, config, model versions)

### Common options

```bash
# JSON output (for programmatic use / piping)
oberon analyze --aoi sample-aoi.geojson \
  --before-start 2024-01-01 --before 2024-03-01 \
  --after-start 2024-07-01 --after 2024-09-01 --json

# Cloud-masked composite (merge up to 3 scenes when single scene too cloudy)
oberon analyze --aoi sample-aoi.geojson \
  --before-start 2024-01-01 --before 2024-03-01 \
  --after-start 2024-07-01 --after 2024-09-01 --composite

# Request file mode (ChangeRequestAPI JSON schema)
oberon analyze --request request.json -o output/

# Check system health
oberon health
oberon health --json

# Version
oberon --version
```

### Date window behavior

Both `--before` and `--after` default to a 30-day lookback from the given date.
Override with `--before-start` and `--after-start`:

```bash
oberon analyze \
  --aoi sample-aoi.geojson \
  --before-start 2024-01-01 --before 2024-03-31 \
  --after-start 2024-07-01 --after 2024-09-30 \
  -o output/
```

### Creating your own AOI

Need a polygon for your own area? Three options:

**1. Built-in `oberon aoi` command** (fastest):

```bash
# Generate a 5km box around any coordinate, write to file
oberon aoi --lat 41.82 --lon -93.62 -o my-aoi.geojson

# Custom buffer size (10km box)
oberon aoi --lat -7.475 --lon -55.175 --buffer 5.0 -o my-aoi.geojson

# Print to stdout (pipe into other tools)
oberon aoi --lat 41.82 --lon -93.62
```

**2. Draw on a map** with [geojson.io](https://geojson.io):

Open the site, draw a polygon with the toolbar, copy the GeoJSON from the
right panel, save as `.geojson`.

**3. Use QGIS or any GIS tool**:

Draw a polygon, export as GeoJSON. Oberon accepts Feature, bare Geometry,
or FeatureCollection (uses the first feature).

See [`samples/README.md`](../samples/README.md) for ready-to-use sample AOIs
covering deforestation, wildfire, and cropland change.

### Configuration

All defaults work out of the box. Override via environment variables:

| Variable | Default | Purpose |
|----------|---------|---------|
| `OBERON_STAC_URL` | Earth Search / Element84 | STAC catalog endpoint |
| `OBERON_STAC_TIMEOUT` | 30 | STAC connection timeout (s) |
| `OBERON_COG_TIMEOUT` | 60 | COG read timeout (s) |
| `OBERON_LOG_FORMAT` | console | `console` (human) or `json` (containers) |
| `OBERON_CACHE_DIR` | ~/.cache/oberon | COG window cache |

See `.env.example` for the full list including control-plane vars.

---

## Path 2: API server (self-hosted)

### Build and run

```bash
cd control-plane
cargo build --release

# Start with auth disabled for local dev
OBERON_AUTH_DISABLED=1 ./target/release/oberon-control-plane serve
```

Server starts at http://localhost:8000.

### Create an API key (for production use)

```bash
./target/release/oberon-control-plane auth create-key --user "your-name"
# Output: oberon_<32 hex chars>
# Store securely — shown once only.
```

### Use the API

```bash
# Health check (no auth required)
curl http://localhost:8000/v1/health

# Submit analysis (auth required unless OBERON_AUTH_DISABLED=1)
curl -X POST http://localhost:8000/v1/change \
  -H "Content-Type: application/json" \
  -H "X-API-Key: oberon...ere" \
  -d '{
    "geometry": {"type": "Polygon", "coordinates": [[[...]]]},
    "before": {"from": "2024-01-01", "to": "2024-03-01"},
    "after": {"from": "2024-07-01", "to": "2024-09-01"}
  }'

# Response: {"job_id": "abc-123", "status": "pending"}

# Poll for results
curl http://localhost:8000/v1/jobs/abc-123 \
  -H "X-API-Key: oberon_your_key_here"

# Get artifacts
curl http://localhost:8000/v1/jobs/abc-123/artifacts/overlay.png \
  -H "X-API-Key: oberon_your_key_here" --output overlay.png
```

### Web dashboard

Open http://localhost:8000/ in your browser. The dashboard lets you:
- Create portfolios and add AOI polygons
- Run analysis across all polygons
- View findings on a Leaflet map
- Review findings (approve/reject/uncertain)

No build step, no npm. Just vanilla JS + Leaflet from CDN.

**Important: auth and the dashboard.** The dashboard JS makes API calls
without `X-API-Key` headers. When auth is enabled, these calls return 401
and the dashboard appears empty. For local dev, always start the server with
`OBERON_AUTH_DISABLED=1`. For production use behind auth, you would need to
inject the API key via a proxy or cookie — this is not built in yet.

### Dashboard walkthrough

A complete first-use flow from server start to viewing results:

**Step 1: Build and start the server**

```bash
cd control-plane
cargo build --release
OBERON_AUTH_DISABLED=1 ./target/release/oberon-control-plane serve
```

You should see a startup log like:
```
INFO oberon_control_plane: listening on 0.0.0.0:8000
```

**Step 2: Verify the server is running**

```bash
curl http://localhost:8000/v1/health
# {"status":"healthy","version":"...","active_jobs":0}
```

**Step 3: Open the dashboard**

Navigate to http://localhost:8000/ in your browser. You should see:
- Left panel: portfolio list (empty on first run)
- Right panel: a dark-themed Leaflet map
- Top bar: "New Portfolio" button

**Step 4: Create a portfolio**

Click "New Portfolio". Enter a name (e.g. "Amazon Monitoring").
The portfolio appears in the left panel.

**Step 5: Add an AOI polygon**

Click "+ AOI" on the portfolio. Paste a GeoJSON geometry. You can get one
from `oberon aoi` or from the `samples/` directory:

```bash
# Generate a polygon to paste
oberon aoi --lat -7.475 --lon -55.175
```

Copy the output JSON and paste it into the prompt. Click OK.

**Step 6: Run analysis**

Click "Run" on the portfolio. The server spawns a Python subprocess for each
polygon. This takes 30-60 seconds per polygon (STAC search + COG read +
change detection). You'll see an alert with the job count.

**Step 7: View results**

Click "Map" on the portfolio. The map zooms to your AOI and shows:
- Blue polygons: your AOI boundaries
- Orange polygons: detected change findings
- Click a finding to see its change score, area, and NDVI/NBR deltas

**Step 8: Review findings (optional)**

Click a finding to open the detail panel. Use Approve/Reject/Uncertain
buttons to record your assessment. Export review decisions via:

```bash
curl http://localhost:8000/v1/reviews/export?portfolio=<id>
```

**Alternative: CLI instead of dashboard.** All of the above can be done via
curl or the CLI. The dashboard is a convenience layer over the same API.

### Portfolio workflow

```bash
# Create a portfolio
curl -X POST http://localhost:8000/v1/portfolios \
  -H "Content-Type: application/json" \
  -H "X-API-Key: oberon_your_key" \
  -d '{"name": "Amazon Monitoring"}'

# Add a polygon
curl -X POST http://localhost:8000/v1/portfolios/<id>/polygons \
  -H "Content-Type: application/json" \
  -H "X-API-Key: oberon_your_key" \
  -d '{"geometry": {...}, "label": "Plot A"}'

# Run analysis for all polygons
curl -X POST http://localhost:8000/v1/portfolios/<id>/run \
  -H "X-API-Key: oberon_your_key"

# List portfolios
curl http://localhost:8000/v1/portfolios \
  -H "X-API-Key: oberon_your_key"

# Get findings as GeoJSON
curl http://localhost:8000/v1/portfolios/<id>/findings \
  -H "X-API-Key: oberon_your_key"

# Review findings
curl -X POST http://localhost:8000/v1/reviews \
  -H "Content-Type: application/json" \
  -H "X-API-Key: oberon_your_key" \
  -d '{
    "run_id": "<run-id>",
    "finding_idx": 0,
    "portfolio_id": "<portfolio-id>",
    "state": "approved",
    "reviewer_notes": "Confirmed deforestation"
  }'

# Export review decisions (for model calibration)
curl http://localhost:8000/v1/reviews/export?portfolio=<id> \
  -H "X-API-Key: oberon_your_key"

# Export audit log
curl http://localhost:8000/v1/audit/export \
  -H "X-API-Key: oberon_your_key"
```

---

## Path 3: Docker (zero install)

### CLI only

```bash
docker build -t oberon:cpu .
docker run --rm \
  -v "$PWD:/data" \
  oberon:cpu analyze \
    --aoi /data/sample-aoi.geojson \
    --before-start 2024-01-01 --before 2024-03-01 \
    --after-start 2024-07-01 --after 2024-09-01 \
    -o /data/output
```

### Server (Rust + Python in one container)

```bash
docker compose --profile server up
```

Dashboard at http://localhost:8000/. SQLite data persists in a named volume.

---

## Logging

Both Python and Rust follow the same logging standard (see
[LOGGING_STANDARD.md](LOGGING_STANDARD.md)).

- Default format: `console` (ANSI-colored, human-readable)
- Container format: set `OBERON_LOG_FORMAT=json`
- Rust verbosity: set `RUST_LOG=debug` (or `trace` for everything)

Every job logs: started, completed/abstained/failed, with duration_ms,
output_mb, peak_rss_mb, and active_jobs count.

---

## Troubleshooting

### "GDAL not found" / rasterio import errors

Install GDAL system libraries:
- macOS: `brew install gdal`
- Ubuntu: `sudo apt install libgdal-dev`
- Or use Docker (no system install needed)

### Analysis abstains with "No suitable scenes"

The STAC search found no cloud-free scenes in your date window. Try:
- Widening the date range (both --before and --after default to 30-day windows)
- Adding `--composite` to merge multiple scenes
- Checking `oberon health` to verify STAC is reachable

### "STAC API: unreachable" in health check

Check your network connection or firewall. The default STAC endpoint is
`https://earth-search.aws.element84.com/v1`. Override with
`OBERON_STAC_URL` if you need a different catalog.

### Server returns 401 Unauthorized

Set `OBERON_AUTH_DISABLED=1` for local dev, or create a key with
`oberon-control-plane auth create-key --user "name"` and pass it in the
`X-API-Key` header.

### Rust build is slow

First `cargo build` takes 3-5 minutes (compiling all dependencies).
Subsequent builds are incremental and fast. Use `cargo build --release` for
production.
