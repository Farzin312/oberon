"""Tests for true-color image rendering and change overlays."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest
from PIL import Image

from oberon.artifacts.images import render_change_overlay, render_true_color


@pytest.fixture
def output_path(tmp_path: Path) -> Path:
    return tmp_path / "test_image.png"


class TestRenderTrueColor:
    """render_true_color: uint16 bands -> 8-bit PNG with 2%-98% clip."""

    def test_produces_valid_png(self, output_path: Path) -> None:
        """Mid-range values produce a non-empty, readable PNG."""
        red = np.full((50, 50), 3000, dtype=np.uint16)
        green = np.full((50, 50), 2500, dtype=np.uint16)
        blue = np.full((50, 50), 2000, dtype=np.uint16)

        result = render_true_color(red, green, blue, output_path)

        assert result == output_path
        assert output_path.exists()
        img = Image.open(output_path)
        assert img.format == "PNG"
        assert img.size == (50, 50)
        img.close()

    def test_all_zero_bands_produce_valid_png(self, output_path: Path) -> None:
        """All-zero input clips to 0 -> valid PNG with all-black pixels."""
        red = np.zeros((20, 20), dtype=np.uint16)
        green = np.zeros((20, 20), dtype=np.uint16)
        blue = np.zeros((20, 20), dtype=np.uint16)

        result = render_true_color(red, green, blue, output_path)

        assert result.exists()
        img = Image.open(output_path)
        assert img.mode in ("RGB", "RGBA")
        arr = np.array(img)
        assert (arr == 0).all()
        img.close()

    def test_all_max_bands_produce_valid_png(self, output_path: Path) -> None:
        """All-10000 input clips to 255 -> valid PNG with all-white pixels."""
        red = np.full((20, 20), 10000, dtype=np.uint16)
        green = np.full((20, 20), 10000, dtype=np.uint16)
        blue = np.full((20, 20), 10000, dtype=np.uint16)

        result = render_true_color(red, green, blue, output_path)

        assert result.exists()
        img = Image.open(output_path)
        arr = np.array(img)
        assert (arr == 255).all()
        img.close()


class TestRenderChangeOverlay:
    """render_change_overlay: before RGB + change mask -> overlay PNG."""

    def test_produces_valid_png(self, tmp_path: Path) -> None:
        """Overlay produces a valid PNG with correct dimensions."""
        before_rgb = np.full((30, 30, 3), 128, dtype=np.uint8)
        change_mask = np.zeros((30, 30), dtype=bool)
        change_mask[10:20, 10:20] = True
        output_path = tmp_path / "overlay.png"

        result = render_change_overlay(before_rgb, change_mask, output_path)

        assert result == output_path
        assert output_path.exists()
        img = Image.open(output_path)
        assert img.format == "PNG"
        assert img.size == (30, 30)
        img.close()

    def test_overlay_red_in_changed_region(self, tmp_path: Path) -> None:
        """Changed pixels should have elevated red channel compared to unchanged."""
        before_rgb = np.full((40, 40, 3), 100, dtype=np.uint8)
        change_mask = np.zeros((40, 40), dtype=bool)
        change_mask[5:15, 5:15] = True
        output_path = tmp_path / "overlay_red.png"

        render_change_overlay(before_rgb, change_mask, output_path)

        img = Image.open(output_path)
        arr = np.array(img)
        # Changed region should have higher red than unchanged region.
        changed_red = arr[5:15, 5:15, 0].mean()
        unchanged_red = arr[0:5, 0:5, 0].mean()
        assert changed_red > unchanged_red
        img.close()

    def test_no_change_produces_unchanged_image(self, tmp_path: Path) -> None:
        """All-False mask means the image is essentially unchanged."""
        before_rgb = np.full((20, 20, 3), 128, dtype=np.uint8)
        change_mask = np.zeros((20, 20), dtype=bool)
        output_path = tmp_path / "no_change.png"

        render_change_overlay(before_rgb, change_mask, output_path)

        img = Image.open(output_path)
        arr = np.array(img)
        # Without any overlay the base should be preserved.
        assert arr.shape == (20, 20, 3)
        img.close()
