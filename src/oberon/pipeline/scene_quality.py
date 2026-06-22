"""Scene quality assessment — local valid-pixel fraction over the AOI.

Phase 1 provided the function signature and documentation. Phase 2 upgrades
assess_scene to read the SCL band from the scene's COG when available,
computing local valid-pixel fraction over the AOI window instead of using
the scene-level cloud-percentage proxy.
"""

from __future__ import annotations

import numpy as np
import rasterio
from rasterio.errors import RasterioIOError
from rasterio.warp import transform as warp_transform
from rasterio.windows import from_bounds as window_from_bounds
from shapely.geometry import shape

from oberon.core import SCL_CLOUD_BITS, CandidateScene

# WGS84 — the CRS of GeoJSON coordinates and STAC bboxes.
_GEO_CRS = "EPSG:4326"


def compute_local_valid_fraction(
    scl_window: np.ndarray,
    cloud_bits: set[int] | None = None,
) -> float:
    """Compute fraction of valid (non-obstructed) pixels from an SCL raster window.

    The SCL (Scene Classification Layer) contains per-pixel labels. Pixels
    matching any value in *cloud_bits* are considered invalid. Returns a
    float in [0.0, 1.0].

    .. code-block:: python

        scl = read_scl_window(scene, aoi_geometry)
        fraction = compute_local_valid_fraction(scl)
        # fraction = 0.85  means 85% of pixels are clear

    ponytail: simple set-membership mask. Per-class weighted scoring or
    buffered cloud-shadow dilation for stricter quality filtering.
    """
    if cloud_bits is None:
        cloud_bits = SCL_CLOUD_BITS

    total = scl_window.size
    if total == 0:
        return 0.0

    invalid = np.isin(scl_window, list(cloud_bits))
    return float((~invalid).sum() / total)


def assess_scene(scene: CandidateScene, aoi_geometry: dict) -> float:
    """Assess the local valid-pixel quality of a scene over the AOI.

    Reads the SCL band from the scene's COG and computes the valid-pixel
    fraction over the AOI window. Falls back to scene-level cloud percentage
    when SCL is unavailable or the read fails.

    ponytail: single-threaded synchronous SCL read. Band-level parallel
    prefetch with ThreadPoolExecutor for latency-sensitive applications.
    """
    if scene.scl_url:
        try:
            geom = shape(aoi_geometry)
            lon_min, lat_min, lon_max, lat_max = geom.bounds

            with rasterio.open(scene.scl_url) as src:
                xs, ys = warp_transform(
                    _GEO_CRS, src.crs,
                    [lon_min, lon_max], [lat_min, lat_max],
                )
                x_min, x_max = min(xs), max(xs)
                y_min, y_max = min(ys), max(ys)

                win = window_from_bounds(
                    x_min, y_min, x_max, y_max,
                    transform=src.transform,
                )
                scl_data = src.read(1, window=win)

                if scl_data.size > 0:
                    return compute_local_valid_fraction(scl_data)
        except RasterioIOError:
            pass  # SCL missing is non-fatal — fall back to proxy
        except Exception:
            pass  # Any other error (e.g. invalid geometry) — degrade gracefully

    # Fallback: scene-level cloud percentage proxy
    return (100.0 - scene.scene_cloud_pct) / 100.0
