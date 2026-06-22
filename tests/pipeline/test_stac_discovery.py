"""Tests for STAC catalog discovery and scene selection.

Module: oberon/pipeline/stac_discovery.py

Each test class covers one public function. Every test method has a
docstring explaining what behaviour it validates. Edge cases and
failure modes are tested explicitly.
"""

from __future__ import annotations

from datetime import UTC, date, datetime
from unittest.mock import MagicMock, patch

import pytest

from oberon.core import CandidateScene, ChangeRequest
from oberon.pipeline.stac_discovery import rank_by_scene_quality, search_catalog

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def change_request() -> ChangeRequest:
    """A standard vegetation-disturbance request spanning Jan and Jun 2026."""
    return ChangeRequest(
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
        before=(date(2026, 1, 1), date(2026, 1, 31)),
        after=(date(2026, 6, 1), date(2026, 6, 30)),
        task="vegetation_disturbance",
    )


@pytest.fixture
def sample_items() -> list[dict]:
    """Two mock STAC items: one low-cloud (5%), one high-cloud (75%)."""
    return [
        {
            "id": "S2A_10TFL_20260115_0_L2A",
            "properties": {"datetime": "2026-01-15T18:30:00Z", "eo:cloud_cover": 5.0},
            "bbox": [-84.2, 9.8, -83.7, 10.3],
            "geometry": {"type": "Polygon", "coordinates": [[[-84.2, 9.8], [-83.7, 9.8], [-83.7, 10.3], [-84.2, 10.3], [-84.2, 9.8]]]},
            "assets": {"blue": {"href": "s3://.../B02.tif"}, "green": {"href": "s3://.../B03.tif"},
                       "red": {"href": "s3://.../B04.tif"}, "nir": {"href": "s3://.../B08.tif"},
                       "scl": {"href": "s3://.../SCL.tif"}},
        },
        {
            "id": "S2A_10TFL_20260125_0_L2A",
            "properties": {"datetime": "2026-01-25T18:30:00Z", "eo:cloud_cover": 75.0},
            "bbox": [-84.2, 9.8, -83.7, 10.3],
            "geometry": {"type": "Polygon", "coordinates": [[[-84.2, 9.8], [-83.7, 9.8], [-83.7, 10.3], [-84.2, 10.3], [-84.2, 9.8]]]},
            "assets": {"blue": {"href": "s3://.../B02.tif"}, "green": {"href": "s3://.../B03.tif"},
                       "red": {"href": "s3://.../B04.tif"}, "nir": {"href": "s3://.../B08.tif"},
                       "scl": {"href": "s3://.../SCL.tif"}},
        },
    ]


def _mock_stac_item(item_dict: dict) -> MagicMock:
    """Build a mock pystac.Item from a simple dict fixture."""
    item = MagicMock()
    item.id = item_dict["id"]
    item.properties = item_dict["properties"]
    item.bbox = item_dict["bbox"]
    item.geometry = item_dict["geometry"]
    item.datetime = datetime.fromisoformat(item_dict["properties"]["datetime"].replace("Z", "+00:00"))
    item.collection_id = "sentinel-2-l2a"
    item.assets = {}
    for band_name, asset_info in item_dict["assets"].items():
        asset = MagicMock()
        asset.href = asset_info["href"]
        asset.media_type = "image/tiff; application=geotiff; profile=cloud-optimized"
        item.assets[band_name] = asset
    return item


# ---------------------------------------------------------------------------
# search_catalog
# ---------------------------------------------------------------------------

class TestSearchCatalog:
    """search_catalog(): discover Sentinel-2 scenes intersecting the AOI."""

    def test_returns_items_from_both_date_windows(self, change_request, sample_items):
        """Should return 4 candidates: 2 items x 2 date windows (before + after)."""
        mock_client = MagicMock()
        mock_client.search.return_value.items.return_value = [
            _mock_stac_item(item) for item in sample_items
        ]

        with patch("oberon.pipeline.stac_discovery.Client.open", return_value=mock_client):
            candidates = search_catalog(change_request)

        assert len(candidates) == 4

    def test_each_result_is_candidate_scene(self, change_request, sample_items):
        """Each returned item should be properly parsed into a CandidateScene with all fields populated."""
        mock_client = MagicMock()
        mock_client.search.return_value.items.return_value = [
            _mock_stac_item(item) for item in sample_items
        ]

        with patch("oberon.pipeline.stac_discovery.Client.open", return_value=mock_client):
            candidates = search_catalog(change_request)

        assert all(isinstance(c, CandidateScene) for c in candidates)
        assert all(c.stac_item_id for c in candidates)
        assert all(c.assets for c in candidates)

    def test_search_uses_intersects_and_datetime_filters(self, change_request):
        """STAC search should be called with intersects, datetime range, and sentinel-2-l2a collection."""
        mock_client = MagicMock()
        mock_client.search.return_value.items.return_value = []

        with patch("oberon.pipeline.stac_discovery.Client.open", return_value=mock_client):
            search_catalog(change_request)

        assert mock_client.search.call_count == 2
        for call_args in mock_client.search.call_args_list:
            kwargs = call_args[1]
            assert "intersects" in kwargs, "search() must filter by geometry"
            assert "datetime" in kwargs, "search() must filter by date window"
            assert kwargs.get("collections") == ["sentinel-2-l2a"], "only Sentinel-2 L2A"

    def test_returns_empty_list_when_no_scenes_found(self, change_request):
        """Should return [] when the catalog has no matching items for either window."""
        mock_client = MagicMock()
        mock_client.search.return_value.items.return_value = []

        with patch("oberon.pipeline.stac_discovery.Client.open", return_value=mock_client):
            candidates = search_catalog(change_request)

        assert candidates == []

    def test_raises_connection_error_on_stac_failure(self, change_request):
        """Should raise ConnectionError with a descriptive message when the STAC API is unreachable."""
        with patch("oberon.pipeline.stac_discovery.Client.open", side_effect=ConnectionError("STAC unavailable")):
            with pytest.raises(ConnectionError, match="STAC"):
                search_catalog(change_request)

    def test_parses_stac_item_fields_correctly(self, change_request, sample_items):
        """CandidateScene fields should faithfully reproduce the STAC item's id, cloud cover, bbox, and assets."""
        mock_client = MagicMock()
        mock_client.search.return_value.items.return_value = [
            _mock_stac_item(sample_items[0])
        ]

        with patch("oberon.pipeline.stac_discovery.Client.open", return_value=mock_client):
            candidates = search_catalog(change_request)

        scene = candidates[0]
        assert scene.stac_item_id == "S2A_10TFL_20260115_0_L2A"
        assert scene.scene_cloud_pct == 5.0
        assert len(scene.bbox) == 4
        assert "B02" in scene.assets
        assert scene.scl_url is not None

    def test_handles_items_without_geometry(self, change_request):
        """Items missing geometry or bbox should be silently skipped (they cannot be evaluated locally)."""
        item = MagicMock()
        item.id = "no-geom"
        item.properties = {"datetime": "2026-01-15T18:30:00Z", "eo:cloud_cover": 0.0}
        item.bbox = None
        item.geometry = None
        item.datetime = datetime(2026, 1, 15, 18, 30, 0)
        item.assets = {"B02": MagicMock(href="s3://..."), "SCL": MagicMock(href="s3://...")}

        mock_client = MagicMock()
        mock_client.search.return_value.items.return_value = [item]

        with patch("oberon.pipeline.stac_discovery.Client.open", return_value=mock_client):
            candidates = search_catalog(change_request)

        assert len(candidates) == 0

    def test_handles_missing_cloud_cover(self, change_request):
        """Should default cloud cover to 0.0 when the STAC item lacks eo:cloud_cover.

        Regression guard: the STAC API may return items without the cloud_cover
        field for older scenes. The parser must coerce this to a safe default
        rather than crashing or producing None.
        """
        item = MagicMock()
        item.id = "no-cloud-meta"
        item.properties = {"datetime": "2026-01-15T18:30:00Z"}
        item.bbox = [-84.2, 9.8, -83.7, 10.3]
        item.geometry = {"type": "Polygon", "coordinates": [[[-84.2, 9.8], [-83.7, 9.8], [-83.7, 10.3], [-84.2, 10.3], [-84.2, 9.8]]]}
        item.datetime = datetime(2026, 1, 15, 18, 30, 0)
        item.assets = {"B02": MagicMock(href="s3://...")}

        # Only return the item on the FIRST search call (before window)
        mock_client = MagicMock()
        mock_client.search.return_value.items.side_effect = [
            [item],   # before window returns the item
            [],       # after window returns nothing
        ]

        with patch("oberon.pipeline.stac_discovery.Client.open", return_value=mock_client):
            candidates = search_catalog(change_request)

        assert len(candidates) == 1
        assert candidates[0].scene_cloud_pct == 0.0


# ---------------------------------------------------------------------------
# rank_by_scene_quality
# ---------------------------------------------------------------------------

class TestRankBySceneQuality:
    """rank_by_scene_quality(): rank and filter CandidateScene items by cloud cover."""

    def test_lower_cloud_fraction_ranks_first(self):
        """Scenes with lower cloud cover should appear before cloudier scenes in the sorted result."""
        candidates = [
            CandidateScene("id-90", datetime.now(UTC), {}, (0, 0, 1, 1), {}, None, 90.0),
            CandidateScene("id-10", datetime.now(UTC), {}, (0, 0, 1, 1), {}, None, 10.0),
        ]
        ranked = rank_by_scene_quality(candidates, max_cloud_pct=100.0, max_selected=2)
        assert ranked[0].candidate.scene_cloud_pct == 10.0
        assert ranked[1].candidate.scene_cloud_pct == 90.0

    def test_filters_candidates_above_cloud_threshold(self):
        """Scenes exceeding max_cloud_pct should be excluded entirely from results."""
        candidates = [
            CandidateScene("clear", datetime.now(UTC), {}, (0, 0, 1, 1), {}, None, 5.0),
            CandidateScene("cloudy", datetime.now(UTC), {}, (0, 0, 1, 1), {}, None, 80.0),
        ]
        ranked = rank_by_scene_quality(candidates, max_cloud_pct=10.0, max_selected=5)
        assert len(ranked) == 1
        assert ranked[0].candidate.stac_item_id == "clear"

    def test_returns_empty_when_all_candidates_exceed_threshold(self):
        """Should return [] when every candidate's cloud cover is above max_cloud_pct."""
        candidates = [
            CandidateScene("very-cloudy", datetime.now(UTC), {}, (0, 0, 1, 1), {}, None, 95.0),
        ]
        ranked = rank_by_scene_quality(candidates, max_cloud_pct=10.0)
        assert ranked == []

    def test_respects_max_selected_limit(self):
        """Should return at most max_selected items, even when more pass the filter."""
        candidates = [
            CandidateScene(f"id-{i}", datetime.now(UTC), {}, (0, 0, 1, 1), {}, None, float(i * 10))
            for i in range(10)
        ]
        ranked = rank_by_scene_quality(candidates, max_cloud_pct=100.0, max_selected=3)
        assert len(ranked) == 3

    def test_period_split_with_window_info(self):
        """When before/after windows are provided, candidates should be split into two period groups."""
        jan_candidate = CandidateScene(
            "jan-scene", datetime(2026, 1, 15, 18, 30, 0, tzinfo=UTC), {}, (0, 0, 1, 1), {}, None, 5.0,
        )
        jun_candidate = CandidateScene(
            "jun-scene", datetime(2026, 6, 15, 18, 30, 0, tzinfo=UTC), {}, (0, 0, 1, 1), {}, None, 10.0,
        )

        ranked = rank_by_scene_quality(
            [jun_candidate, jan_candidate],
            before_window=(date(2026, 1, 1), date(2026, 1, 31)),
            after_window=(date(2026, 6, 1), date(2026, 6, 30)),
            max_cloud_pct=100.0,
            max_selected=1,
        )

        assert len(ranked) == 2
        periods = {r.period for r in ranked}
        assert periods == {"before", "after"}

    def test_period_unknown_without_window_info(self):
        """When no window info is provided, period should default to 'unknown'."""
        candidates = [
            CandidateScene("test", datetime.now(UTC), {}, (0, 0, 1, 1), {}, None, 5.0),
        ]
        ranked = rank_by_scene_quality(candidates, max_cloud_pct=100.0)
        assert ranked[0].period == "unknown"

    def test_empty_candidate_list_returns_empty(self):
        """Passing an empty list of candidates should return [] without error (no crash)."""
        assert rank_by_scene_quality([], max_cloud_pct=100.0) == []

    def test_local_valid_fraction_derived_from_cloud_pct(self):
        """local_valid_fraction should be (100 - cloud_pct) / 100 as a scene-level proxy."""
        candidates = [
            CandidateScene("half-cloudy", datetime.now(UTC), {}, (0, 0, 1, 1), {}, None, 50.0),
        ]
        ranked = rank_by_scene_quality(candidates, max_cloud_pct=100.0, max_selected=1)
        assert ranked[0].local_valid_fraction == 0.5

    def test_filters_scene_footprints_that_do_not_intersect_aoi(self):
        """Scenes whose STAC footprint misses the AOI should not win selection on cloud score alone."""
        aoi = {
            "type": "Polygon",
            "coordinates": [[
                [-120.1, 35.0],
                [-120.0, 35.0],
                [-120.0, 35.1],
                [-120.1, 35.1],
                [-120.1, 35.0],
            ]],
        }
        overlapping = CandidateScene(
            "overlapping",
            datetime(2026, 1, 15, 18, 30, 0, tzinfo=UTC),
            {"type": "Polygon", "coordinates": [[
                [-120.2, 34.9],
                [-119.9, 34.9],
                [-119.9, 35.2],
                [-120.2, 35.2],
                [-120.2, 34.9],
            ]]},
            (-120.2, 34.9, -119.9, 35.2),
            {},
            None,
            10.0,
        )
        lower_cloud_but_wrong_tile = CandidateScene(
            "wrong-tile",
            datetime(2026, 1, 16, 18, 30, 0, tzinfo=UTC),
            {"type": "Polygon", "coordinates": [[
                [-118.2, 34.9],
                [-117.9, 34.9],
                [-117.9, 35.2],
                [-118.2, 35.2],
                [-118.2, 34.9],
            ]]},
            (-118.2, 34.9, -117.9, 35.2),
            {},
            None,
            0.0,
        )

        ranked = rank_by_scene_quality(
            [lower_cloud_but_wrong_tile, overlapping],
            before_window=(date(2026, 1, 1), date(2026, 1, 31)),
            after_window=(date(2026, 6, 1), date(2026, 6, 30)),
            max_cloud_pct=100.0,
            max_selected=1,
            aoi_geometry=aoi,
        )

        assert [scene.candidate.stac_item_id for scene in ranked] == ["overlapping"]

    def test_prefers_common_mgrs_tile_across_periods(self):
        """Before/after selection should not mix Sentinel-2 tiles when a common tile is available."""
        before_10 = CandidateScene(
            "S2A_10SGD_20240619_0_L2A",
            datetime(2024, 6, 19, 18, 30, 0, tzinfo=UTC),
            {},
            (0, 0, 1, 1),
            {},
            None,
            12.0,
        )
        after_11_cleaner = CandidateScene(
            "S2B_11SKU_20241022_0_L2A",
            datetime(2024, 10, 22, 18, 30, 0, tzinfo=UTC),
            {},
            (0, 0, 1, 1),
            {},
            None,
            0.0,
        )
        after_10_common = CandidateScene(
            "S2B_10SGD_20241022_0_L2A",
            datetime(2024, 10, 22, 18, 30, 0, tzinfo=UTC),
            {},
            (0, 0, 1, 1),
            {},
            None,
            1.0,
        )

        ranked = rank_by_scene_quality(
            [after_11_cleaner, before_10, after_10_common],
            before_window=(date(2024, 6, 1), date(2024, 6, 30)),
            after_window=(date(2024, 10, 1), date(2024, 10, 31)),
            max_cloud_pct=100.0,
            max_selected=1,
        )

        assert [(scene.period, scene.candidate.stac_item_id) for scene in ranked] == [
            ("before", "S2A_10SGD_20240619_0_L2A"),
            ("after", "S2B_10SGD_20241022_0_L2A"),
        ]

    def test_falls_back_to_best_cloudy_candidate_when_period_would_be_empty(self):
        """Catalog cloud threshold should not prevent SCL/composite fallback from evaluating a period."""
        before_clear = CandidateScene(
            "S2A_29TNE_20240722_0_L2A",
            datetime(2024, 7, 22, 18, 30, 0, tzinfo=UTC),
            {},
            (0, 0, 1, 1),
            {},
            None,
            1.0,
        )
        after_cloudy = CandidateScene(
            "S2B_29TNE_20241010_0_L2A",
            datetime(2024, 10, 10, 18, 30, 0, tzinfo=UTC),
            {},
            (0, 0, 1, 1),
            {},
            None,
            19.0,
        )

        ranked = rank_by_scene_quality(
            [before_clear, after_cloudy],
            before_window=(date(2024, 7, 1), date(2024, 7, 31)),
            after_window=(date(2024, 10, 1), date(2024, 10, 31)),
            max_cloud_pct=15.0,
            max_selected=1,
        )

        assert [(scene.period, scene.candidate.stac_item_id) for scene in ranked] == [
            ("before", "S2A_29TNE_20240722_0_L2A"),
            ("after", "S2B_29TNE_20241010_0_L2A"),
        ]
