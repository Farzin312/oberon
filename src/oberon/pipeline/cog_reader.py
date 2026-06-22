"""COG windowed reads — extract AOI-bounded raster windows from cloud-optimized GeoTIFFs."""

from __future__ import annotations

from oberon.core import CandidateScene, RasterWindow


def read_window(
    scene: CandidateScene,
    aoi_geometry: dict,
    bands: list[str],
    buffer_pixels: int = 1,
) -> RasterWindow:
    """Read a windowed subset of the COG overlapping the AOI.

    Only the required bands are fetched, and only the portion of each
    band that intersects the AOI bounding box (plus a small buffer).

    ponytail: single-threaded synchronous reads. Parallel band reads via
    ThreadPoolExecutor for latency-sensitive applications.
    """
    raise NotImplementedError("requires Rasterio windowed read implementation")
