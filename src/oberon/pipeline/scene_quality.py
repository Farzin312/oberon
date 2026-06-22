"""Scene quality assessment — local valid-pixel fraction over the AOI.

Phase 1 provides the function signature and documentation. The full AOI-local
quality computation requires the COG reader (Phase 2) to read the SCL band
over the AOI window. Until then, scene-level cloud percentage from
`stac_discovery.rank_by_scene_quality` serves as the quality proxy.

ponytail: full SCL-based local quality is deferred to Phase 2 (COG reader).
"""

from __future__ import annotations

import numpy as np

from oberon.core import SCL_CLOUD_BITS, CandidateScene


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

    Requires reading the SCL band from the scene's COG. This function is
    the bridge between the STAC discovery layer and the COG reader.

    ponytail: stub returning scene-level cloud % as a proxy. Replace with
    actual SCL windowed read when the COG reader exists (Phase 2).
    """
    # ponytail: Phase 1 — scene-level proxy only.
    # Full implementation: read_scl_window() -> compute_local_valid_fraction()
    return (100.0 - scene.scene_cloud_pct) / 100.0
