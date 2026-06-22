"""Provenance manifest — a first-class record of how each finding was produced."""

from __future__ import annotations

import json
import platform
from pathlib import Path

import numpy as np

from oberon.core import EvidenceBundle, Finding


def build_provenance(
    findings: list[Finding],
    bundle: EvidenceBundle,
    oberon_version: str = "0.1.0",
    abstention_reason: str | None = None,
) -> dict:
    """Construct the provenance dictionary for a set of findings.

    This is product data, not logging. It records every detail needed
    to independently verify or reproduce a result.
    """
    finding_entries = []
    for idx, f in enumerate(findings, start=1):
        finding_entries.append({
            "id": idx,
            "score": f.score,
            "area_ha": f.area_ha,
            "metrics": {
                "ndvi_delta_mean": f.ndvi_delta_mean,
                "nbr_delta_mean": f.nbr_delta_mean,
                "valid_pixels_in_finding": f.valid_pixels_in_finding,
            },
        })

    provenance: dict = {
        "oberon_version": oberon_version,
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

    if abstention_reason:
        provenance["abstention"] = {"reason": abstention_reason}

    return provenance


def write_provenance_manifest(provenance: dict, output_path: Path) -> Path:
    """Write the provenance manifest as pretty-printed JSON."""
    with open(output_path, "w") as f:
        json.dump(provenance, f, indent=2, default=str)
    return output_path


def _collect_software_versions(oberon_version: str) -> dict:
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
