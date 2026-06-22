"""Artifact store — run-level index of pipeline output files with checksums.

Every pipeline run produces an artifact_index.json alongside the evidence
bundle. It records the run_id, timestamp, all artifact paths, and SHA-256
checksums for text artifacts (JSON/GeoJSON only — raster artifacts are too
large for checksumming).
"""

from __future__ import annotations

import hashlib
import json
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from oberon.core import EvidenceBundle

# Only checksum text artifacts. Raster outputs (PNG) are too large for
# per-run SHA-256 on every run. Record size+date for those.
_CHECKSUMMED_EXTENSIONS = {".json", ".geojson"}


def compute_sha256(file_path: Path) -> str:
    """Compute SHA-256 hex digest of a file."""
    h = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def _generate_run_id() -> str:
    """Generate a unique run ID: oberon-<timestamp>-<uuid8>."""
    ts = datetime.now(UTC).strftime("%Y%m%dT%H%M%S")
    short_id = uuid.uuid4().hex[:8]
    return f"oberon-{ts}-{short_id}"


def build_run_artifact_index(
    bundle: EvidenceBundle,
    output_dir: Path,
    run_id: str | None = None,
) -> dict[str, Any]:
    """Build the artifact index for a pipeline run.

    Returns a dict with: run_id, created_at, artifacts (paths), checksums,
    and file_sizes. Writes artifact_index.json to the output directory.

    Args:
        bundle: The EvidenceBundle from the pipeline run.
        output_dir: Directory where artifacts were written.
        run_id: Optional run ID override. Auto-generated if None.
    """
    if run_id is None:
        run_id = _generate_run_id()

    created_at = datetime.now(UTC).isoformat()

    # Collect artifact paths from the bundle.
    artifact_paths: dict[str, str] = {
        "before_image": str(bundle.before_image.name) if bundle.before_image else "",
        "after_image": str(bundle.after_image.name) if bundle.after_image else "",
        "overlay_image": str(bundle.overlay_image.name) if bundle.overlay_image else "",
        "findings_geojson": str(bundle.findings_geojson.name) if bundle.findings_geojson else "",
        "provenance": str(bundle.provenance_manifest.name) if bundle.provenance_manifest else "",
    }

    # Compute checksums for text artifacts only.
    checksums: dict[str, str] = {}
    file_sizes: dict[str, int] = {}

    for name, rel_path in artifact_paths.items():
        if not rel_path:
            continue
        full_path = output_dir / rel_path
        if not full_path.exists():
            continue
        file_sizes[name] = full_path.stat().st_size
        if full_path.suffix in _CHECKSUMMED_EXTENSIONS:
            checksums[name] = f"sha256:{compute_sha256(full_path)}"

    index: dict[str, Any] = {
        "run_id": run_id,
        "created_at": created_at,
        "artifacts": artifact_paths,
        "checksums": checksums,
        "file_sizes": file_sizes,
    }

    # Write the index file.
    index_path = output_dir / "artifact_index.json"
    with open(index_path, "w") as f:
        json.dump(index, f, indent=2)

    return index
