"""Change detection — thresholding, connected components, finding extraction."""

from __future__ import annotations

import numpy as np
from scipy import ndimage as ndi

from oberon.core import BaselineResult, Finding


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
    return np.abs(np.nan_to_num(diff_map, nan=0.0)) > threshold


def extract_findings(
    change_mask: np.ndarray,
    ndvi_diff: np.ndarray | None,
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
        score = 1.0
        if ndvi_diff is not None:
            mean_delta = float(np.nanmean(np.where(component, ndvi_diff, np.nan)))
            # ponytail: linear score normalized to [0, 1]; calibrate against
            # labeled examples when evaluation dataset exists.
            score = min(abs(mean_delta) / 0.5, 1.0)

            findings.append(
                Finding(
                    geometry=_component_to_geojson_polygon(labeled, i, component),
                    score=score,
                    area_ha=area_ha,
                    ndvi_delta_mean=mean_delta,
                    nbr_delta_mean=0.0,
                    valid_pixels_in_finding=pixel_count,
                )
            )

    return findings


def _component_to_geojson_polygon(
    labeled: np.ndarray,
    label_id: int,
    component: np.ndarray,
) -> dict:
    """Convert a connected component to a GeoJSON Polygon.

    ponytail: bounding-box polygon instead of exact concave hull.
    Switch to shapely `Polygon` with `convex_hull` for accurate boundaries.
    """
    rows, cols = np.where(component)
    min_row, max_row = int(rows.min()), int(rows.max())
    min_col, max_col = int(cols.min()), int(cols.max())

    # Returns a unit bbox polygon in pixel coordinates —
    # the caller must transform to geographic CRS.
    return {
        "type": "Polygon",
        "coordinates": [[
            [min_col, min_row],
            [max_col, min_row],
            [max_col, max_row],
            [min_col, max_row],
            [min_col, min_row],
        ]],
    }
