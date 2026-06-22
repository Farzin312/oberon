"""Tests for deterministic baseline computations.

Module: oberon/core/baselines.py

Each test class covers one behaviour of compute_baselines(). Every test
method has a docstring explaining what behaviour it validates. Small 4x4
numpy arrays are used to keep assertions readable.
"""

from __future__ import annotations

import numpy as np

from oberon.core import PreparedPair
from oberon.core.baselines import compute_baselines

# ---------------------------------------------------------------------------
# Shared fixture values for every PreparedPair built in these tests.
# ---------------------------------------------------------------------------

_CRS = "EPSG:32616"
_TRANSFORM = (10.0, 0.0, 0.0, 0.0, -10.0, 0.0)
_BOUNDS = (0.0, 0.0, 100.0, 100.0)


def _pair(before: dict, after: dict, mask: np.ndarray) -> PreparedPair:
    """Build a PreparedPair with the canonical test CRS/transform/bounds."""
    return PreparedPair(
        before=before,
        after=after,
        mask=mask,
        crs=_CRS,
        transform=_TRANSFORM,
        bounds=_BOUNDS,
    )


# ---------------------------------------------------------------------------
# compute_baselines
# ---------------------------------------------------------------------------

class TestComputeBaselines:
    """compute_baselines(): deterministic NDVI/NBR/NDMI diffs over a prepared pair."""

    def test_abstains_when_valid_fraction_below_threshold(self) -> None:
        """A mask with <30% valid pixels should return abstain=True and all diffs None."""
        # 4x4 = 16 pixels; 3 True -> 18.75% valid, below the 0.30 threshold.
        mask = np.array(
            [
                [True, True, True, False],
                [False, False, False, False],
                [False, False, False, False],
                [False, False, False, False],
            ],
            dtype=bool,
        )
        before = {
            "B04": np.ones((4, 4), dtype=np.float32),
            "B08": np.ones((4, 4), dtype=np.float32) * 2,
            "B11": np.ones((4, 4), dtype=np.float32) * 3,
            "B12": np.ones((4, 4), dtype=np.float32) * 4,
        }
        after = {
            "B04": np.ones((4, 4), dtype=np.float32) * 5,
            "B08": np.ones((4, 4), dtype=np.float32) * 6,
            "B11": np.ones((4, 4), dtype=np.float32) * 7,
            "B12": np.ones((4, 4), dtype=np.float32) * 8,
        }
        result = compute_baselines(_pair(before, after, mask))

        assert result.abstain is True
        assert result.ndvi_diff is None
        assert result.nbr_diff is None
        assert result.ndmi_diff is None

    def test_all_bands_present_computes_every_diff(self) -> None:
        """With B04/B08/B11/B12 present and a usable mask, all three diffs are non-None."""
        mask = np.ones((4, 4), dtype=bool)
        before = {
            "B04": np.full((4, 4), 100, dtype=np.float32),
            "B08": np.full((4, 4), 200, dtype=np.float32),
            "B11": np.full((4, 4), 150, dtype=np.float32),
            "B12": np.full((4, 4), 250, dtype=np.float32),
        }
        after = {
            "B04": np.full((4, 4), 120, dtype=np.float32),
            "B08": np.full((4, 4), 180, dtype=np.float32),
            "B11": np.full((4, 4), 140, dtype=np.float32),
            "B12": np.full((4, 4), 260, dtype=np.float32),
        }
        result = compute_baselines(_pair(before, after, mask))

        assert result.abstain is False
        assert result.ndvi_diff is not None
        assert result.nbr_diff is not None
        assert result.ndmi_diff is not None
        # shared "valid in both" mask -> before/after counts are equal
        assert result.valid_pixels_before == result.valid_pixels_after
        assert result.valid_pixels_before == int(mask.sum())

    def test_missing_swir_bands_drops_ndmi_and_nbr_only(self) -> None:
        """No B11/B12 -> ndmi_diff and nbr_diff are None but ndvi_diff still computes."""
        mask = np.ones((4, 4), dtype=bool)
        before = {
            "B04": np.full((4, 4), 100, dtype=np.float32),
            "B08": np.full((4, 4), 200, dtype=np.float32),
        }
        after = {
            "B04": np.full((4, 4), 150, dtype=np.float32),
            "B08": np.full((4, 4), 180, dtype=np.float32),
        }
        result = compute_baselines(_pair(before, after, mask))

        assert result.abstain is False
        assert result.ndvi_diff is not None
        assert result.ndmi_diff is None
        assert result.nbr_diff is None

    def test_all_zero_nir_red_yields_zero_ndvi_diff(self) -> None:
        """NIR=0 and Red=0 are guarded by an epsilon so ndvi_diff is finite and ~0.0."""
        mask = np.ones((4, 4), dtype=bool)
        before = {
            "B04": np.zeros((4, 4), dtype=np.float32),
            "B08": np.zeros((4, 4), dtype=np.float32),
        }
        after = {
            "B04": np.zeros((4, 4), dtype=np.float32),
            "B08": np.zeros((4, 4), dtype=np.float32),
        }
        result = compute_baselines(_pair(before, after, mask))

        assert result.abstain is False
        assert result.ndvi_diff is not None
        # epsilon guard turns 0/0 into 0/eps == 0 for both before and after -> diff ~0
        assert np.all(np.isfinite(result.ndvi_diff))
        assert np.allclose(result.ndvi_diff[mask], 0.0)

    def test_nir_saturated_near_red_yields_near_zero_ndvi_diff(self) -> None:
        """B08~10000 and Red~10000 -> NDVI ~0 for both windows, so diff ~0."""
        mask = np.ones((4, 4), dtype=bool)
        before = {
            "B04": np.full((4, 4), 9999, dtype=np.float32),
            "B08": np.full((4, 4), 10000, dtype=np.float32),
        }
        after = {
            "B04": np.full((4, 4), 9998, dtype=np.float32),
            "B08": np.full((4, 4), 10001, dtype=np.float32),
        }
        result = compute_baselines(_pair(before, after, mask))

        assert result.abstain is False
        assert result.ndvi_diff is not None
        assert np.allclose(result.ndvi_diff[mask], 0.0, atol=1e-3)

    def test_fully_masked_pair_abstains(self) -> None:
        """A mask with no valid pixels (0%) should return abstain=True."""
        mask = np.zeros((4, 4), dtype=bool)
        before = {
            "B04": np.ones((4, 4), dtype=np.float32),
            "B08": np.ones((4, 4), dtype=np.float32) * 2,
        }
        after = {
            "B04": np.ones((4, 4), dtype=np.float32) * 3,
            "B08": np.ones((4, 4), dtype=np.float32) * 4,
        }
        result = compute_baselines(_pair(before, after, mask))

        assert result.abstain is True
        assert result.ndvi_diff is None
