"""Pipeline orchestration — runs stages in order, handles abstention."""

from __future__ import annotations

from pathlib import Path

from oberon.artifacts import build_evidence_bundle
from oberon.core import ChangeRequest, EvidenceBundle
from oberon.core.baselines import compute_baselines
from oberon.core.change_detection import (
    deduplicate_and_rank,
    extract_findings,
    threshold_change_map,
)
from oberon.pipeline import (
    align_to_common_grid,
    build_composite,
    rank_by_scene_quality,
    read_window,
    search_catalog,
)

# Sentinel-2 bands needed for the vegetation-change pipeline.
_BANDS_RGB = ["B04", "B03", "B02"]
_BANDS_NDVI = ["B08", "B04"]
_BANDS_NBR = ["B12"]
_BANDS_NDMI = ["B11"]
REQUIRED_BANDS = sorted(set(_BANDS_RGB + _BANDS_NDVI + _BANDS_NBR + _BANDS_NDMI))

# When the best single scene's valid-pixel fraction is below this, build a
# composite from the top candidates instead. Roadmap correction #2.
COMPOSITE_THRESHOLD = 0.7

# Max scenes to merge in a composite.
_MAX_COMPOSITE_SCENES = 3


def run_analysis(
    request: ChangeRequest,
    output_dir: Path,
    *,
    force_composite: bool = False,
) -> EvidenceBundle:
    """Run the full analysis pipeline for a change request.

    Calls each pipeline stage in order. If any stage returns abstention,
    the pipeline stops early and returns an abstention result containing
    the reason and any partial provenance.

    When force_composite is True, or when the best single scene's
    valid-pixel fraction falls below COMPOSITE_THRESHOLD, the pipeline
    builds a cloud-masked median composite from the top candidate scenes
    for that period instead of using a single observation.
    """
    # ----- Phase 1: STAC discovery + scene quality -----
    try:
        candidates = search_catalog(request)
    except ConnectionError as exc:
        return _abstention_result(str(exc), output_dir)

    scenes = rank_by_scene_quality(
        candidates,
        before_window=request.before,
        after_window=request.after,
        max_cloud_pct=request.max_cloud_fraction * 100.0,
    )

    if not scenes:
        return _abstention_result("No suitable scenes found for AOI and date range", output_dir)

    # ----- Phase 2: COG reading + preparation -----
    # Decide composite vs single-scene per period.
    before_scenes = [s for s in scenes if s.period == "before"][:_MAX_COMPOSITE_SCENES]
    after_scenes = [s for s in scenes if s.period == "after"][:_MAX_COMPOSITE_SCENES]

    if not before_scenes:
        return _abstention_result("No suitable before scene found", output_dir)
    if not after_scenes:
        return _abstention_result("No suitable after scene found", output_dir)

    use_composite_before = force_composite or before_scenes[0].local_valid_fraction < COMPOSITE_THRESHOLD
    use_composite_after = force_composite or after_scenes[0].local_valid_fraction < COMPOSITE_THRESHOLD

    try:
        if use_composite_before and len(before_scenes) > 1:
            windows = [read_window(s.candidate, request.geometry, REQUIRED_BANDS) for s in before_scenes]
            before_window = build_composite(windows)
        else:
            before_window = read_window(before_scenes[0].candidate, request.geometry, REQUIRED_BANDS)
    except FileNotFoundError as exc:
        return _abstention_result(f"Before COG read failed: {exc}", output_dir)

    try:
        if use_composite_after and len(after_scenes) > 1:
            windows = [read_window(s.candidate, request.geometry, REQUIRED_BANDS) for s in after_scenes]
            after_window = build_composite(windows)
        else:
            after_window = read_window(after_scenes[0].candidate, request.geometry, REQUIRED_BANDS)
    except FileNotFoundError as exc:
        return _abstention_result(f"After COG read failed: {exc}", output_dir)

    pair = align_to_common_grid(before_window, after_window)
    if not pair.is_usable:
        fraction = pair.valid_fraction
        return _abstention_result(
            f"Insufficient valid pixels: {fraction:.0%} "
            f"(requires >= {request.min_valid_pixels:.0%})",
            output_dir,
        )

    # ----- Phase 3: Baselines + change detection -----
    baseline = compute_baselines(pair)
    if baseline.abstain:
        reason = baseline.abstain_reason or "Baseline abstention — no valid signal"
        return _abstention_result(reason, output_dir)

    change_mask = threshold_change_map(baseline.ndvi_diff)
    if change_mask is None:
        return _abstention_result("Could not compute change mask from NDVI difference", output_dir)

    raw_findings = extract_findings(
        change_mask,
        baseline.ndvi_diff,
        min_pixels=max(1, int(request.min_change_area_ha / 0.01)),  # 1px = 0.01ha at 10m
    )
    findings = deduplicate_and_rank(raw_findings)

    # ----- Phase 4: Evidence bundles -----
    # Record source scene metadata for provenance.
    source_info: dict[str, object] = {
        "before_source_type": "composite" if (use_composite_before and len(before_scenes) > 1) else "single",
        "after_source_type": "composite" if (use_composite_after and len(after_scenes) > 1) else "single",
        "before_source_scenes": [s.candidate.stac_item_id for s in before_scenes],
        "after_source_scenes": [s.candidate.stac_item_id for s in after_scenes],
    }
    if use_composite_before and len(before_scenes) > 1:
        source_info["before_composite_method"] = "median"
    if use_composite_after and len(after_scenes) > 1:
        source_info["after_composite_method"] = "median"

    bundle = build_evidence_bundle(findings, pair, output_dir, source_info=source_info)

    return bundle


def _abstention_result(reason: str, output_dir: Path) -> EvidenceBundle:
    """Build an abstention evidence bundle with the given reason."""
    import numpy as np

    from oberon.core import PreparedPair

    # Minimal empty pair so build_evidence_bundle has something to work with.
    empty_pair = PreparedPair(
        before={}, after={},
        mask=np.array([[False]], dtype=bool),
        crs="EPSG:4326",
        transform=(),
        bounds=(0.0, 0.0, 0.0, 0.0),
    )
    return build_evidence_bundle([], empty_pair, output_dir, abstention_reason=reason)
