"""Deterministic baseline computations — NDVI, NBR, NDMI, pixel deltas."""

from __future__ import annotations

import numpy as np

from oberon.core import BaselineResult, PreparedPair

# Small epsilon to avoid division by zero.
_EPSILON = np.finfo(np.float32).eps


def compute_ndvi(nir: np.ndarray, red: np.ndarray) -> np.ndarray:
    """Normalized Difference Vegetation Index: (NIR - R) / (NIR + R)."""
    denom = nir + red
    denom = np.where(np.abs(denom) < _EPSILON, _EPSILON, denom)
    return (nir - red) / denom


def compute_nbr(nir: np.ndarray, swir2: np.ndarray) -> np.ndarray:
    """Normalized Burn Ratio: (NIR - SWIR2) / (NIR + SWIR2)."""
    denom = nir + swir2
    denom = np.where(np.abs(denom) < _EPSILON, _EPSILON, denom)
    return (nir - swir2) / denom


def compute_ndmi(nir: np.ndarray, swir1: np.ndarray) -> np.ndarray:
    """Normalized Difference Moisture Index: (NIR - SWIR1) / (NIR + SWIR1)."""
    denom = nir + swir1
    denom = np.where(np.abs(denom) < _EPSILON, _EPSILON, denom)
    return (nir - swir1) / denom


def compute_pixel_delta(before: np.ndarray, after: np.ndarray) -> np.ndarray:
    """Per-band magnitude of pixel-level change (Euclidean across all bands)."""
    return np.sqrt(((after - before) ** 2).sum(axis=-1)) if before.ndim == 3 else np.abs(after - before)


def compute_baselines(pair: PreparedPair) -> BaselineResult:
    """Compute all deterministic baselines from a prepared before/after pair.

    Applies the valid-pixel mask so that invalid pixels are excluded
    from all calculations.
    """
    # All baselines use the same "before" NIR (B08) and Red (B04) bands.
    nir_before = pair.before.get("B08")
    red_before = pair.before.get("B04")
    nir_after = pair.after.get("B08")
    red_after = pair.after.get("B04")

    if any(a is None for a in (nir_before, red_before, nir_after, red_after)):
        return BaselineResult(
            ndvi_diff=None,
            nbr_diff=None,
            ndmi_diff=None,
            pixel_delta_magnitude=None,
            valid_pixels_before=0,
            valid_pixels_after=0,
            abstain=True,
            abstain_reason="Missing required bands (B04, B08)",
        )

    ndvi_before = compute_ndvi(nir_before, red_before)
    ndvi_after = compute_ndvi(nir_after, red_after)

    ndvi_diff = np.where(pair.mask, ndvi_after - ndvi_before, np.nan)

    nbr_diff = None
    if "B12" in pair.before and "B12" in pair.after:
        nbr_before = compute_nbr(nir_before, pair.before["B12"])
        nbr_after = compute_nbr(nir_after, pair.after["B12"])
        nbr_diff = np.where(pair.mask, nbr_after - nbr_before, np.nan)

    ndmi_diff = None
    if "B11" in pair.before and "B11" in pair.after:
        ndmi_before = compute_ndmi(nir_before, pair.before["B11"])
        ndmi_after = compute_ndmi(nir_after, pair.after["B11"])
        ndmi_diff = np.where(pair.mask, ndmi_after - ndmi_before, np.nan)

    valid_before = int(pair.mask.sum())
    valid_after = int(pair.mask.sum())

    # Abstention check: insufficient valid pixels
    total = pair.mask.size
    valid_frac_before = valid_before / total if total > 0 else 0
    if valid_frac_before < 0.3:
        return BaselineResult(
            ndvi_diff=None,
            nbr_diff=None,
            ndmi_diff=None,
            pixel_delta_magnitude=None,
            valid_pixels_before=valid_before,
            valid_pixels_after=valid_after,
            abstain=True,
            abstain_reason=f"Insufficient valid pixels: {valid_frac_before:.1%}",
        )

    return BaselineResult(
        ndvi_diff=ndvi_diff,
        nbr_diff=nbr_diff,
        ndmi_diff=ndmi_diff,
        pixel_delta_magnitude=None,  # requires all-bands stacked
        valid_pixels_before=valid_before,
        valid_pixels_after=valid_after,
    )
