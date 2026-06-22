"""Image preparation — masking, reprojection, resampling, and alignment."""

from __future__ import annotations

import numpy as np
import rasterio
from affine import Affine

from oberon.core import PreparedPair, RasterWindow

TARGET_RESOLUTION_M = 10

# Sentinel-2 bands at 20m native resolution that need upsampling to 10m.
_20M_BANDS = frozenset({"B05", "B06", "B07", "B11", "B12", "B8A"})


def build_valid_mask(window: RasterWindow) -> tuple[np.ndarray, str | None]:
    """Build boolean valid-pixel mask from SCL classification and nodata.

    Returns (valid_mask, reason) where valid_mask is True for usable pixels
    and reason is a descriptive string when the entire AOI is obstructed,
    or None when the mask contains valid pixels.

    Combines SCL-based quality classification (cloud, shadow, snow -> invalid)
    with Sentinel-2 nodata (value 0). When SCL is unavailable, falls back to
    a nodata-only mask with a warning reason.
    """
    # Nothing to mask if no bands were read.
    if not window.data:
        return np.array([[]], dtype=bool).reshape(0, 0), "AOI fully obstructed — no bands available"

    # Pick any band as the reference for shape and nodata.
    ref_band = next(iter(window.data.values()))
    nodata_valid = ref_band != 0  # Sentinel-2 L2A uses 0 for nodata

    if window.scl_mask is not None:
        # SCL mask is already boolean (True = valid) from cog_reader.
        valid = window.scl_mask & nodata_valid
        reason: str | None = None
    else:
        # No SCL band available — degrade to nodata-only mask.
        valid = nodata_valid
        reason = "SCL band unavailable — using nodata-only mask"

    # Check for full obstruction.
    if not valid.any():
        reason = "AOI fully obstructed in selected scenes"

    return valid, reason


def _resolve_target_crs(
    before: RasterWindow,
    after: RasterWindow,
    target_crs: str | None,
) -> str:
    """Determine output CRS, defaulting to the before window's CRS."""
    if target_crs:
        return target_crs
    if before.crs:
        return before.crs
    if after.crs:
        return after.crs
    return "EPSG:4326"


def _reproject_band(
    band_data: np.ndarray,
    src_crs: str,
    src_transform: tuple[float, ...],
    dst_crs: str,
    dst_affine: Affine,
    dst_height: int,
    dst_width: int,
    resampling: rasterio.enums.Resampling = rasterio.enums.Resampling.bilinear,
) -> np.ndarray:
    """Reproject a single band array to the target CRS and grid."""
    if src_crs == dst_crs:
        # Same CRS — just match the target shape, no actual reprojection needed.
        if band_data.shape == (dst_height, dst_width):
            return band_data.astype(np.float32)
        # Different pixel grid within same CRS: resize via reproject.
        dst = np.zeros((dst_height, dst_width), dtype=np.float32)
        src_affine = Affine(*src_transform) if src_transform else dst_affine
        rasterio.warp.reproject(
            source=band_data,
            destination=dst,
            src_transform=src_affine,
            src_crs=src_crs,
            dst_transform=dst_affine,
            dst_crs=dst_crs,
            resampling=resampling,
        )
        return dst

    # Different CRS: reproject to target.
    dst = np.zeros((dst_height, dst_width), dtype=np.float32)
    src_affine = Affine(*src_transform) if src_transform else Affine(1.0, 0.0, 0.0, 0.0, -1.0, 0.0)
    rasterio.warp.reproject(
        source=band_data,
        destination=dst,
        src_transform=src_affine,
        src_crs=src_crs,
        dst_transform=dst_affine,
        dst_crs=dst_crs,
        resampling=resampling,
    )
    return dst


def align_to_common_grid(
    before: RasterWindow,
    after: RasterWindow,
    target_crs: str | None = None,
    target_resolution: float = TARGET_RESOLUTION_M,
) -> PreparedPair:
    """Reproject, resample, and crop before/after to a shared grid.

    Uses the CRS of the before window as default target. All output bands
    share the same shape and CRS. Returns a PreparedPair with a combined
    valid-pixel mask and dimension checks.

    ponytail: synchronous band-by-band reprojection. For production
    throughput, parallelise independent band reprojections with
    ThreadPoolExecutor, cache reprojected grids for repeated AOIs.
    """
    # 1. Build valid-pixel masks.
    before_mask, _ = build_valid_mask(before)
    after_mask, _ = build_valid_mask(after)

    # 2. Determine target CRS.
    out_crs = _resolve_target_crs(before, after, target_crs)

    # 3. Determine destination grid from intersection of window bounds.
    def _bounds_tuple(b: tuple[float, float, float, float]) -> tuple[float, ...] | None:
        return b if len(b) == 4 else None

    b_bounds = _bounds_tuple(before.bounds)
    a_bounds = _bounds_tuple(after.bounds)

    if b_bounds and a_bounds:
        # Project both bounds into the output CRS for intersection.
        b_minx, b_miny, b_maxx, b_maxy = b_bounds
        a_minx, a_miny, a_maxx, a_maxy = a_bounds

        if before.crs != out_crs:
            b_xs, b_ys = rasterio.warp.transform(before.crs, out_crs, [b_minx, b_maxx], [b_miny, b_maxy])
            b_minx, b_maxx = min(b_xs), max(b_xs)
            b_miny, b_maxy = min(b_ys), max(b_ys)
        if after.crs != out_crs:
            a_xs, a_ys = rasterio.warp.transform(after.crs, out_crs, [a_minx, a_maxx], [a_miny, a_maxy])
            a_minx, a_maxx = min(a_xs), max(a_xs)
            a_miny, a_maxy = min(a_ys), max(a_ys)

        inter_minx = max(b_minx, a_minx)
        inter_miny = max(b_miny, a_miny)
        inter_maxx = min(b_maxx, a_maxx)
        inter_maxy = min(b_maxy, a_maxy)

        if inter_minx >= inter_maxx or inter_miny >= inter_maxy:
            # No overlap — abstain.
            dst_affine = Affine(target_resolution, 0.0, 0.0, 0.0, -target_resolution, 0.0)
            return PreparedPair(
                before={}, after={},
                mask=np.array([[]], dtype=bool).reshape(0, 0),
                crs=out_crs, transform=(), bounds=(),
            )

        from rasterio.transform import from_bounds as transform_from_bounds
        dst_width = max(int(round((inter_maxx - inter_minx) / target_resolution)), 1)
        dst_height = max(int(round((inter_maxy - inter_miny) / target_resolution)), 1)
        dst_affine = transform_from_bounds(inter_minx, inter_miny, inter_maxx, inter_maxy, dst_width, dst_height)
    elif not before.data:
        return PreparedPair(
            before={}, after={},
            mask=np.array([[]], dtype=bool).reshape(0, 0),
            crs=out_crs, transform=(), bounds=(),
        )
    else:
        # Fallback: use before window's shape as-is (no geographic bounds available).
        ref_band = next(iter(before.data.values()))
        dst_height, dst_width = ref_band.shape
        dst_affine = Affine(*before.transform) if before.transform else Affine(
            target_resolution, 0.0, 0.0, 0.0, -target_resolution, 0.0,
        )

    # 4. Reproject each band.
    before_reproj: dict[str, np.ndarray] = {}
    after_reproj: dict[str, np.ndarray] = {}

    for band_name, band_data in before.data.items():
        is_scl = band_name in ("SCL",)
        resampling = rasterio.enums.Resampling.nearest if is_scl else rasterio.enums.Resampling.bilinear
        before_reproj[band_name] = _reproject_band(
            band_data, before.crs, before.transform,
            out_crs, dst_affine, dst_height, dst_width,
            resampling=resampling,
        )

    for band_name, band_data in after.data.items():
        is_scl = band_name in ("SCL",)
        resampling = rasterio.enums.Resampling.nearest if is_scl else rasterio.enums.Resampling.bilinear
        after_reproj[band_name] = _reproject_band(
            band_data, after.crs, after.transform,
            out_crs, dst_affine, dst_height, dst_width,
            resampling=resampling,
        )

    # 5. Reproject and combine the masks.
    mask_reproj = np.ones((dst_height, dst_width), dtype=bool)
    if before_mask.size > 0 and before_mask.shape != (dst_height, dst_width):
        before_mask_proj = _reproject_band(
            before_mask.astype(np.float32), before.crs, before.transform,
            out_crs, dst_affine, dst_height, dst_width,
            resampling=rasterio.enums.Resampling.nearest,
        )
        mask_reproj &= before_mask_proj > 0.5
    elif before_mask.size > 0:
        mask_reproj &= before_mask

    if after_mask.size > 0 and after_mask.shape != (dst_height, dst_width):
        after_mask_proj = _reproject_band(
            after_mask.astype(np.float32), after.crs, after.transform,
            out_crs, dst_affine, dst_height, dst_width,
            resampling=rasterio.enums.Resampling.nearest,
        )
        mask_reproj &= after_mask_proj > 0.5
    elif after_mask.size > 0:
        mask_reproj &= after_mask

    # 6. Crop to common intersecting shape.
    #    (Simplified: use the minimum height/width across all before/after bands.)
    min_h = min(
        *(arr.shape[0] for arr in before_reproj.values()),
        *(arr.shape[0] for arr in after_reproj.values()),
        dst_height,
    )
    min_w = min(
        *(arr.shape[1] for arr in before_reproj.values()),
        *(arr.shape[1] for arr in after_reproj.values()),
        dst_width,
    )

    if min_h < dst_height or min_w < dst_width:
        before_reproj = {k: v[:min_h, :min_w] for k, v in before_reproj.items()}
        after_reproj = {k: v[:min_h, :min_w] for k, v in after_reproj.items()}
        mask_reproj = mask_reproj[:min_h, :min_w]
        dst_height, dst_width = min_h, min_w

    # 7. Check dimension threshold (< 10px -> unusable).
    if dst_height < 10 or dst_width < 10:
        mask_reproj = np.zeros_like(mask_reproj)

    return PreparedPair(
        before=before_reproj,
        after=after_reproj,
        mask=mask_reproj,
        crs=out_crs,
        transform=tuple(dst_affine),
        bounds=(),
    )
