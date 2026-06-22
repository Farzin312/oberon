"""Tests for orchestrator auto-fallback to composite mode.

Module: oberon/cli/orchestrator.py

Tests that the orchestrator triggers scene compositing when the best
single scene's valid-pixel fraction is below the composite threshold,
and does NOT trigger it when the single scene is sufficient.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np

from oberon.cli.orchestrator import COMPOSITE_THRESHOLD, run_analysis
from oberon.core import ChangeRequest


def _request() -> ChangeRequest:
    """Build a minimal change request for testing."""
    return ChangeRequest(
        geometry={"type": "Polygon", "coordinates": [[[0, 0], [1, 0], [1, 1], [0, 1], [0, 0]]]},
        before=(date(2026, 1, 1), date(2026, 1, 31)),
        after=(date(2026, 6, 1), date(2026, 6, 30)),
    )


def _mock_selected_scene(scene_id: str, period: str, valid_frac: float) -> MagicMock:
    """Build a mock SelectedScene with the given valid fraction."""
    scene = MagicMock()
    scene.period = period
    scene.local_valid_fraction = valid_frac
    scene.candidate.stac_item_id = scene_id
    return scene


def _mock_raster_window() -> MagicMock:
    """Build a mock RasterWindow with minimal valid data."""
    window = MagicMock()
    window.data = {"B04": np.ones((10, 10), dtype=np.float32) * 1000}
    window.crs = "EPSG:32616"
    window.transform = (10.0, 0.0, 0.0, 0.0, -10.0, 0.0)
    window.bounds = (0.0, 0.0, 100.0, 100.0)
    window.scl_mask = np.ones((10, 10), dtype=bool)
    return window


def _patch_pipeline_stages():
    """Patch all pipeline stages downstream of composite/align so tests stay isolated."""
    from oberon.core import PreparedPair

    mock_pair = MagicMock(spec=PreparedPair)
    mock_pair.is_usable = True
    mock_pair.valid_fraction = 0.9
    mock_pair.before = {"B04": np.ones((10, 10), dtype=np.float32)}
    mock_pair.after = {"B04": np.zeros((10, 10), dtype=np.float32)}
    mock_pair.mask = np.ones((10, 10), dtype=bool)

    return (
        patch("oberon.cli.orchestrator.search_catalog", return_value=[]),
        patch("oberon.cli.orchestrator.rank_by_scene_quality"),
        patch("oberon.cli.orchestrator.read_window"),
        patch("oberon.cli.orchestrator.align_to_common_grid", return_value=mock_pair),
        patch("oberon.cli.orchestrator.build_composite"),
        patch("oberon.cli.orchestrator.compute_baselines"),
        patch("oberon.cli.orchestrator.threshold_change_map", return_value=np.ones((10, 10), dtype=bool)),
        patch("oberon.cli.orchestrator.extract_findings", return_value=[]),
        patch("oberon.cli.orchestrator.deduplicate_and_rank", return_value=[]),
        patch("oberon.cli.orchestrator.build_evidence_bundle", return_value=MagicMock()),
    )


class TestCompositeFallback:
    """Orchestrator auto-fallback: composite when single-scene quality insufficient."""

    def test_fallback_triggers_below_threshold(self, tmp_path: Path) -> None:
        """When best scene valid_fraction < COMPOSITE_THRESHOLD, composite is called."""
        low_quality = _mock_selected_scene("S2_before_1", "before", COMPOSITE_THRESHOLD - 0.1)
        good_after = _mock_selected_scene("S2_after_1", "after", 0.95)
        # Need 2+ before scenes for composite to kick in.
        low2 = _mock_selected_scene("S2_before_2", "before", 0.4)
        scenes = [low_quality, low2, good_after]

        window = _mock_raster_window()

        patches = _patch_pipeline_stages()
        with patches[0], patches[1] as mock_rank, patches[2] as mock_read, patches[3], \
             patches[4] as mock_composite, patches[5], patches[6], patches[7], patches[8], patches[9]:
            mock_rank.return_value = scenes
            mock_read.return_value = window
            mock_composite.return_value = window

            run_analysis(_request(), tmp_path / "output")

            assert mock_composite.called, "Composite should have been called when best scene < threshold"

    def test_no_fallback_when_single_scene_sufficient(self, tmp_path: Path) -> None:
        """When best scene valid_fraction >= COMPOSITE_THRESHOLD, composite is NOT called."""
        good_before = _mock_selected_scene("S2_before_1", "before", 0.95)
        good_after = _mock_selected_scene("S2_after_1", "after", 0.95)
        scenes = [good_before, good_after]

        window = _mock_raster_window()

        patches = _patch_pipeline_stages()
        with patches[0], patches[1] as mock_rank, patches[2] as mock_read, patches[3], \
             patches[4] as mock_composite, patches[5], patches[6], patches[7], patches[8], patches[9]:
            mock_rank.return_value = scenes
            mock_read.return_value = window

            run_analysis(_request(), tmp_path / "output")

            assert not mock_composite.called, "Composite should NOT be called when single scene is sufficient"

    def test_force_composite_always_composites(self, tmp_path: Path) -> None:
        """When force_composite=True, composite is used even with high quality scenes."""
        good_before = _mock_selected_scene("S2_before_1", "before", 0.99)
        good2 = _mock_selected_scene("S2_before_2", "before", 0.95)
        good_after = _mock_selected_scene("S2_after_1", "after", 0.99)
        good_after2 = _mock_selected_scene("S2_after_2", "after", 0.95)
        scenes = [good_before, good2, good_after, good_after2]

        window = _mock_raster_window()

        patches = _patch_pipeline_stages()
        with patches[0], patches[1] as mock_rank, patches[2] as mock_read, patches[3], \
             patches[4] as mock_composite, patches[5], patches[6], patches[7], patches[8], patches[9]:
            mock_rank.return_value = scenes
            mock_read.return_value = window
            mock_composite.return_value = window

            run_analysis(_request(), tmp_path / "output", force_composite=True)

            assert mock_composite.called, "Composite should be called when force_composite=True"
