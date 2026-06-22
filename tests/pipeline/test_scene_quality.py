"""Tests for scene quality assessment module.

Module: oberon/pipeline/scene_quality.py

Covers local valid-pixel fraction computation from SCL arrays and the
scene-assessment bridge. Full AOI-local quality via windowed COG reads
is implemented in Phase 2; Phase 1 tests validate the pure-function
SCL analysis and the interface contract.
"""

from __future__ import annotations

from datetime import datetime

import numpy as np

from oberon.core import CandidateScene
from oberon.pipeline.scene_quality import assess_scene, compute_local_valid_fraction

# ---------------------------------------------------------------------------
# compute_local_valid_fraction
# ---------------------------------------------------------------------------

class TestComputeLocalValidFraction:
    """compute_local_valid_fraction(): compute valid-pixel fraction from SCL array."""

    def test_all_clear_returns_1(self):
        """An SCL array with no cloud/shadow pixels should return 1.0 (fully valid)."""
        scl = np.full((10, 10), 4, dtype=np.uint8)  # SCL value 4 = vegetation
        fraction = compute_local_valid_fraction(scl)
        assert fraction == 1.0

    def test_all_cloud_returns_0(self):
        """An SCL array where every pixel is cloud should return 0.0."""
        scl = np.full((10, 10), 8, dtype=np.uint8)  # SCL value 8 = medium-probability cloud
        fraction = compute_local_valid_fraction(scl)
        assert fraction == 0.0

    def test_half_clear_half_cloud_returns_05(self):
        """A 50/50 mix of clear and cloud pixels should return 0.5."""
        scl = np.full((100, 100), 8, dtype=np.uint8)  # all cloud
        scl[:50, :] = 4  # top half = vegetation (valid)
        fraction = compute_local_valid_fraction(scl)
        assert fraction == 0.5

    def test_cloud_shadow_and_snow_all_invalid(self):
        """SCL values for saturated (1), shadow (3), cirrus (10), and snow (11) should all count as invalid."""
        scl = np.array([
            [1, 3],   # saturated, shadow
            [10, 11], # cirrus, snow
        ], dtype=np.uint8)
        fraction = compute_local_valid_fraction(scl)
        assert fraction == 0.0

    def test_empty_array_returns_0(self):
        """An empty SCL array (no pixels) should return 0.0 without crashing."""
        scl = np.array([], dtype=np.uint8)
        fraction = compute_local_valid_fraction(scl)
        assert fraction == 0.0

    def test_custom_cloud_bits(self):
        """Passing a custom cloud_bits set should use those values instead of defaults."""
        scl = np.full((5, 5), 4, dtype=np.uint8)  # vegetation
        # Treat value 4 (vegetation) as invalid
        fraction = compute_local_valid_fraction(scl, cloud_bits={4})
        assert fraction == 0.0

    def test_no_nan_handling_required(self):
        """SCL is integer-typed; the function should work with uint8 inputs without float coercion issues."""
        scl = np.array([[2, 4], [6, 8]], dtype=np.uint8)
        fraction = compute_local_valid_fraction(scl)
        # Values 2 (dark area pixels), 4 (vegetation), 6 (water) are valid
        # Value 8 (cloud) is invalid
        assert fraction == 0.75


# ---------------------------------------------------------------------------
# assess_scene
# ---------------------------------------------------------------------------

class TestAssessScene:
    """assess_scene(): bridge between STAC discovery and quality assessment."""

    def test_returns_derived_quality_from_cloud_pct(self):
        """The Phase 1 stub should return (100 - cloud_pct) / 100 as a proxy quality score."""
        scene = CandidateScene(
            "test", datetime.now(), {}, (0, 0, 1, 1), {}, None, 25.0,
        )
        quality = assess_scene(scene, {})
        assert quality == 0.75  # (100 - 25) / 100

    def test_clear_scene_returns_near_1(self):
        """A scene with 2% cloud should return a quality near 1.0."""
        scene = CandidateScene(
            "clear-scene", datetime.now(), {}, (0, 0, 1, 1), {}, None, 2.0,
        )
        quality = assess_scene(scene, {})
        assert quality == 0.98

    def test_fully_cloudy_scene_returns_0(self):
        """A scene with 100% cloud should return quality of 0.0."""
        scene = CandidateScene(
            "fully-cloudy", datetime.now(), {}, (0, 0, 1, 1), {}, None, 100.0,
        )
        quality = assess_scene(scene, {})
        assert quality == 0.0
