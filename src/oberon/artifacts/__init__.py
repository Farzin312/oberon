"""Artifact generation — images, GeoJSON, and provenance manifests."""

from __future__ import annotations

from pathlib import Path

import numpy as np

from oberon.core import EvidenceBundle, Finding, PreparedPair

from .geojson import write_findings_geojson
from .images import render_change_overlay, render_true_color
from .provenance import build_provenance, write_provenance_manifest


def create_output_dir(path: Path) -> Path:
    """Create the output directory if it doesn't exist and return it."""
    path.mkdir(parents=True, exist_ok=True)
    return path


def build_evidence_bundle(
    findings: list[Finding],
    pair: PreparedPair,
    output_dir: Path,
    abstention_reason: str | None = None,
) -> EvidenceBundle:
    """Build all evidence artifacts (images, GeoJSON, provenance) into output_dir.

    Renders before/after true-color PNGs, a change overlay, a findings GeoJSON
    file, and a provenance manifest. Returns the EvidenceBundle with all paths.

    ponytail: full-AOI rendering. Upgrade path: tile rendering for very large
    areas (>1000x1000 px) to avoid memory pressure.
    """
    output_dir = create_output_dir(output_dir)

    before_path = output_dir / "before.png"
    after_path = output_dir / "after.png"
    overlay_path = output_dir / "overlay.png"
    findings_path = output_dir / "findings.geojson"
    provenance_path = output_dir / "provenance.json"

    # Render before/after true-color if RGB bands are available.
    b_bands = pair.before
    a_bands = pair.after

    has_rgb_before = all(b in b_bands for b in ("B04", "B03", "B02"))
    has_rgb_after = all(b in a_bands for b in ("B04", "B03", "B02"))

    if has_rgb_before:
        render_true_color(b_bands["B04"], b_bands["B03"], b_bands["B02"], before_path)
    if has_rgb_after:
        render_true_color(a_bands["B04"], a_bands["B03"], a_bands["B02"], after_path)

    # Overlay: need a before RGB image and the change mask.
    if has_rgb_before:
        before_rgb_8bit = _stack_true_color_8bit(b_bands["B04"], b_bands["B03"], b_bands["B02"])
        # Build a change mask from finding geometries (or use the pair mask
        # as fallback if no findings — shows full AOI as highlighted).
        from oberon.core.baselines import compute_baselines
        from oberon.core.change_detection import threshold_change_map

        baseline = compute_baselines(pair)
        raw_mask = threshold_change_map(baseline.ndvi_diff) if baseline.ndvi_diff is not None else np.ones(pair.mask.shape, dtype=bool)
        change_mask = raw_mask if raw_mask is not None else np.ones(pair.mask.shape, dtype=bool)

        render_change_overlay(before_rgb_8bit, change_mask, overlay_path)

    # GeoJSON findings.
    write_findings_geojson(findings, findings_path)

    # Provenance manifest.
    bundle = EvidenceBundle(
        output_dir=output_dir,
        before_image=before_path if has_rgb_before else before_path,
        after_image=after_path if has_rgb_after else after_path,
        overlay_image=overlay_path if has_rgb_before else overlay_path,
        findings_geojson=findings_path,
        provenance_manifest=provenance_path,
        provenance={},
    )
    provenance = build_provenance(findings, bundle, abstention_reason=abstention_reason)
    bundle.provenance = provenance
    write_provenance_manifest(provenance, provenance_path)

    return bundle


def _stack_true_color_8bit(red: np.ndarray, green: np.ndarray, blue: np.ndarray) -> np.ndarray:
    """Stack three uint16 bands into an (H, W, 3) uint8 array with percent clip."""

    from .images import _percent_clip

    return np.stack([
        _percent_clip(red),
        _percent_clip(green),
        _percent_clip(blue),
    ], axis=-1)
