"""Tests for change detection — thresholding, components, ranking, orchestration.

Module: oberon/core/change_detection.py

Each test class covers one public function. Every test method has a
docstring explaining what behaviour it validates. Edge cases and
failure modes are tested explicitly.
"""

from __future__ import annotations

import numpy as np
import pytest

from oberon.core import Finding, PreparedPair
from oberon.core.change_detection import (
    deduplicate_and_rank,
    detect_changes,
    extract_findings,
)

# ---------------------------------------------------------------------------
# extract_findings
# ---------------------------------------------------------------------------

class TestExtractFindings:
    """extract_findings(): convert a binary change mask into Finding records."""

    def test_all_false_mask_returns_empty(self) -> None:
        """An entirely-False change mask has no components and yields no findings."""
        change_mask = np.zeros((30, 30), dtype=bool)
        ndvi_diff = np.zeros((30, 30), dtype=np.float32)
        assert extract_findings(change_mask, ndvi_diff) == []

    def test_single_block_component_produces_one_finding(self) -> None:
        """A single 10x10 (100px) block with a non-zero ndvi_diff yields one Finding whose area_ha == pixel_count * 0.01."""
        change_mask = np.zeros((30, 30), dtype=bool)
        change_mask[5:15, 5:15] = True  # 100 pixels
        ndvi_diff = np.full((30, 30), 0.3, dtype=np.float32)
        findings = extract_findings(change_mask, ndvi_diff)
        assert len(findings) == 1
        assert findings[0].area_ha == pytest.approx(100 * 0.01)
        assert findings[0].valid_pixels_in_finding == 100

    def test_only_one_component_above_min_pixels_returned(self) -> None:
        """When multiple components exist but only one exceeds min_pixels, exactly one Finding is returned."""
        change_mask = np.zeros((50, 50), dtype=bool)
        # big component: 10x10 = 100px (>= 50)
        change_mask[5:15, 5:15] = True
        # small component: 5x5 = 25px (< 50)
        change_mask[40:45, 40:45] = True
        ndvi_diff = np.full((50, 50), 0.3, dtype=np.float32)
        findings = extract_findings(change_mask, ndvi_diff)
        assert len(findings) == 1

    def test_component_of_exactly_49_pixels_is_filtered(self) -> None:
        """A component with 49 pixels (below default min_pixels=50) yields zero findings."""
        change_mask = np.zeros((50, 50), dtype=bool)
        # 49 pixels via a non-rectangular blob
        change_mask[0:7, 0:7] = True  # 49 px
        ndvi_diff = np.full((50, 50), 0.3, dtype=np.float32)
        assert extract_findings(change_mask, ndvi_diff) == []


# ---------------------------------------------------------------------------
# deduplicate_and_rank
# ---------------------------------------------------------------------------

class TestDeduplicateAndRank:
    """deduplicate_and_rank(): filter zero-score, sort by score, cap to max_findings."""

    def test_returns_findings_sorted_by_score_desc(self) -> None:
        """Findings should be sorted by score in descending order."""
        findings = [
            Finding(geometry={"type": "Polygon", "coordinates": [[]]}, score=0.2,
                    area_ha=0.5, ndvi_delta_mean=0.1, nbr_delta_mean=0.0, valid_pixels_in_finding=50),
            Finding(geometry={"type": "Polygon", "coordinates": [[]]}, score=0.9,
                    area_ha=0.5, ndvi_delta_mean=0.4, nbr_delta_mean=0.0, valid_pixels_in_finding=50),
            Finding(geometry={"type": "Polygon", "coordinates": [[]]}, score=0.5,
                    area_ha=0.5, ndvi_delta_mean=0.2, nbr_delta_mean=0.0, valid_pixels_in_finding=50),
        ]
        ranked = deduplicate_and_rank(findings)
        assert [f.score for f in ranked] == [0.9, 0.5, 0.2]

    def test_caps_at_max_findings(self) -> None:
        """With 25 distinct-score findings and max_findings=20, the result is capped to 20 (the top 20 by score)."""
        findings = [
            Finding(geometry={"type": "Polygon", "coordinates": [[]]}, score=i / 100.0,
                    area_ha=0.5, ndvi_delta_mean=0.1, nbr_delta_mean=0.0, valid_pixels_in_finding=50)
            for i in range(1, 26)
        ]
        ranked = deduplicate_and_rank(findings, max_findings=20)
        assert len(ranked) == 20
        assert ranked[0].score == pytest.approx(0.25)

    def test_all_zero_scores_returns_empty(self) -> None:
        """When every finding has score == 0.0, the result is empty (all dropped)."""
        findings = [
            Finding(geometry={"type": "Polygon", "coordinates": [[]]}, score=0.0,
                    area_ha=0.5, ndvi_delta_mean=0.0, nbr_delta_mean=0.0, valid_pixels_in_finding=50),
            Finding(geometry={"type": "Polygon", "coordinates": [[]]}, score=0.0,
                    area_ha=0.5, ndvi_delta_mean=0.0, nbr_delta_mean=0.0, valid_pixels_in_finding=50),
        ]
        assert deduplicate_and_rank(findings) == []


# ---------------------------------------------------------------------------
# _component_to_geojson_polygon (via extract_findings geometry)
# ---------------------------------------------------------------------------

class TestComponentGeometry:
    """Verify the geometry produced for a finding is a valid closed GeoJSON Polygon."""

    def test_geometry_is_valid_closed_polygon(self) -> None:
        """A 2D 10x10 blob should produce a GeoJSON Polygon with a closed exterior ring of >=4 points."""
        change_mask = np.zeros((30, 30), dtype=bool)
        change_mask[5:15, 5:15] = True  # 2D block -> convex hull is a real Polygon
        ndvi_diff = np.full((30, 30), 0.3, dtype=np.float32)
        findings = extract_findings(change_mask, ndvi_diff)
        assert len(findings) == 1
        geom = findings[0].geometry
        assert geom["type"] == "Polygon"
        ring = geom["coordinates"][0]
        assert len(ring) >= 4
        assert ring[0] == ring[-1]  # closed exterior ring


# ---------------------------------------------------------------------------
# detect_changes (orchestrator smoke test)
# ---------------------------------------------------------------------------

class TestDetectChanges:
    """detect_changes(): thin orchestrator tying baselines + thresholding + extraction + ranking."""

    def _make_pair(self, mask_fraction: float = 1.0) -> PreparedPair:
        """Build a PreparedPair with a clear NDVI shift in a block, for the smoke test."""
        h, w = 30, 30
        # before: healthy vegetation (high NIR, low red) -> high NDVI
        nir_before = np.full((h, w), 0.6, dtype=np.float32)
        red_before = np.full((h, w), 0.1, dtype=np.float32)
        # after: bare soil in a block -> NDVI drops by > 0.15
        nir_after = np.full((h, w), 0.6, dtype=np.float32)
        red_after = np.full((h, w), 0.1, dtype=np.float32)
        nir_after[5:20, 5:20] = 0.15  # big drop in NIR over the block
        red_after[5:20, 5:20] = 0.25
        mask = np.zeros((h, w), dtype=bool)
        if mask_fraction >= 1.0:
            mask[:] = True
        else:
            # set roughly mask_fraction of pixels True
            n_true = int(mask_fraction * mask.size)
            mask.flat[:n_true] = True
        return PreparedPair(
            before={"B04": red_before, "B08": nir_before},
            after={"B04": red_after, "B08": nir_after},
            mask=mask,
            crs="EPSG:32617",
            transform=(10.0, 0.0, 0.0, 0.0, 10.0, 0.0),
            bounds=(0.0, 0.0, 300.0, 300.0),
        )

    def test_usable_pair_returns_findings(self) -> None:
        """A usable pair with a clear NDVI shift should return a non-empty list of Finding."""
        pair = self._make_pair(mask_fraction=1.0)
        findings = detect_changes(pair)
        assert isinstance(findings, list)
        assert len(findings) >= 1
        assert all(isinstance(f, Finding) for f in findings)

    def test_non_usable_pair_returns_empty(self) -> None:
        """A pair with only ~20% valid pixels (below the 0.30 usability threshold) abstains and returns []."""
        pair = self._make_pair(mask_fraction=0.2)
        assert detect_changes(pair) == []
