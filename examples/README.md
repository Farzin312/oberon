# Oberon Examples

Example scripts showing how to use Oberon programmatically.

## sdk_demo.py

Full analysis workflow from Python — load an AOI, define date windows, run the pipeline, and report findings. Demonstrates both the core pipeline API and the API serialization layer.

```bash
# Run the demo (requires network access to STAC catalog)
uv run python examples/sdk_demo.py

# Or with Docker
docker run --rm \
  -v "$PWD/examples:/examples:ro" \
  -v "$PWD/output:/output" \
  oberon:cpu python /examples/sdk_demo.py
```

## Writing your own script

```python
from datetime import date
from oberon.core import ChangeRequest
from oberon.cli.orchestrator import run_analysis

request = ChangeRequest(
    geometry=your_geojson_polygon,
    before=(date(2026, 1, 1), date(2026, 2, 1)),
    after=(date(2026, 6, 1), date(2026, 7, 1)),
)

bundle = run_analysis(request, output_dir="./output")

# Check for abstention
if bundle.provenance.get("abstention"):
    print(f"Abstained: {bundle.provenance['abstention']['reason']}")
else:
    findings = bundle.provenance.get("findings", [])
    print(f"Found {len(findings)} change region(s)")
```
