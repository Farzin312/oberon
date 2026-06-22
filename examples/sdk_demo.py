"""Oberon SDK example — full analysis workflow from Python.

This demonstrates the programmatic API for running an Oberon analysis
without going through the CLI. It uses the same pipeline stages.

Usage:
    uv run python examples/sdk_demo.py

Requires a GeoJSON AOI file and network access to the STAC catalog.
"""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

from oberon.cli.orchestrator import run_analysis
from oberon.core import ChangeRequest


def load_geojson(path: str | Path) -> dict[str, object]:
    """Load a GeoJSON file and return the geometry dict."""
    with open(path) as f:
        geojson = json.load(f)

    # Handle FeatureCollection: extract first feature's geometry.
    if geojson.get("type") == "FeatureCollection" and geojson.get("features"):
        feat = geojson["features"][0]
        return feat.get("geometry") or feat  # type: ignore[return-value]

    return geojson.get("geometry") or geojson  # type: ignore[return-value]


def main() -> None:
    # 1. Load your area of interest.
    aoi_path = "tests/data/sample.geojson"
    if not Path(aoi_path).exists():
        print(f"AOI file not found: {aoi_path}")
        print("Provide a GeoJSON polygon file.")
        return

    geometry = load_geojson(aoi_path)

    # 2. Define before/after windows.
    request = ChangeRequest(
        geometry=geometry,
        before=(date(2026, 1, 1), date(2026, 2, 1)),
        after=(date(2026, 6, 1), date(2026, 7, 1)),
        task="vegetation_disturbance",
        max_cloud_fraction=0.15,
        min_valid_pixels=0.30,
    )

    # 3. Run the analysis pipeline.
    output_dir = Path("./oberon-output")
    print(f"Analyzing AOI for {request.task}...")
    print(f"  Before: {request.before[0]} to {request.before[1]}")
    print(f"  After:  {request.after[0]} to {request.after[1]}")
    print()

    bundle = run_analysis(request, output_dir, use_ai=False)

    # 4. Check for abstention.
    provenance = bundle.provenance
    if provenance.get("abstention"):
        reason = provenance["abstention"]["reason"]
        print(f"Abstained: {reason}")
        print("The pipeline determined inputs were insufficient for a reliable result.")
        return

    # 5. Report findings.
    findings = provenance.get("findings", [])
    print(f"Analysis complete: {len(findings)} finding(s)")
    print()

    for i, f in enumerate(findings, start=1):
        score = f["score"]
        area_ha = f["area_ha"]
        ndvi = f["metrics"]["ndvi_delta_mean"]
        nbr = f["metrics"]["nbr_delta_mean"]
        print(f"  Finding {i}: score={score:.2f}, area={area_ha:.1f}ha")
        print(f"    NDVI delta: {ndvi:+.3f}, NBR delta: {nbr:+.3f}")

    print()
    print("Artifacts:")
    print(f"  Before image:  {bundle.before_image}")
    print(f"  After image:   {bundle.after_image}")
    print(f"  Overlay:       {bundle.overlay_image}")
    print(f"  Findings:      {bundle.findings_geojson}")
    print(f"  Provenance:    {bundle.provenance_manifest}")

    # 6. Use the API serialization layer for structured output.
    from oberon.api.serialization import serialize_bundle_to_response

    response = serialize_bundle_to_response(bundle)
    print()
    print(f"API response status: {response.status.value}")
    print(f"  Findings: {len(response.findings)}")
    for f in response.findings:
        print(f"    change_score={f.change_score:.2f}, "
              f"area={f.changed_area_m2:.0f}m2, "
              f"encoder={f.model.encoder}")


if __name__ == "__main__":
    main()
