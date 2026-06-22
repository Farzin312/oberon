"""True-color image composites and change overlays."""

from __future__ import annotations

from pathlib import Path

import numpy as np
from PIL import Image


def render_true_color(
    red: np.ndarray,
    green: np.ndarray,
    blue: np.ndarray,
    output_path: Path,
) -> Path:
    """Write a true-color PNG composite from R/G/B bands.

    Bands are expected in the native Sentinel-2 uint16 range (0-10000).
    Output is an 8-bit PNG with linear percent clip (2%-98%).

    ponytail: simple linear stretch. Consider histogram equalization or
    multi-band fusion for visual quality in varying illumination.
    """
    stacked = np.stack([_percent_clip(red), _percent_clip(green), _percent_clip(blue)], axis=-1)
    img = Image.fromarray(stacked.astype(np.uint8), mode="RGB")
    img.save(output_path, format="PNG")
    return output_path


def render_change_overlay(
    before_rgb: np.ndarray,
    change_mask: np.ndarray,
    output_path: Path,
) -> Path:
    """Overlay detected change regions (red highlight) on the before image.

    before_rgb is an (H, W, 3) uint8 array.
    change_mask is a boolean array where True = detected change.
    """
    rgba = np.dstack([before_rgb, np.full(before_rgb.shape[:2], 255, dtype=np.uint8)]).copy()
    # Red tint on changed pixels: blend original with semi-transparent red.
    rgba[change_mask, 0] = np.minimum(
        rgba[change_mask, 0].astype(np.int32) + 150, 255
    ).astype(np.uint8)
    rgba[change_mask, 1] = (rgba[change_mask, 1].astype(np.int32) * 3 // 10).astype(np.uint8)
    rgba[change_mask, 2] = (rgba[change_mask, 2].astype(np.int32) * 3 // 10).astype(np.uint8)

    # Flatten alpha onto white background so output is RGB (no alpha channel).
    alpha = rgba[:, :, 3:4].astype(np.float32) / 255.0
    white = np.full_like(rgba[:, :, :3], 255, dtype=np.float32)
    rgb_flat = rgba[:, :, :3].astype(np.float32) * alpha + white * (1 - alpha)
    rgb_out = np.clip(rgb_flat, 0, 255).astype(np.uint8)

    img = Image.fromarray(rgb_out, mode="RGB")
    img.save(output_path, format="PNG")
    return output_path


def _percent_clip(band: np.ndarray, low: float = 2.0, high: float = 98.0) -> np.ndarray:
    """Clip a uint16 band to 8-bit using percentile-based linear stretch."""
    band_f = band.astype(np.float64)
    lo = float(np.percentile(band_f, low))
    hi = float(np.percentile(band_f, high))
    if hi - lo < 1.0:
        # Uniform band: map to 0 if all-dark, 255 if all-bright.
        if lo <= 0.0:
            return np.zeros(band.shape, dtype=np.uint8)
        lo = 0.0
        hi = max(lo, 1.0)
    scaled = (band_f - lo) / (hi - lo) * 255.0
    return np.clip(scaled, 0, 255).astype(np.uint8)
