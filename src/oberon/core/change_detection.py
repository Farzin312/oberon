"""Change detection — thresholding, connected components, finding extraction."""

from __future__ import annotations

from typing import Any, cast

import numpy as np
from scipy import ndimage as ndi
from shapely.geometry import MultiPoint, mapping

from oberon.core import Finding, PreparedPair

# Default threshold: |NDVI change| > 0.15 is considered significant.
_DEFAULT_NDVI_THRESHOLD = 0.15

# Minimum contiguous pixels for a finding (~50 pixels at 10m = 0.5 ha).
_MIN_CHANGE_PIXELS = 50

# Pixel area at 10m resolution (ha per pixel).
_PIXEL_AREA_HA = 0.01


def threshold_change_map(
    diff_map: np.ndarray | None,
    threshold: float = _DEFAULT_NDVI_THRESHOLD,
) -> np.ndarray | None:
    """Apply signed threshold to a difference map.

    Returns a boolean mask where |diff| > threshold.
    """
    if diff_map is None:
        return None
    return np.asarray(np.abs(np.nan_to_num(diff_map, nan=0.0)) > threshold)


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
    threshold: float = _DEFAULT_NDVI_THRESHOLD,
    min_pixels: int = _MIN_CHANGE_PIXELS,
) -> list[Finding]:
    """Thin orchestrator: baseline -> threshold -> extract -> rank.

    Abstains (returns []) when the pair is not usable, the baseline abstained,
    or no NDVI difference could be computed.
    """
    # Local import avoids a module-load cycle with baselines.
    from oberon.core.baselines import compute_baselines

    baseline = compute_baselines(pair)
    if not pair.is_usable or baseline.abstain or baseline.ndvi_diff is None:
        return []
    change_mask = threshold_change_map(baseline.ndvi_diff, threshold)
    findings = extract_findings(
        cast(np.ndarray, change_mask),
        baseline.ndvi_diff,
        pixel_delta=baseline.pixel_delta_magnitude,
        min_pixels=min_pixels,
    )
    return deduplicate_and_rank(findings)
