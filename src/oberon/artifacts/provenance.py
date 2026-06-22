"""Provenance manifest — a first-class record of how each finding was produced."""

from __future__ import annotations

import json
import platform
from pathlib import Path
from typing import Any

import numpy as np

from oberon.core import EvidenceBundle, Finding


def build_provenance(
    findings: list[Finding],
    bundle: EvidenceBundle,
    oberon_version: str = "0.1.0",
    abstention_reason: str | None = None,
    source_info: dict[str, Any] | None = None,
    model_versions: list[str] | None = None,
    processing_config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Construct the provenance dictionary for a set of findings.

    This is product data, not logging. It records every detail needed
    to independently verify or reproduce a result.

    Args:
        model_versions: List of registered model version strings used
            in this run (e.g. ["deterministic-v1", "clay-v1.5"]).
            Defaults to ["deterministic-v1"].
        processing_config: Processing parameters that produced these
            findings (task name, threshold direction, closing kernel
            size, etc.). Required by CLAUDE.md rule 3.
    """
    if model_versions is None:
        model_versions = ["deterministic-v1"]
    finding_entries = []
    for idx, f in enumerate(findings, start=1):
        finding_entries.append({
            "id": idx,
            "score": f.score,
            "area_ha": f.area_ha,
            "metrics": {
                "ndvi_delta_mean": f.ndvi_delta_mean,
                "nbr_delta_mean": f.nbr_delta_mean,
                "pixel_delta_mean": f.pixel_delta_mean,
                "valid_pixels_in_finding": f.valid_pixels_in_finding,
            },
        })

    provenance: dict[str, Any] = {
        "oberon_version": oberon_version,
        "model_versions": model_versions,
        "artifacts": {
            "before_image": bundle.before_image.name if bundle.before_image else None,
            "after_image": bundle.after_image.name if bundle.after_image else None,
            "overlay": bundle.overlay_image.name if bundle.overlay_image else None,
            "findings": bundle.findings_geojson.name if bundle.findings_geojson else None,
        },
        "findings": finding_entries,
        "software": _collect_software_versions(oberon_version),
        "abstention": None,
    }

    if source_info:
        provenance["sources"] = source_info

    if processing_config:
        provenance["processing_config"] = processing_config

    if abstention_reason:
        provenance["abstention"] = {"reason": abstention_reason}

    return provenance


def write_provenance_manifest(provenance: dict[str, Any], output_path: Path) -> Path:
    """Write the provenance manifest as pretty-printed JSON."""
    with open(output_path, "w") as f:
        json.dump(provenance, f, indent=2, default=str)
    return output_path


def _collect_software_versions(oberon_version: str) -> dict[str, str]:
    """Record runtime versions for reproducibility."""
    versions: dict[str, str] = {
        "oberon": oberon_version,
        "python": platform.python_version(),
        "numpy": np.__version__,
    }
    try:
        import rasterio
        versions["rasterio"] = rasterio.__version__
    except ImportError:
        pass
    try:
        import scipy
        versions["scipy"] = scipy.__version__
    except ImportError:
        pass
    try:
        import shapely
        versions["shapely"] = shapely.__version__
    except ImportError:
        pass
    return versions
