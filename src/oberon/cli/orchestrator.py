"""Pipeline orchestration — runs stages in order, handles abstention."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np

from oberon.artifacts import build_evidence_bundle
from oberon.core import ChangeRequest, EvidenceBundle, PreparedPair
from oberon.core.baselines import compute_baselines
from oberon.core.change_detection import (
    NDVI_THRESHOLD,
    apply_morphological_closing,
    compute_change_spatial_variance,
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


def _is_cross_season(request: ChangeRequest) -> bool:
    """Check if before/after windows span different phenological seasons.

    Heuristic: windows whose start months are 4+ months apart are likely
    cross-season (e.g. summer to winter, spring to fall).
    """
    before_month = request.before[0].month
    after_month = request.after[0].month
    return abs(after_month - before_month) >= 4


def run_analysis(
    request: ChangeRequest,
    output_dir: Path,
    *,
    force_composite: bool = False,
    use_ai: bool = False,
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
        aoi_geometry=request.geometry,
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
        reason = (
            f"Insufficient valid pixels: {fraction:.0%} "
            f"(requires >= {request.min_valid_pixels:.0%})"
        )
        if _is_cross_season(request):
            reason = f"seasonal: {reason}"
        return _abstention_result(reason, output_dir)

    # ----- Phase 3: Baselines + change detection -----
    baseline = compute_baselines(pair)
    if baseline.abstain:
        reason = baseline.abstain_reason or "Baseline abstention — no valid signal"
        if _is_cross_season(request) and baseline.ndvi_diff is None:
            reason = f"seasonal: {reason}"
        return _abstention_result(reason, output_dir)

    ndvi_diff = baseline.ndvi_diff
    if ndvi_diff is None:
        return _abstention_result("Could not compute NDVI difference", output_dir)

    # Step 3a: Task-direction-aware signed threshold.
    # vegetation_disturbance only flags NDVI loss (negative diff).
    direction = "negative" if request.task == "vegetation_disturbance" else "absolute"
    change_mask = threshold_change_map(ndvi_diff, direction=direction)
    if change_mask is None or not change_mask.any():
        return _abstention_result(
            f"No significant change detected ({direction} direction)", output_dir,
        )

    # Step 3b: Morphological closing to consolidate fragmented findings.
    change_mask = apply_morphological_closing(change_mask)

    # Step 3c: Spatial-variance seasonal detection (014).
    # Distinguishes uniform seasonal senescence from patchy real disturbance.
    # Abstains only when BOTH: uniform (low CV) AND broad (>50% coverage).
    seasonal_risk = False
    seasonal_assessment = compute_change_spatial_variance(change_mask, ndvi_diff, pair.mask)
    if seasonal_assessment is not None:
        if seasonal_assessment.should_abstain:
            return _abstention_result(
                f"Seasonal pattern: uniform NDVI loss "
                f"(CV={seasonal_assessment.cv:.2f}, "
                f"coverage={seasonal_assessment.coverage:.0%})",
                output_dir,
            )
        seasonal_risk = seasonal_assessment.is_uniform

    # Step 3d: Extract + rank findings.
    raw_findings = extract_findings(
        change_mask,
        ndvi_diff,
        min_pixels=max(1, int(request.min_change_area_ha / 0.01)),
    )
    findings = deduplicate_and_rank(raw_findings)

    # ----- Phase 3b: Optional AI branch (parallel to baseline) -----
    model_versions: list[str] = ["deterministic-v1"]
    ai_info: dict[str, object] | None = None
    if use_ai:
        ai_info = _run_ai_branch(pair)
        if ai_info and not ai_info.get("abstain", True):
            model_versions.append("clay-v1.5")

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

    if ai_info is not None:
        source_info["ai"] = ai_info

    processing_config: dict[str, Any] = {
            "task": request.task,
            "threshold_direction": direction,
            "ndvi_threshold": NDVI_THRESHOLD,
            "closing_kernel_size": 25,
        }
    if seasonal_risk and seasonal_assessment is not None:
        processing_config["seasonal_risk"] = True
        processing_config["spatial_cv"] = round(seasonal_assessment.cv, 4)
        processing_config["change_coverage"] = round(seasonal_assessment.coverage, 4)

    bundle = build_evidence_bundle(
        findings, pair, output_dir,
        source_info=source_info,
        model_versions=model_versions,
        processing_config=processing_config,
    )

    # ----- Phase 5: Artifact index -----
    from oberon.store.artifact_index import build_run_artifact_index

    build_run_artifact_index(bundle, output_dir)

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


def _run_ai_branch(pair: PreparedPair) -> dict[str, object] | None:
    """Run the Clay AI branch if torch is available.

    Returns a dict with adapter_version, model_version, chip_count, and
    abstention info. Returns None if torch is not installed (graceful skip).
    """
    try:
        import numpy as np

        from oberon.ai.clay_adapter import ClayAdapter
        from oberon.ai.clay_config import CLAY_BANDS, CLAY_CHIP_SIZE
        from oberon.ai.tiled_inference import compute_chip_grid, extract_chip, stitch_embeddings
    except ImportError:
        return {"abstain": True, "abstain_reason": "torch or clay not installed"}

    # Check all required bands are present.
    missing = [b for b in CLAY_BANDS if b not in pair.before or b not in pair.after]
    if missing:
        return {"abstain": True, "abstain_reason": f"Missing bands for Clay: {missing}"}

    try:
        adapter = ClayAdapter(device="cpu")

        # Determine chip grid.
        ref_shape = next(iter(pair.before.values())).shape
        origins = compute_chip_grid(ref_shape[0], ref_shape[1], CLAY_CHIP_SIZE)

        before_embeddings: list[np.ndarray] = []
        after_embeddings: list[np.ndarray] = []

        for top, left in origins:
            before_chip = extract_chip(pair.before, top, left, CLAY_CHIP_SIZE)
            after_chip = extract_chip(pair.after, top, left, CLAY_CHIP_SIZE)

            # Stack bands into (H, W, B) array in CLAY_BANDS order.
            before_stack = np.stack([before_chip[b] for b in CLAY_BANDS], axis=-1)
            after_stack = np.stack([after_chip[b] for b in CLAY_BANDS], axis=-1)

            before_feat = adapter.extract_features(before_stack, {"month": 6})
            after_feat = adapter.extract_features(after_stack, {"month": 6})

            before_embeddings.append(before_feat)
            after_embeddings.append(after_feat)

        # Compute per-chip feature diffs, then stitch.
        diffs = np.array([
            adapter.compute_feature_diff(b, a)
            for b, a in zip(before_embeddings, after_embeddings, strict=True)
        ])

        diff_map = stitch_embeddings(
            diffs.reshape(-1, 1), origins,
            ref_shape[0], ref_shape[1], CLAY_CHIP_SIZE,
            patch_grid=int(np.sqrt(before_embeddings[0].shape[0])),
        )[:, :, 0]

        score_map = ClayAdapter.normalize_diff_map(diff_map)

        return {
            "adapter_version": adapter.version,
            "model_version": "clay-v1.5-large",
            "chip_count": len(origins),
            "change_score_mean": float(np.nanmean(score_map)),
            "change_score_max": float(np.nanmax(score_map)),
            "abstain": False,
        }
    except Exception as exc:
        return {"abstain": True, "abstain_reason": f"Clay inference failed: {exc}"}
