"""Change detection — thresholding, connected components, finding extraction."""

from __future__ import annotations

from typing import Any, cast

import numpy as np
from scipy import ndimage as ndi
from shapely.geometry import MultiPoint, mapping

from oberon.core import Finding, PreparedPair, SeasonalAssessment

# Default threshold: |NDVI change| > 0.15 is considered significant.
NDVI_THRESHOLD = 0.15

# Minimum contiguous pixels for a finding (~50 pixels at 10m = 0.5 ha).
_MIN_CHANGE_PIXELS = 50

# Pixel area at 10m resolution (ha per pixel).
_PIXEL_AREA_HA = 0.01

# Task-to-direction mapping for signed thresholding.
# vegetation_disturbance only flags NDVI loss (negative diff).
_TASK_DIRECTIONS: dict[str, str] = {
    "vegetation_disturbance": "negative",
}


def _direction_for_task(task: str) -> str:
    """Return the threshold direction for a given task name.

    Unknown tasks fall back to "absolute" (backwards compatible).
    """
    return _TASK_DIRECTIONS.get(task, "absolute")


# Thresholds for spatial-variance seasonal detection (014).
# CV < 0.3 = uniform change (likely seasonal senescence).
# Coverage > 0.5 = broad change (majority of AOI).
# Abstain only when BOTH: uniform AND broad.
_SEASONAL_CV_THRESHOLD = 0.3
_SEASONAL_COVERAGE_THRESHOLD = 0.5
_MIN_PIXELS_FOR_VARIANCE = 50


def compute_change_spatial_variance(
    change_mask: np.ndarray,
    ndvi_diff: np.ndarray,
    valid_mask: np.ndarray,
) -> SeasonalAssessment | None:
    """Assess whether a change mask represents seasonal vs real disturbance.

    Seasonal senescence produces uniform NDVI loss (low spatial variance,
    low coefficient of variation). Real disturbance (fire, clearing) produces
    patchy, concentrated change (high CV).

    Returns None if there are too few changed pixels (<50) for reliable
    statistics.
    """
    changed = change_mask & valid_mask
    n_changed = int(np.count_nonzero(changed))
    if n_changed < _MIN_PIXELS_FOR_VARIANCE:
        return None

    changed_values = ndvi_diff[changed]
    mean_loss = float(np.mean(changed_values))
    std_loss = float(np.std(changed_values))

    cv = std_loss / abs(mean_loss) if abs(mean_loss) > 1e-6 else 0.0

    total_valid = int(np.count_nonzero(valid_mask))
    coverage = n_changed / total_valid if total_valid > 0 else 0.0

    is_uniform = cv < _SEASONAL_CV_THRESHOLD
    should_abstain = is_uniform and coverage > _SEASONAL_COVERAGE_THRESHOLD

    return SeasonalAssessment(
        cv=cv,
        coverage=coverage,
        is_uniform=is_uniform,
        should_abstain=should_abstain,
    )


def apply_morphological_closing(
    change_mask: np.ndarray,
    kernel_size: int = 25,
) -> np.ndarray:
    """Apply binary closing to merge nearby fragmented change regions.

    Uses a square structuring element of `kernel_size` x `kernel_size`
    to fill small gaps within a single disturbance event (fire scars,
    clearcuts) that may have been fragmented by noise or mixed pixels.

    Default 25x25 (250m at 10m resolution) merges fragments within a
    typical disturbance event while keeping genuinely separate events
    (>500m apart) distinct. Tuned from integration tests: 15x15 reduced
    finding counts but not enough for tight expected ranges (1-5).
    """
    from scipy import ndimage as ndi

    structure = np.ones((kernel_size, kernel_size), dtype=bool)
    result = ndi.binary_closing(change_mask, structure=structure)
    return cast(np.ndarray, result)


def threshold_change_map(
    diff_map: np.ndarray | None,
    threshold: float = NDVI_THRESHOLD,
    direction: str = "absolute",
) -> np.ndarray | None:
    """Apply directional or absolute threshold to a difference map.

    Args:
        diff_map: NDVI (or other index) difference array.
        threshold: Pixels with |diff| > threshold (absolute mode) or
                   diff < -threshold (negative mode, for vegetation loss)
                   or diff > threshold (positive mode, for vegetation gain)
                   are flagged as change.
        direction: One of "absolute" (both directions, backwards compat),
                   "negative" (only decreases — vegetation_disturbance),
                   "positive" (only increases — future recovery task).

    Returns:
        Boolean mask of same shape as diff_map, or None if input is None.
    """
    if diff_map is None:
        return None
    diff = np.nan_to_num(diff_map, nan=0.0)
    if direction == "negative":
        return np.asarray(diff < -threshold)
    if direction == "positive":
        return np.asarray(diff > threshold)
    # Default: "absolute" — backwards compatible.
    return np.asarray(np.abs(diff) > threshold)


def extract_findings(
    change_mask: np.ndarray,
    ndvi_diff: np.ndarray | None,
    pixel_delta: np.ndarray | None = None,
    min_pixels: int = _MIN_CHANGE_PIXELS,
    pixel_area_ha: float = _PIXEL_AREA_HA,
) -> list[Finding]:
    """Extract connected-component findings from a binary change mask.

    ponytail: single-scale connected components. Multi-scale or
    watershed segmentation if findings frequently straddle boundaries.
    """
    labeled, num_features = ndi.label(change_mask)

    findings: list[Finding] = []
    for i in range(1, num_features + 1):
        component = labeled == i
        pixel_count = int(component.sum())
        if pixel_count < min_pixels:
            continue

        area_ha = pixel_count * pixel_area_ha
        # Approximate score from the component's mean NDVI delta
        score = 0.0
        mean_delta = 0.0
        if ndvi_diff is not None:
            mean_delta = float(np.nanmean(np.where(component, ndvi_diff, np.nan)))
            ndvi_score = min(abs(mean_delta) / 0.5, 1.0)
        else:
            ndvi_score = 0.0

        delta_mean = 0.0
        if pixel_delta is not None:
            delta_mean = float(np.nanmean(np.where(component, pixel_delta, np.nan)))
        delta_score = min(delta_mean / 5000.0, 1.0)

        # NDVI stays primary; pixel_delta is secondary at 0.3 weight.
        score = max(ndvi_score, delta_score * 0.3)

        findings.append(
            Finding(
                geometry=_component_to_geojson_polygon(component),
                score=score,
                area_ha=area_ha,
                ndvi_delta_mean=mean_delta,
                nbr_delta_mean=0.0,
                valid_pixels_in_finding=pixel_count,
                pixel_delta_mean=delta_mean,
            )
        )

    return findings


def _component_to_geojson_polygon(component: np.ndarray) -> dict[str, Any]:
    """Convert a connected component to a GeoJSON Polygon.

    Builds a convex hull around the component's pixel coordinates. Falls back
    to an axis-aligned bbox when the hull is degenerate (collinear or single
    pixel — shapely then returns a LineString or Point, not a Polygon).

    ponytail: convex hull, not concave hull or exact footprint. Degenerate
    fallback to bbox; upgrade path: buffer degenerate hulls by half a pixel
    so all components yield a true Polygon.
    """
    rows, cols = np.nonzero(component)
    min_row, max_row = int(rows.min()), int(rows.max())
    min_col, max_col = int(cols.min()), int(cols.max())

    bbox = {
        "type": "Polygon",
        "coordinates": [[
            [min_col, min_row],
            [max_col, min_row],
            [max_col, max_row],
            [min_col, max_row],
            [min_col, min_row],
        ]],
    }

    points = list(zip(cols.tolist(), rows.tolist(), strict=True))
    hull = MultiPoint(points).convex_hull
    if hull.geom_type != "Polygon":
        # Degenerate hull (LineString / Point for collinear / single-pixel comps).
        return bbox
    geom: dict[str, Any] = cast(dict[str, Any], mapping(hull))
    if geom.get("type") != "Polygon":
        return bbox
    return geom


def deduplicate_and_rank(
    findings: list[Finding],
    max_findings: int = 20,
) -> list[Finding]:
    """Filter, sort, and cap findings.

    Drops findings with score <= 0.0 (including all-zero inputs -> empty),
    sorts the remainder by score descending, and caps to max_findings.
    Does not mutate the input list or its objects.

    ponytail: no geometric IoU dedup yet; ceiling is overlapping neighbours
    within a tolerance; upgrade path: pairwise shapely intersection-over-union.
    """
    if not findings:
        return []
    kept = [f for f in findings if f.score > 0.0]
    # Avoid mutating the caller's input list order.
    ranked = sorted(kept, key=lambda f: f.score, reverse=True)
    return ranked[:max_findings]


def detect_changes(
    pair: PreparedPair,
    threshold: float = NDVI_THRESHOLD,
    min_pixels: int = _MIN_CHANGE_PIXELS,
    task: str = "vegetation_disturbance",
) -> list[Finding]:
    """Thin orchestrator: baseline -> threshold -> extract -> rank.

    Uses task-aware directional thresholding so that
    vegetation_disturbance only detects NDVI loss (negative diff),
    not seasonal green-up.

    Abstains (returns []) when the pair is not usable, the baseline abstained,
    or no NDVI difference could be computed.
    """
    # Local import avoids a module-load cycle with baselines.
    from oberon.core.baselines import compute_baselines

    baseline = compute_baselines(pair)
    if not pair.is_usable or baseline.abstain or baseline.ndvi_diff is None:
        return []
    direction = _direction_for_task(task)
    change_mask = threshold_change_map(baseline.ndvi_diff, threshold, direction=direction)
    findings = extract_findings(
        cast(np.ndarray, change_mask),
        baseline.ndvi_diff,
        pixel_delta=baseline.pixel_delta_magnitude,
        min_pixels=min_pixels,
    )
    return deduplicate_and_rank(findings)
