"""Tests for the COG session cache (006 Phase 3)."""

from __future__ import annotations

import numpy as np

from oberon.core import CandidateScene, RasterWindow
from oberon.pipeline.cog_reader import (
    _cache_key,
    clear_cache,
    disable_cache,
    enable_cache,
    get_cache_size,
)


def _make_scene(scene_id: str = "S2A_001") -> CandidateScene:
    return CandidateScene(
        stac_item_id=scene_id,
        datetime=None,  # type: ignore[arg-type]
        geometry={"type": "Polygon", "coordinates": [[[0, 0], [1, 0], [1, 1], [0, 1], [0, 0]]]},
        bbox=(0.0, 0.0, 1.0, 1.0),
        assets={"B04": "https://example.com/B04.tif", "B03": "https://example.com/B03.tif"},
        scl_url=None,
        scene_cloud_pct=5.0,
    )


def _make_raster_window() -> RasterWindow:
    return RasterWindow(
        data={"B04": np.ones((10, 10), dtype=np.float32)},
        crs="EPSG:32617",
        transform=(10.0, 0.0, 0.0, 0.0, -10.0, 0.0),
        bounds=(0.0, 0.0, 100.0, 100.0),
        scl_mask=None,
    )


class TestCacheKey:
    """_cache_key: deterministic key from (scene, AOI, bands)."""

    def test_same_inputs_same_key(self) -> None:
        scene = _make_scene()
        geom = {"type": "Polygon", "coordinates": [[[0, 0], [1, 0], [1, 1], [0, 1], [0, 0]]]}
        k1 = _cache_key(scene, geom, ["B04", "B03"])
        k2 = _cache_key(scene, geom, ["B04", "B03"])
        assert k1 == k2

    def test_different_scenes_different_keys(self) -> None:
        s1 = _make_scene("S2A_001")
        s2 = _make_scene("S2B_002")
        geom = {"type": "Polygon", "coordinates": [[[0, 0], [1, 0], [1, 1], [0, 1], [0, 0]]]}
        k1 = _cache_key(s1, geom, ["B04"])
        k2 = _cache_key(s2, geom, ["B04"])
        assert k1 != k2

    def test_different_bands_different_keys(self) -> None:
        scene = _make_scene()
        geom = {"type": "Polygon", "coordinates": [[[0, 0], [1, 0], [1, 1], [0, 1], [0, 0]]]}
        k1 = _cache_key(scene, geom, ["B04"])
        k2 = _cache_key(scene, geom, ["B03"])
        assert k1 != k2

    def test_band_order_independent(self) -> None:
        """Bands [B04, B03] and [B03, B04] should produce the same key."""
        scene = _make_scene()
        geom = {"type": "Polygon", "coordinates": [[[0, 0], [1, 0], [1, 1], [0, 1], [0, 0]]]}
        k1 = _cache_key(scene, geom, ["B04", "B03"])
        k2 = _cache_key(scene, geom, ["B03", "B04"])
        assert k1 == k2


class TestCacheEnableDisable:
    """enable_cache / disable_cache / clear_cache lifecycle."""

    def test_enable_sets_flag(self) -> None:
        disable_cache()  # Start clean
        enable_cache()
        from oberon.pipeline.cog_reader import _cache_enabled

        assert _cache_enabled is True
        disable_cache()

    def test_disable_clears_flag(self) -> None:
        enable_cache()
        disable_cache()
        from oberon.pipeline.cog_reader import _cache_enabled

        assert _cache_enabled is False

    def test_disable_clears_entries(self) -> None:
        enable_cache()
        # Manually inject an entry via the module-level dict.
        from oberon.pipeline.cog_reader import _cache

        _cache["test-key"] = _make_raster_window()
        assert get_cache_size() > 0
        disable_cache()
        assert get_cache_size() == 0

    def test_clear_cache_without_disable(self) -> None:
        enable_cache()
        from oberon.pipeline.cog_reader import _cache

        _cache["test-key"] = _make_raster_window()
        assert get_cache_size() > 0
        clear_cache()
        assert get_cache_size() == 0
        # Cache is still enabled, just empty.
        from oberon.pipeline.cog_reader import _cache_enabled

        assert _cache_enabled is True
        disable_cache()
