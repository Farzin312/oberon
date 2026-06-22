"""True-color image composites and change overlays."""

from __future__ import annotations

from pathlib import Path

import numpy as np


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
    raise NotImplementedError("requires PIL or matplotlib for PNG generation")


def render_change_overlay(
    before_rgb: np.ndarray,
    change_mask: np.ndarray,
    output_path: Path,
) -> Path:
    """Overlay detected change regions (red highlight) on the before image.

    change_mask is a boolean array where True = detected change.
    """
    raise NotImplementedError("requires overlay compositing logic")
