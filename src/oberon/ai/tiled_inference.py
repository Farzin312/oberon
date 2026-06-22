"""Tiled inference — chip AOI into grids, batch, stitch results.

Handles the spatial decomposition needed because Clay operates on fixed
256x256 chips while AOIs can be any size.

ponytail: simple grid chipping with reflect-padding at edges, no feathered
overlap yet. For small AOIs (< 256px), a single chip suffices.
"""

from __future__ import annotations

import numpy as np


def compute_chip_grid(
    height: int,
    width: int,
    chip_size: int = 256,
) -> list[tuple[int, int]]:
    """Compute (row, col) origins for a grid of chips covering (height, width).

    Returns a list of (top, left) pixel coordinates. The grid is laid out
    so that chips tile the entire area. Edges that don't fill a full chip
    are handled by reflect-padding at inference time.
    """
    if height <= 0 or width <= 0:
        return []

    rows = (height + chip_size - 1) // chip_size
    cols = (width + chip_size - 1) // chip_size

    origins: list[tuple[int, int]] = []
    for r in range(rows):
        for c in range(cols):
            top = r * chip_size
            left = c * chip_size
            origins.append((top, left))
    return origins


def extract_chip(
    data: dict[str, np.ndarray],
    top: int,
    left: int,
    chip_size: int = 256,
) -> dict[str, np.ndarray]:
    """Extract a single chip from a band dict, reflect-padding at edges.

    Returns a dict with the same band names, each (chip_size, chip_size).
    """
    h, w = next(iter(data.values())).shape
    padded: dict[str, np.ndarray] = {}
    for band_name, arr in data.items():
        # Pad the array to ensure (top+chip_size, left+chip_size) is valid.
        pad_bottom = max(0, top + chip_size - h)
        pad_right = max(0, left + chip_size - w)
        if pad_bottom > 0 or pad_right > 0:
            arr = np.pad(
                arr,
                ((0, pad_bottom), (0, pad_right)),
                mode="reflect",
            )
        padded[band_name] = arr[top:top + chip_size, left:left + chip_size]
    return padded


def stitch_embeddings(
    embeddings: np.ndarray,  # (N_chips, D) or (N_chips, P, D)
    origins: list[tuple[int, int]],
    height: int,
    width: int,
    chip_size: int = 256,
    patch_grid: int | None = None,
) -> np.ndarray:
    """Stitch per-chip embeddings back into a spatial map.

    If embeddings are (N_chips, D): returns (H, W, D) — each pixel gets
    its chip's embedding vector (nearest-chip assignment).

    If embeddings are (N_chips, P, D) where P is a patch grid: returns
    (H, W, D) with each patch block filled from the corresponding patch.

    ponytail: nearest-chip assignment, no feathered blending. Upgrade
    path: weighted average at chip boundaries.
    """
    if embeddings.ndim == 2:
        # (N_chips, D) — fill each chip region with its embedding.
        d = embeddings.shape[1]
        result = np.zeros((height, width, d), dtype=np.float32)
        for i, (top, left) in enumerate(origins):
            bottom = min(top + chip_size, height)
            right = min(left + chip_size, width)
            result[top:bottom, left:right] = embeddings[i]
        return result

    # (N_chips, P, D) — patch-level stitching.
    if patch_grid is None:
        patch_grid = int(np.sqrt(embeddings.shape[1]))
    d = embeddings.shape[2]
    patch_size = chip_size // patch_grid
    result = np.zeros((height, width, d), dtype=np.float32)
    for i, (top, left) in enumerate(origins):
        for pr in range(patch_grid):
            for pc in range(patch_grid):
                ptop = top + pr * patch_size
                pleft = left + pc * patch_size
                pbottom = min(ptop + patch_size, height)
                pright = min(pleft + patch_size, width)
                patch_idx = pr * patch_grid + pc
                result[ptop:pbottom, pleft:pright] = embeddings[i, patch_idx]
    return result
