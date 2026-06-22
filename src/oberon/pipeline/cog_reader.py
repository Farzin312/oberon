"""COG windowed reads — extract AOI-bounded raster windows from cloud-optimized GeoTIFFs."""

from __future__ import annotations

from typing import Any

import numpy as np
import rasterio
from affine import Affine
from rasterio import warp, windows
from rasterio.errors import RasterioIOError
from rasterio.windows import Window
from shapely.geometry import shape

from oberon.core import SCL_CLOUD_BITS, CandidateScene, RasterWindow

# WGS84 — the CRS of GeoJSON coordinates and STAC bboxes.
_GEO_CRS = "EPSG:4326"

# Session-level COG cache. Keyed by (scene_id, band, AOI geometry hash).
# In-memory only — no disk persistence. Clears when the process exits.
# Set via enable_cache() / disable_cache().
_cache_enabled: bool = False
_cache: dict[str, RasterWindow] = {}


def enable_cache() -> None:
    """Enable session-level COG window caching."""
    global _cache_enabled
    _cache_enabled = True


def disable_cache() -> None:
    """Disable session-level COG window caching and clear stored entries."""
    global _cache_enabled, _cache
    _cache_enabled = False
    _cache.clear()


def clear_cache() -> None:
    """Clear the cache without disabling it."""
    _cache.clear()


def get_cache_size() -> int:
    """Return the number of cached entries."""
    return len(_cache)


def _cache_key(scene: CandidateScene, aoi_geometry: dict[str, Any], bands: list[str]) -> str:
    """Build a deterministic cache key for (scene, AOI, bands)."""
    import hashlib
    import json

    geom_str = json.dumps(aoi_geometry, sort_keys=True)
    bands_str = ",".join(sorted(bands))
    raw = f"{scene.stac_item_id}|{bands_str}|{geom_str}"
    return hashlib.sha256(raw.encode()).hexdigest()


def read_window(
    scene: CandidateScene,
    aoi_geometry: dict[str, Any],
    bands: list[str],
    buffer_pixels: int = 1,
) -> RasterWindow:
    """Read a windowed subset of the COG overlapping the AOI.

    Only the required bands are fetched, and only the portion of each
    band that intersects the AOI bounding box (plus a small buffer).

    Raises FileNotFoundError if the COG URL is unreachable (404/403).
    Silently skips bands absent from scene.assets.

    ponytail: single-threaded synchronous reads. Parallel band reads via
    ThreadPoolExecutor for latency-sensitive applications.
    """
    if not bands:
        raise ValueError("At least one band must be requested")

    # Check session cache.
    if _cache_enabled:
        key = _cache_key(scene, aoi_geometry, bands)
        if key in _cache:
            return _cache[key]

    geom = shape(aoi_geometry)
    lon_min, lat_min, lon_max, lat_max = geom.bounds

    data: dict[str, np.ndarray] = {}
    crs: str = ""
    _transform: Affine | None = None
    last_window: Window | None = None

    # Reference grid for resolution harmonization. Sentinel-2 bands have
    # mixed resolutions (10m for B02/B03/B04/B08, 20m for B05/B06/B07/B8A/B11/B12).
    # We must resample all bands to a common grid so they can be stacked together.
    ref_height: int | None = None
    ref_width: int | None = None
    ref_transform: Affine | None = None

    for band in bands:
        if band not in scene.assets:
            continue

        url = scene.assets[band]
        try:
            with rasterio.open(url) as src:
                if not crs:
                    crs = str(src.crs)
                    _transform = src.transform

                # Transform AOI bbox from geographic coords to the COG's native CRS.
                xs, ys = warp.transform(
                    _GEO_CRS,
                    src.crs,
                    [lon_min, lon_max],
                    [lat_min, lat_max],
                )
                x_min, x_max = min(xs), max(xs)
                y_min, y_max = min(ys), max(ys)

                win = windows.from_bounds(
                    x_min, y_min, x_max, y_max,
                    transform=src.transform,
                )

                if buffer_pixels > 0:
                    win = Window(
                        col_off=win.col_off - buffer_pixels,
                        row_off=win.row_off - buffer_pixels,
                        width=win.width + 2 * buffer_pixels,
                        height=win.height + 2 * buffer_pixels,
                    )

                last_window = win
                band_data = src.read(1, window=win)

                # Capture reference grid from the first band read.
                if ref_height is None:
                    ref_height = band_data.shape[0]
                    ref_width = band_data.shape[1]
                    ref_transform = src.transform
                elif band_data.shape[0] != ref_height or band_data.shape[1] != ref_width:
                    # This band is at a different native resolution (e.g. 20m
                    # vs 10m reference). Resample to the reference grid.
                    assert ref_height is not None and ref_width is not None
                    resampled = np.zeros((ref_height, ref_width), dtype=band_data.dtype)
                    rasterio.warp.reproject(
                        source=band_data,
                        destination=resampled,
                        src_transform=src.transform,
                        src_crs=src.crs,
                        dst_transform=ref_transform or src.transform,
                        dst_crs=src.crs,
                        resampling=rasterio.enums.Resampling.bilinear,
                    )
                    band_data = resampled

                data[band] = band_data
        except RasterioIOError as exc:
            raise FileNotFoundError(
                f"COG read failed for scene {scene.stac_item_id}: {band}"
            ) from exc

    # Read SCL band if available — build valid-pixel mask (True = valid).
    scl_mask: np.ndarray | None = None
    if scene.scl_url:
        try:
            with rasterio.open(scene.scl_url) as src:
                if not crs:
                    crs = str(src.crs)
                    _transform = src.transform

                xs, ys = warp.transform(
                    _GEO_CRS,
                    src.crs,
                    [lon_min, lon_max],
                    [lat_min, lat_max],
                )
                x_min, x_max = min(xs), max(xs)
                y_min, y_max = min(ys), max(ys)

                scl_win = windows.from_bounds(
                    x_min, y_min, x_max, y_max,
                    transform=src.transform,
                )

                if buffer_pixels > 0:
                    scl_win = Window(
                        col_off=scl_win.col_off - buffer_pixels,
                        row_off=scl_win.row_off - buffer_pixels,
                        width=scl_win.width + 2 * buffer_pixels,
                        height=scl_win.height + 2 * buffer_pixels,
                    )

                scl_data = src.read(1, window=scl_win)

                # Resample SCL to reference grid if needed.
                if (
                    ref_height is not None
                    and ref_width is not None
                    and (scl_data.shape[0] != ref_height or scl_data.shape[1] != ref_width)
                ):
                    resampled_scl = np.zeros((ref_height, ref_width), dtype=scl_data.dtype)
                    rasterio.warp.reproject(
                        source=scl_data,
                        destination=resampled_scl,
                        src_transform=src.transform,
                        src_crs=src.crs,
                        dst_transform=ref_transform or src.transform,
                        dst_crs=src.crs,
                        resampling=rasterio.enums.Resampling.nearest,
                    )
                    scl_data = resampled_scl

                scl_mask = (~np.isin(scl_data, list(SCL_CLOUD_BITS))) & (scl_data != 0)
        except RasterioIOError:
            pass  # SCL missing is non-fatal — caller falls back to nodata-only mask

    win_bounds = (
        windows.bounds(last_window, _transform)
        if last_window is not None
        else (0.0, 0.0, 0.0, 0.0)
    )

    result = RasterWindow(
        data=data,
        crs=crs,
        transform=tuple(_transform) if _transform is not None else (),
        bounds=win_bounds,
        scl_mask=scl_mask,
    )

    # Store in session cache.
    if _cache_enabled:
        key = _cache_key(scene, aoi_geometry, bands)
        _cache[key] = result

    return result
