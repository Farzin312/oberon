"""COG windowed reads — extract AOI-bounded raster windows from cloud-optimized GeoTIFFs."""

from __future__ import annotations

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


def read_window(
    scene: CandidateScene,
    aoi_geometry: dict,
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

    geom = shape(aoi_geometry)
    lon_min, lat_min, lon_max, lat_max = geom.bounds

    data: dict[str, np.ndarray] = {}
    crs: str = ""
    _transform: Affine | None = None
    last_window: Window | None = None

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
                scl_mask = (~np.isin(scl_data, list(SCL_CLOUD_BITS))) & (scl_data != 0)
        except RasterioIOError:
            pass  # SCL missing is non-fatal — caller falls back to nodata-only mask

    win_bounds = (
        windows.bounds(last_window, _transform)
        if last_window is not None
        else (0.0, 0.0, 0.0, 0.0)
    )

    return RasterWindow(
        data=data,
        crs=crs,
        transform=tuple(_transform) if _transform is not None else (),
        bounds=win_bounds,  # type: ignore[arg-type]
        scl_mask=scl_mask,
    )
