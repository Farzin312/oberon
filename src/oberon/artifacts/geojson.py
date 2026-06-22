"""GeoJSON output for findings."""

from __future__ import annotations

from pathlib import Path

from oberon.core import Finding


def write_findings_geojson(
    findings: list[Finding],
    output_path: Path,
) -> Path:
    """Write a GeoJSON FeatureCollection of findings with change metrics.

    Each feature has properties: score, area_ha, ndvi_delta_mean,
    nbr_delta_mean, and valid_pixels_in_finding.
    """
    raise NotImplementedError("requires GeoJSON serialization")
