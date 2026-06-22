"""Tests for image preparation — masking, reprojection, resampling, and alignment.

Module: oberon/pipeline/preparation.py

Covers build_valid_mask (SCL + nodata mask construction) and
align_to_common_grid (reprojection, resampling, cropping).
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from oberon.core import PreparedPair, RasterWindow
from oberon.pipeline.preparation import align_to_common_grid, build_valid_mask

# ---------------------------------------------------------------------------
# build_valid_mask
# ---------------------------------------------------------------------------


class TestBuildValidMask:
    """build_valid_mask(): construct boolean valid-pixel mask from SCL + nodata."""

    def test_combines_scl_and_nodata(self):
        """Valid mask should be True only where SCL says valid AND band data != 0."""
        scl = np.array([
            [True, True, False, False],
            [True, True, False, False],
        ])
        data = np.array([
            [5000, 5000, 5000, 5000],
            [5000,    0, 5000,    0],
        ], dtype=np.uint16)
        window = RasterWindow(
            data={"B04": data},
            crs="EPSG:32616",
            transform=(),
            bounds=(),
            scl_mask=scl,
        )

        mask, reason = build_valid_mask(window)

        # Both conditions true
        assert mask[0, 0]
        assert mask[0, 1]
        # SCL says invalid
        assert not mask[0, 2]
        assert not mask[0, 3]
        # Nodata in band
        assert mask[1, 0]       # SCL=True, 5000 != 0
        assert not mask[1, 1]   # SCL=True, data=0 -> nodata
        # Both conditions false
        assert not mask[1, 2]   # SCL=False
        assert not mask[1, 3]   # SCL=False, data=0
        assert reason is None

    def test_missing_scl_falls_back_to_nodata(self):
        """When scl_mask is None, only band nodata (0) is checked and a warning reason is returned."""
        data = np.array([
            [5000, 5000, 0],
            [5000, 0,    0],
        ], dtype=np.uint16)
        window = RasterWindow(
            data={"B04": data},
            crs="EPSG:32616",
            transform=(),
            bounds=(),
            scl_mask=None,
        )

        mask, reason = build_valid_mask(window)

        assert mask[0, 0]
        assert mask[0, 1]
        assert not mask[0, 2]  # nodata
        assert mask[1, 0]
        assert not mask[1, 1]  # nodata
        assert not mask[1, 2]  # nodata
        assert reason is not None
        assert "SCL" in reason

    def test_all_pixels_obstructed_by_scl_returns_reason(self):
        """When every pixel is masked by SCL, returns all-False mask with 'AOI fully obstructed'."""
        scl = np.zeros((3, 4), dtype=bool)  # all False = all invalid
        data = np.full((3, 4), 5000, dtype=np.uint16)
        window = RasterWindow(
            data={"B04": data},
            crs="EPSG:32616",
            transform=(),
            bounds=(),
            scl_mask=scl,
        )

        mask, reason = build_valid_mask(window)

        assert not mask.any()
        assert "obstructed" in reason.lower()

    def test_all_pixels_obstructed_by_nodata_returns_reason(self):
        """When every pixel is nodata (0), returns all-False mask with obstruction reason."""
        data = np.zeros((4, 5), dtype=np.uint16)
        window = RasterWindow(
            data={"B04": data},
            crs="EPSG:32616",
            transform=(),
            bounds=(),
            scl_mask=np.ones((4, 5), dtype=bool),  # SCL says all valid
        )

        mask, reason = build_valid_mask(window)

        assert not mask.any()
        assert "obstructed" in reason.lower()

    def test_all_valid_returns_mask_all_true_and_no_reason(self):
        """When SCL is all True and no band is nodata, mask should be all True with no reason."""
        window = RasterWindow(
            data={"B04": np.full((5, 5), 5000, dtype=np.uint16)},
            crs="EPSG:32616",
            transform=(),
            bounds=(),
            scl_mask=np.ones((5, 5), dtype=bool),
        )

        mask, reason = build_valid_mask(window)

        assert mask.all()
        assert reason is None

    def test_empty_data_dict_returns_empty_mask_with_reason(self):
        """When no bands were read, there is no pixel data to mask — return empty array and obstruction reason."""
        window = RasterWindow(
            data={},
            crs="EPSG:32616",
            transform=(),
            bounds=(),
            scl_mask=None,
        )

        mask, reason = build_valid_mask(window)

        assert mask.size == 0 or list(mask.shape) == [0, 0]
        assert reason is not None

    def test_scl_none_and_empty_data_returns_empty_mask(self):
        """Edge case: no SCL and no band data should still produce a valid empty return."""
        window = RasterWindow(
            data={},
            crs="",
            transform=(),
            bounds=(),
            scl_mask=None,
        )

        mask, reason = build_valid_mask(window)

        assert mask.size == 0
        assert reason is not None


# ---------------------------------------------------------------------------
# Fixtures for align_to_common_grid
# ---------------------------------------------------------------------------


@pytest.fixture
def same_crs_before() -> RasterWindow:
    """Before window with 3 bands at 10x10 in EPSG:32616."""
    return RasterWindow(
        data={
            "B04": np.full((10, 10), 5000, dtype=np.uint16),
            "B08": np.full((10, 10), 8000, dtype=np.uint16),
            "B11": np.full((10, 10), 2000, dtype=np.uint16),
        },
        crs="EPSG:32616",
        transform=(10.0, 0.0, 500000.0, 0.0, -10.0, 1000000.0),
        bounds=(500000.0, 999900.0, 500100.0, 1000000.0),
        scl_mask=np.ones((10, 10), dtype=bool),
    )


@pytest.fixture
def same_crs_after() -> RasterWindow:
    """After window with matching CRS and shape, slightly different band values."""
    return RasterWindow(
        data={
            "B04": np.full((10, 10), 3000, dtype=np.uint16),
            "B08": np.full((10, 10), 6000, dtype=np.uint16),
            "B11": np.full((10, 10), 1500, dtype=np.uint16),
        },
        crs="EPSG:32616",
        transform=(10.0, 0.0, 500000.0, 0.0, -10.0, 1000000.0),
        bounds=(500000.0, 999900.0, 500100.0, 1000000.0),
        scl_mask=np.ones((10, 10), dtype=bool),
    )


# ---------------------------------------------------------------------------
# align_to_common_grid
# ---------------------------------------------------------------------------


class TestAlignToCommonGrid:
    """align_to_common_grid(): reproject, resample, and crop before/after to shared grid."""

    @patch("oberon.pipeline.preparation.rasterio")
    def test_same_crs_returns_matching_shapes(
        self, mock_rasterio: MagicMock,
        same_crs_before: RasterWindow,
        same_crs_after: RasterWindow,
    ):
        """When before and after share the same CRS, all output bands should have identical shape and CRS."""
        mock_rasterio.warp = MagicMock()
        mock_rasterio.warp.reproject = _passthrough_reproject
        mock_rasterio.warp.transform = MagicMock(return_value=([500000.0], [1000000.0]))

        result = align_to_common_grid(same_crs_before, same_crs_after)

        assert isinstance(result, PreparedPair)
        assert result.before.keys() == result.after.keys() == {"B04", "B08", "B11"}
        first_shape = next(iter(result.before.values())).shape
        for arr in result.before.values():
            assert arr.shape == first_shape, "all before bands must share shape"
        for arr in result.after.values():
            assert arr.shape == first_shape, "all after bands must share shape"
        assert first_shape == (10, 10)
        assert result.crs == "EPSG:32616"
        assert result.mask.shape == first_shape
        assert result.mask.dtype == bool

    @patch("oberon.pipeline.preparation.rasterio")
    def test_different_crs_reprojects_to_target(
        self, mock_rasterio: MagicMock,
    ):
        """Before and after from different CRS should both be reprojected to target_crs with matching shapes."""
        before = RasterWindow(
            data={"B04": np.full((8, 8), 5000, dtype=np.uint16)},
            crs="EPSG:32616",
            transform=(10.0, 0.0, 500000.0, 0.0, -10.0, 1000000.0),
            bounds=(500000.0, 999920.0, 500080.0, 1000000.0),
            scl_mask=np.ones((8, 8), dtype=bool),
        )
        after = RasterWindow(
            data={"B04": np.full((6, 6), 3000, dtype=np.uint16)},
            crs="EPSG:32617",
            transform=(10.0, 0.0, 600000.0, 0.0, -10.0, 4800000.0),
            bounds=(),  # empty bounds → uses fallback grid (before's shape)
            scl_mask=np.ones((6, 6), dtype=bool),
        )

        def _reproject_to_dst_shape(source, destination, **kwargs):
            destination[:] = np.full(destination.shape, np.mean(source), dtype=np.float32)
        mock_rasterio.warp = MagicMock()
        mock_rasterio.warp.reproject = _reproject_to_dst_shape
        mock_rasterio.warp.transform = MagicMock(return_value=([500000.0], [1000000.0]))

        result = align_to_common_grid(before, after, target_crs="EPSG:32616")

        assert result.crs == "EPSG:32616"
        assert result.before["B04"].shape == result.after["B04"].shape
        assert result.mask.shape == result.before["B04"].shape

    @patch("oberon.pipeline.preparation.rasterio")
    def test_dimension_below_10px_returns_unusable(
        self, mock_rasterio: MagicMock,
    ):
        """When the resampled output has any dimension < 10 pixels, is_usable should be False."""
        before = RasterWindow(
            data={"B04": np.full((3, 10), 5000, dtype=np.uint16)},
            crs="EPSG:32616",
            transform=(10.0, 0.0, 500000.0, 0.0, -10.0, 1000000.0),
            bounds=(500000.0, 999970.0, 500030.0, 1000000.0),
            scl_mask=np.ones((3, 10), dtype=bool),
        )
        after = RasterWindow(
            data={"B04": np.full((3, 10), 3000, dtype=np.uint16)},
            crs="EPSG:32616",
            transform=(10.0, 0.0, 500000.0, 0.0, -10.0, 1000000.0),
            bounds=(500000.0, 999970.0, 500030.0, 1000000.0),
            scl_mask=np.ones((3, 10), dtype=bool),
        )

        mock_rasterio.warp = MagicMock()
        mock_rasterio.warp.reproject = _passthrough_reproject
        mock_rasterio.warp.transform = MagicMock(return_value=([500000.0], [1000000.0]))

        result = align_to_common_grid(before, after)

        assert not result.is_usable

    @patch("oberon.pipeline.preparation.rasterio")
    def test_20m_bands_upsampled_to_10m(
        self, mock_rasterio: MagicMock,
    ):
        """20m-resolution bands (B05, B06, etc.) should be bilinearly upsampled to match 10m band shape."""
        before = RasterWindow(
            data={
                "B04": np.full((10, 10), 5000, dtype=np.uint16),      # 10m band
                "B05": np.full((5, 5), 4000, dtype=np.uint16),         # 20m band
            },
            crs="EPSG:32616",
            transform=(10.0, 0.0, 500000.0, 0.0, -10.0, 1000000.0),
            bounds=(500000.0, 999900.0, 500100.0, 1000000.0),
            scl_mask=np.ones((10, 10), dtype=bool),
        )
        after = RasterWindow(
            data={
                "B04": np.full((10, 10), 3000, dtype=np.uint16),
                "B05": np.full((5, 5), 2000, dtype=np.uint16),
            },
            crs="EPSG:32616",
            transform=(10.0, 0.0, 500000.0, 0.0, -10.0, 1000000.0),
            bounds=(500000.0, 999900.0, 500100.0, 1000000.0),
            scl_mask=np.ones((10, 10), dtype=bool),
        )

        recorded_calls: list[dict] = []

        def _reproject_with_tracking(source, destination, **kwargs):
            recorded_calls.append({
                "src_shape": source.shape,
                "dst_shape": destination.shape,
                "resampling": kwargs.get("resampling"),
            })
            destination[:] = np.full(destination.shape, np.mean(source), dtype=np.float32)

        mock_rasterio.warp = MagicMock()
        mock_rasterio.warp.reproject = _reproject_with_tracking
        mock_rasterio.warp.transform = MagicMock(return_value=([500000.0], [1000000.0]))

        result = align_to_common_grid(before, after)

        # All output bands should share the same (10m) shape
        first_shape = next(iter(result.before.values())).shape
        for arr in result.before.values():
            assert arr.shape == first_shape
        for arr in result.after.values():
            assert arr.shape == first_shape
        # The 20m band (B05) should have been upsampled to 10m shape
        assert result.before["B05"].shape == (10, 10)

    @patch("oberon.pipeline.preparation.rasterio")
    def test_is_usable_threshold(self, mock_rasterio: MagicMock):
        """PreparedPair.is_usable should be False when valid_fraction < 0.30."""
        mock_rasterio.warp = MagicMock()
        mock_rasterio.warp.reproject = _passthrough_reproject
        mock_rasterio.warp.transform = MagicMock(return_value=([500000.0], [1000000.0]))

        pair = PreparedPair(
            before={"B04": np.ones((10, 10))},
            after={"B04": np.ones((10, 10))},
            mask=np.zeros((10, 10), dtype=bool),  # all invalid
            crs="EPSG:32616",
            transform=(10.0, 0.0, 500000.0, 0.0, -10.0, 1000000.0),
            bounds=(),
        )

        assert pair.valid_fraction == 0.0
        assert not pair.is_usable

        pair2 = PreparedPair(
            before={"B04": np.ones((10, 10))},
            after={"B04": np.ones((10, 10))},
            mask=np.ones((10, 10), dtype=bool),  # all valid
            crs="EPSG:32616",
            transform=(),
            bounds=(),
        )
        assert pair2.valid_fraction == 1.0
        assert pair2.is_usable

    @patch("oberon.pipeline.preparation.rasterio")
    def test_intersection_bounds_cropping(
        self, mock_rasterio: MagicMock,
    ):
        """When before and after have different geographic extents, output should be cropped to their intersection."""
        before = RasterWindow(
            data={"B04": np.full((10, 20), 5000, dtype=np.uint16)},
            crs="EPSG:32616",
            transform=(10.0, 0.0, 500000.0, 0.0, -10.0, 1000000.0),
            bounds=(500000.0, 999800.0, 500200.0, 1000000.0),  # 200m x 200m
            scl_mask=np.ones((10, 20), dtype=bool),
        )
        after = RasterWindow(
            data={"B04": np.full((12, 10), 3000, dtype=np.uint16)},
            crs="EPSG:32616",
            transform=(10.0, 0.0, 499980.0, 0.0, -10.0, 1000020.0),
            bounds=(499980.0, 999900.0, 500080.0, 1000020.0),  # 100m x 120m, shifted west and up
            scl_mask=np.ones((12, 10), dtype=bool),
        )

        # before extent: x=[500000, 500200], y=[999800, 1000000]
        # after extent:  x=[499980, 500080], y=[999900, 1000020]
        # intersection:  x=[500000, 500080], y=[999900, 1000000]
        # → width=80m/10m=8px, height=100m/10m=10px → (10, 8)

        mock_rasterio.warp = MagicMock()
        mock_rasterio.warp.reproject = _passthrough_reproject
        mock_rasterio.warp.transform = MagicMock(return_value=([500000.0], [1000000.0]))

        result = align_to_common_grid(before, after)

        assert result.before["B04"].shape == (10, 8)
        assert result.after["B04"].shape == (10, 8)
        assert result.mask.shape == (10, 8)

    @patch("oberon.pipeline.preparation.rasterio")
    def test_no_overlap_returns_empty(
        self, mock_rasterio: MagicMock,
    ):
        """When before and after bounds do not overlap at all, should return an empty PreparedPair."""
        before = RasterWindow(
            data={"B04": np.full((10, 10), 5000, dtype=np.uint16)},
            crs="EPSG:32616",
            transform=(10.0, 0.0, 500000.0, 0.0, -10.0, 1000000.0),
            bounds=(500000.0, 999900.0, 500100.0, 1000000.0),
            scl_mask=np.ones((10, 10), dtype=bool),
        )
        after = RasterWindow(
            data={"B04": np.full((10, 10), 3000, dtype=np.uint16)},
            crs="EPSG:32616",
            transform=(10.0, 0.0, 600000.0, 0.0, -10.0, 4800000.0),
            bounds=(600000.0, 4799900.0, 600100.0, 4800000.0),  # different hemisphere
            scl_mask=np.ones((10, 10), dtype=bool),
        )

        mock_rasterio.warp = MagicMock()
        mock_rasterio.warp.reproject = _passthrough_reproject
        mock_rasterio.warp.transform = MagicMock(return_value=([500000.0], [1000000.0]))

        result = align_to_common_grid(before, after)

        assert result.before == {}
        assert result.after == {}
        assert result.mask.size == 0

    @patch("oberon.pipeline.preparation.rasterio")
    def test_scl_band_uses_nearest_neighbor(
        self, mock_rasterio: MagicMock,
    ):
        """When a band named 'SCL' is in the data dict, nearest-neighbor resampling should be used (not bilinear)."""
        recorded_calls: list[dict] = []

        def _tracking_reproject(source, destination, **kwargs):
            recorded_calls.append({
                "resampling": kwargs.get("resampling"),
                "src_shape": source.shape,
                "dst_shape": destination.shape,
            })
            destination[:] = np.full(destination.shape, np.mean(source), dtype=np.float32)

        # Destination is 10x10 (from intersection bounds at 10m resolution).
        # SCL band at 5x5 needs reproject (different shape → resize), which triggers the resampling decision.
        before = RasterWindow(
            data={
                "B04": np.full((10, 10), 5000, dtype=np.uint16),   # 10m
                "SCL": np.full((5, 5), 4, dtype=np.uint16),        # 20m → needs nearest-neighbor upsampling
            },
            crs="EPSG:32616",
            transform=(10.0, 0.0, 500000.0, 0.0, -10.0, 1000000.0),
            bounds=(500000.0, 999900.0, 500100.0, 1000000.0),
            scl_mask=np.ones((10, 10), dtype=bool),
        )
        after = RasterWindow(
            data={
                "B04": np.full((10, 10), 3000, dtype=np.uint16),
                "SCL": np.full((5, 5), 4, dtype=np.uint16),
            },
            crs="EPSG:32616",
            transform=(10.0, 0.0, 500000.0, 0.0, -10.0, 1000000.0),
            bounds=(500000.0, 999900.0, 500100.0, 1000000.0),
            scl_mask=np.ones((10, 10), dtype=bool),
        )

        mock_rasterio.warp = MagicMock()
        mock_rasterio.warp.reproject = _tracking_reproject
        mock_rasterio.warp.transform = MagicMock(return_value=([500000.0], [1000000.0]))

        result = align_to_common_grid(before, after)

        # All output bands share the same shape
        assert result.before["B04"].shape == (10, 10)
        assert result.before["SCL"].shape == (10, 10)

        # Each recorded call for an SCL source should use nearest-neighbor
        for call in recorded_calls:
            if call["src_shape"] == (5, 5):  # SCL band (20m)
                # The resampling value is a MagicMock wrapping the real enum under mock patches
                resampling_name = str(call["resampling"])
                assert "nearest" in resampling_name.lower(), \
                    f"SCL band must use nearest-neighbor resampling, got {resampling_name}"


def _passthrough_reproject(source, destination, **kwargs):
    """Mock rasterio.warp.reproject that copies source into destination, up/down-scaling shape as needed."""
    if source.shape != destination.shape:
        destination[:] = np.full(destination.shape, np.mean(source), dtype=np.float32)
    else:
        destination[:] = source.astype(np.float32)
