"""Tests for tiled inference — chipping and stitching.

Module: oberon/ai/tiled_inference.py
"""

from __future__ import annotations

import numpy as np

from oberon.ai.tiled_inference import compute_chip_grid, extract_chip, stitch_embeddings


class TestComputeChipGrid:
    """compute_chip_grid: grid origins for tiling."""

    def test_single_chip_for_small_area(self) -> None:
        """Area smaller than chip_size gets exactly 1 chip."""
        origins = compute_chip_grid(100, 100, chip_size=256)
        assert origins == [(0, 0)]

    def test_exact_fit_no_remainder(self) -> None:
        """Area exactly divisible by chip_size gets a clean grid."""
        origins = compute_chip_grid(512, 256, chip_size=256)
        assert len(origins) == 2
        assert (0, 0) in origins
        assert (256, 0) in origins

    def test_remainder_adds_extra_chips(self) -> None:
        """Area not divisible by chip_size gets extra chips for the edge."""
        origins = compute_chip_grid(300, 300, chip_size=256)
        assert len(origins) == 4  # 2x2 grid
        assert (0, 0) in origins
        assert (0, 256) in origins
        assert (256, 0) in origins
        assert (256, 256) in origins

    def test_empty_area_returns_empty(self) -> None:
        """Zero-size area returns empty list."""
        assert compute_chip_grid(0, 0) == []


class TestExtractChip:
    """extract_chip: extract a padded chip from a band dict."""

    def test_extract_from_interior(self) -> None:
        """Chip from interior extracts the correct region."""
        data = {"B04": np.arange(400).reshape(20, 20).astype(np.float32)}
        chip = extract_chip(data, top=0, left=0, chip_size=10)
        assert chip["B04"].shape == (10, 10)
        assert chip["B04"][0, 0] == 0
        assert chip["B04"][9, 9] == 189  # 9*20+9

    def test_extract_at_edge_pads(self) -> None:
        """Chip at edge that exceeds bounds is reflect-padded."""
        data = {"B04": np.arange(100).reshape(10, 10).astype(np.float32)}
        # Request chip starting at (5, 5) with size 10 — only 5x5 of real data
        chip = extract_chip(data, top=5, left=5, chip_size=10)
        assert chip["B04"].shape == (10, 10)
        # Top-left of chip is data[5,5] = 55
        assert chip["B04"][0, 0] == 55


class TestStitchEmbeddings:
    """stitch_embeddings: reconstruct spatial map from per-chip embeddings."""

    def test_stitch_chip_level_embeddings(self) -> None:
        """Chip-level (N, D) embeddings stitch to (H, W, D)."""
        # 2x1 grid covering 512x256 with chip_size=256
        origins = [(0, 0), (256, 0)]
        embeddings = np.array([[1.0, 2.0], [3.0, 4.0]], dtype=np.float32)
        result = stitch_embeddings(embeddings, origins, 512, 256, chip_size=256)

        assert result.shape == (512, 256, 2)
        # Top chip (rows 0-255) has embedding [1, 2]
        assert np.allclose(result[0, 0], [1.0, 2.0])
        # Bottom chip (rows 256-511) has embedding [3, 4]
        assert np.allclose(result[256, 0], [3.0, 4.0])

    def test_stitch_single_chip(self) -> None:
        """Single chip fills the entire area."""
        origins = [(0, 0)]
        embeddings = np.array([[5.0]], dtype=np.float32)
        result = stitch_embeddings(embeddings, origins, 100, 100, chip_size=256)

        assert result.shape == (100, 100, 1)
        assert np.allclose(result, 5.0)
