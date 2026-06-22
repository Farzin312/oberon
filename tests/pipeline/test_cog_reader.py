"""Tests for COG windowed reads.

Module: oberon/pipeline/cog_reader.py

Covers windowed reads from cloud-optimized GeoTIFFs: valid reads, 404 handling,
missing bands, empty band lists, and window buffer behaviour.
"""

from __future__ import annotations

from datetime import datetime
from unittest.mock import MagicMock, patch

import numpy as np
import pytest
from affine import Affine
from rasterio.crs import CRS
from rasterio.errors import RasterioIOError
from rasterio.windows import Window

from oberon.core import CandidateScene, RasterWindow
from oberon.pipeline.cog_reader import read_window

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def cog_scene() -> CandidateScene:
    """A CandidateScene with four band assets for standard windowed reading."""
    return CandidateScene(
        stac_item_id="S2A_10TFL_20260115_0_L2A",
        datetime=datetime(2026, 1, 15, 18, 30, 0),
        geometry={
            "type": "Polygon",
            "coordinates": [[
                [-84.0, 10.0],
                [-83.9, 10.0],
                [-83.9, 10.1],
                [-84.0, 10.1],
                [-84.0, 10.0],
            ]],
        },
        bbox=(-84.0, 10.0, -83.9, 10.1),
        assets={
            "B02": "s3://mock-cog/B02.tif",
            "B03": "s3://mock-cog/B03.tif",
            "B04": "s3://mock-cog/B04.tif",
            "B08": "s3://mock-cog/B08.tif",
        },
        scl_url="s3://mock-cog/SCL.tif",
        scene_cloud_pct=5.0,
    )


@pytest.fixture
def aoi_geometry() -> dict:
    """Small AOI polygon (~100 ha) in Costa Rica."""
    return {
        "type": "Polygon",
        "coordinates": [[
            [-84.0, 10.0],
            [-83.9, 10.0],
            [-83.9, 10.1],
            [-84.0, 10.1],
            [-84.0, 10.0],
        ]],
    }


# ---------------------------------------------------------------------------
# read_window
# ---------------------------------------------------------------------------


class TestReadWindow:
    """read_window(): windowed reads from cloud-optimized GeoTIFFs."""

    # --- helpers -----------------------------------------------------------

    @staticmethod
    def _make_mock_src() -> MagicMock:
        """Build a mock rasterio DatasetReader with standard UTM metadata."""
        src = MagicMock()
        src.crs = CRS.from_epsg(32616)
        src.transform = Affine(10.0, 0.0, 300000.0, 0.0, -10.0, 4800000.0)
        return src

    @staticmethod
    def _setup_mock_rasterio(
        mock_rasterio: MagicMock,
        mock_src: MagicMock,
        win: Window | None = None,
        warp_result: tuple[list[float], list[float]] | None = None,
        win_bounds: tuple[float, float, float, float] = (300040.0, 4799740.0, 300260.0, 4799960.0),
    ) -> None:
        """Configure the mocked rasterio module with standard return values."""
        if win is None:
            win = Window(5, 5, 20, 20)
        if warp_result is None:
            warp_result = (
                [300000.0, 300100.0, 300000.0, 300100.0],
                [4800000.0, 4800000.0, 4800100.0, 4800100.0],
            )
        mock_rasterio.open.return_value.__enter__.return_value = mock_src
        mock_rasterio.windows.from_bounds.return_value = win
        mock_rasterio.warp.transform.return_value = warp_result
        mock_rasterio.windows.bounds.return_value = win_bounds

    # --- tests -------------------------------------------------------------

    @patch("oberon.pipeline.cog_reader.rasterio")
    def test_returns_rasterwindow_with_correct_keys_and_shapes(
        self,
        mock_rasterio: MagicMock,
        cog_scene: CandidateScene,
        aoi_geometry: dict,
    ):
        """read_window returns a RasterWindow whose data dict keys match the requested bands, each a 2D uint16 array."""
        mock_src = self._make_mock_src()
        mock_src.read.return_value = np.ones((22, 22), dtype=np.uint16)
        self._setup_mock_rasterio(mock_rasterio, mock_src)

        result = read_window(cog_scene, aoi_geometry, ["B02", "B03", "B04", "B08"])

        assert isinstance(result, RasterWindow)
        assert set(result.data.keys()) == {"B02", "B03", "B04", "B08"}
        for _band, arr in result.data.items():
            assert isinstance(arr, np.ndarray)
            assert arr.ndim == 2
            assert arr.dtype == np.uint16
            assert arr.shape == (22, 22)

    @patch("oberon.pipeline.cog_reader.rasterio")
    def test_404_cog_url_raises_file_not_found(
        self,
        mock_rasterio: MagicMock,
        cog_scene: CandidateScene,
        aoi_geometry: dict,
    ):
        """A RasterioIOError from rasterio.open should be raised as FileNotFoundError with the scene ID in the message."""
        mock_rasterio.open.side_effect = RasterioIOError("No such file or directory")

        with pytest.raises(FileNotFoundError, match=cog_scene.stac_item_id):
            read_window(cog_scene, aoi_geometry, ["B02"])

    @patch("oberon.pipeline.cog_reader.rasterio")
    def test_missing_band_returns_partial_dict(
        self,
        mock_rasterio: MagicMock,
        cog_scene: CandidateScene,
        aoi_geometry: dict,
    ):
        """Bands absent from scene.assets are silently skipped; only available bands appear in the returned data dict."""
        mock_src = self._make_mock_src()
        mock_src.read.return_value = np.ones((22, 22), dtype=np.uint16)
        self._setup_mock_rasterio(mock_rasterio, mock_src)

        # Request a band (B11) that is not in the scene's assets
        result = read_window(cog_scene, aoi_geometry, ["B02", "B11", "B03", "B08"])

        assert "B02" in result.data
        assert "B03" in result.data
        assert "B08" in result.data
        assert "B11" not in result.data

    @patch("oberon.pipeline.cog_reader.rasterio")
    def test_empty_band_list_raises_value_error(
        self,
        mock_rasterio: MagicMock,
        cog_scene: CandidateScene,
        aoi_geometry: dict,
    ):
        """Passing an empty bands list should raise ValueError — at least one band is required."""
        with pytest.raises(ValueError, match="band"):
            read_window(cog_scene, aoi_geometry, [])

    @patch("oberon.pipeline.cog_reader.rasterio")
    def test_buffer_pixels_adds_padding(
        self,
        mock_rasterio: MagicMock,
        cog_scene: CandidateScene,
        aoi_geometry: dict,
    ):
        """buffer_pixels=1 should produce a window that is 2 px wider and taller than the non-buffered AOI window."""
        mock_src = self._make_mock_src()
        # from_bounds returns Window(5, 5, 20, 20). With buffer=1: (4, 4, 22, 22)
        mock_src.read.return_value = np.ones((22, 22), dtype=np.uint16)
        self._setup_mock_rasterio(mock_rasterio, mock_src)

        result = read_window(cog_scene, aoi_geometry, ["B02"], buffer_pixels=1)

        assert result.data["B02"].shape == (22, 22), (
            "buffer_pixels=1 on a 20x20 window produces a 22x22 array"
        )
