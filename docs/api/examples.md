# Usage Examples

**Parent**: [../../README.md](../../README.md)

## Basic analysis

```bash
oberon analyze \
  --aoi aoi.geojson \
  --before-start 2024-01-01 --before 2024-03-01 \
  --after-start 2024-07-01 --after 2024-09-01 \
  -o output/
```

Output:
```
Analysis complete: 3 finding(s)
  Before image:  output/before.png
  After image:   output/after.png
  Overlay:       output/overlay.png
  Findings:      output/findings.geojson
  Provenance:    output/provenance.json
```

## JSON output (programmatic)

```bash
oberon analyze \
  --aoi aoi.geojson \
  --before-start 2024-01-01 --before 2024-03-01 \
  --after-start 2024-07-01 --after 2024-09-01 \
  --json
```

Outputs the full Product Brief section 5 ChangeResponse shape on stdout. See [cli.md](cli.md) for the schema.

## With AI triage

Requires `uv sync --extra ai` and the Clay v1.5 checkpoint (~5GB).

```bash
oberon analyze \
  --aoi aoi.geojson \
  --before-start 2024-01-01 --before 2024-03-01 \
  --after-start 2024-07-01 --after 2024-09-01 \
  --use-ai -o output/
```

Runs Clay v1.5 feature extraction alongside the deterministic baseline. AI is experimental - the deterministic result is always produced regardless.

## Cloud-masked composite

When cloud cover is high, merge up to 3 scenes per period:

```bash
oberon analyze \
  --aoi aoi.geojson \
  --before-start 2024-01-01 --before 2024-03-01 \
  --after-start 2024-07-01 --after 2024-09-01 \
  --composite -o output/
```

## Request file mode

For programmatic or API-compatible invocations:

```bash
# Create request.json
cat > request.json << 'EOF'
{
  "geometry": {"type": "Polygon", "coordinates": [[[...]]]},
  "before": {"from": "2024-01-01", "to": "2024-03-01"},
  "after": {"from": "2024-07-01", "to": "2024-09-01"}
}
EOF

oberon analyze --request request.json -o output/
```

This is the same JSON shape the Rust control plane uses.

## Docker

### CPU

```bash
docker build -t oberon:cpu .

docker run --rm \
  -v "$PWD/input:/input:ro" \
  -v "$PWD/output:/output" \
  oberon:cpu analyze \
    --aoi /input/aoi.geojson \
    --before-start 2024-01-01 --before 2024-03-01 \
    --after-start 2024-07-01 --after 2024-09-01 \
    -o /output
```

### GPU (requires nvidia-docker)

```bash
docker compose --profile gpu run --rm oberon-gpu analyze \
  --aoi /input/aoi.geojson \
  --before-start 2024-01-01 --before 2024-03-01 \
  --after-start 2024-07-01 --after 2024-09-01 \
  --use-ai -o /output
```

## Python (SDK)

```python
from datetime import date
from oberon.core import ChangeRequest
from oberon.cli.orchestrator import run_analysis

request = ChangeRequest(
    geometry=load_geojson("aoi.geojson"),
    before=(date(2024, 1, 1), date(2024, 3, 1)),
    after=(date(2024, 7, 1), date(2024, 9, 1)),
)

bundle = run_analysis(request, output_dir="./output")

# Check for abstention
if bundle.provenance.get("abstention"):
    print(f"Abstained: {bundle.provenance['abstention']['reason']}")
else:
    findings = bundle.provenance.get("findings", [])
    print(f"Found {len(findings)} change region(s)")
```

See [examples/sdk_demo.py](../../examples/sdk_demo.py) for a full working demo.

## Health check

```bash
oberon health          # human-readable
oberon health --json   # JSON output
```

Verifies version, torch availability, STAC API reachability, and cache size. Use before running analysis in a new environment.

## Handling abstention

Abstention is a valid result (exit code 0), not an error. It means the pipeline could not produce reliable findings given the inputs.

Common abstention reasons:
- Insufficient valid pixels (cloud cover too high over the AOI)
- No suitable scenes found for the date range
- Before/after windows too close together

Remediation:
- Try `--composite` to merge multiple cloud-free scenes
- Widen the date windows
- Increase `--max-cloud` tolerance
