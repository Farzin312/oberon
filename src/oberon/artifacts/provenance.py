"""Provenance manifest — a first-class record of how each finding was produced."""

from __future__ import annotations

import json
from pathlib import Path

from oberon.core import EvidenceBundle, Finding


def build_provenance(
    findings: list[Finding],
    bundle: EvidenceBundle,
    oberon_version: str = "0.1.0",
) -> dict:
    """Construct the provenance dictionary for a set of findings.

    This is product data, not logging. It records every detail needed
    to independently verify or reproduce a result.
    """
    raise NotImplementedError("requires provenance construction logic")


def write_provenance_manifest(provenance: dict, output_path: Path) -> Path:
    """Write the provenance manifest as pretty-printed JSON."""
    with open(output_path, "w") as f:
        json.dump(provenance, f, indent=2, default=str)
    return output_path
