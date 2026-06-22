"""Image preparation — masking, reprojection, resampling, and alignment."""

from __future__ import annotations

from oberon.core import PreparedPair, RasterWindow


TARGET_RESOLUTION_M = 10


def build_valid_mask(window: RasterWindow) -> tuple:
    """Build boolean valid-pixel mask from SCL classification data.

    Returns (valid_mask, invalid_reason) where valid_mask is True for
    clear/valid pixels and invalid_reason is populated if the entire
    window is invalid.
    """
    raise NotImplementedError("requires SCL mask construction logic")


def align_to_common_grid(
    before: RasterWindow,
    after: RasterWindow,
    target_crs: str | None = None,
    target_resolution: float = TARGET_RESOLUTION_M,
) -> PreparedPair:
    """Reproject, resample, and crop before/after to a shared grid.

    Uses the CRS and grid of the 'before' window as default target.
    Returns a PreparedPair with all band arrays and the intersection mask.
    """
    raise NotImplementedError("requires reprojection + resampling logic")
