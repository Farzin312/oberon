"""GeoJSON output for findings."""

from __future__ import annotations

import json
from pathlib import Path

from oberon.core import Finding


def write_findings_geojson(
    findings: list[Finding],
    output_path: Path,
) -> Path:
    """Write a GeoJSON FeatureCollection of findings with change metrics.

    Each feature has properties: id, score, area_ha, ndvi_delta_mean,
    nbr_delta_mean, and valid_pixels_in_finding.

    ponytail: coordinates used as-is from Finding.geometry (already in
    the target CRS by the time this is called). Upgrade path: pyproj
    CRS transform from source CRS to EPSG:4326 if needed.
    """
    features = []
    for idx, finding in enumerate(findings, start=1):
        feature = {
            "type": "Feature",
            "geometry": finding.geometry,
            "properties": {
                "id": idx,
                "score": finding.score,
                "area_ha": finding.area_ha,
                "ndvi_delta_mean": finding.ndvi_delta_mean,
                "nbr_delta_mean": finding.nbr_delta_mean,
                "valid_pixels_in_finding": finding.valid_pixels_in_finding,
            },
        }
        features.append(feature)

    fc = {"type": "FeatureCollection", "features": features}
    with open(output_path, "w") as f:
        json.dump(fc, f, indent=2)
    return output_path
