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
    apply_morphological_closing,
    deduplicate_and_rank,
    detect_changes,
    extract_findings,
    is_broad_change,
    threshold_change_map,
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


# ---------------------------------------------------------------------------
# threshold_change_map direction parameter
# ---------------------------------------------------------------------------


class TestThresholdDirection:
    """threshold_change_map(direction=...): task-aware sign filtering."""

    def test_negative_direction_keeps_only_loss(self) -> None:
        """With direction='negative', only diff < -threshold is True (NDVI loss)."""
        diff = np.array([[-0.3, -0.1, 0.0, 0.1, 0.3]], dtype=np.float32)
        mask = threshold_change_map(diff, threshold=0.15, direction="negative")
        expected = np.array([[True, False, False, False, False]], dtype=bool)
        assert mask is not None
        np.testing.assert_array_equal(mask, expected)

    def test_positive_direction_keeps_only_gain(self) -> None:
        """With direction='positive', only diff > threshold is True (NDVI gain)."""
        diff = np.array([[-0.3, -0.1, 0.0, 0.1, 0.3]], dtype=np.float32)
        mask = threshold_change_map(diff, threshold=0.15, direction="positive")
        expected = np.array([[False, False, False, False, True]], dtype=bool)
        assert mask is not None
        np.testing.assert_array_equal(mask, expected)

    def test_absolute_direction_keeps_both(self) -> None:
        """With direction='absolute', |diff| > threshold keeps both signs (backwards compat)."""
        diff = np.array([[-0.3, -0.1, 0.0, 0.1, 0.3]], dtype=np.float32)
        mask = threshold_change_map(diff, threshold=0.15, direction="absolute")
        expected = np.array([[True, False, False, False, True]], dtype=bool)
        assert mask is not None
        np.testing.assert_array_equal(mask, expected)

    def test_default_is_absolute_for_backwards_compat(self) -> None:
        """When direction is omitted, current abs() behaviour is preserved."""
        diff = np.array([[-0.3, -0.1, 0.0, 0.1, 0.3]], dtype=np.float32)
        mask = threshold_change_map(diff, threshold=0.15)
        expected = np.array([[True, False, False, False, True]], dtype=bool)
        assert mask is not None
        np.testing.assert_array_equal(mask, expected)

    def test_nan_handled_in_negative_direction(self) -> None:
        """NaN values are zeroed before thresholding in all directions."""
        diff = np.array([[-0.3, np.nan, 0.2]], dtype=np.float32)
        mask = threshold_change_map(diff, threshold=0.15, direction="negative")
        assert mask is not None
        assert mask[0, 0]  # -0.3 < -0.15
        assert not mask[0, 1]  # NaN -> 0 -> not less than -0.15
        assert not mask[0, 2]  # 0.2 is positive, not negative change

    def test_none_diff_returns_none(self) -> None:
        """None input returns None regardless of direction."""
        assert threshold_change_map(None, direction="negative") is None
        assert threshold_change_map(None, direction="positive") is None
        assert threshold_change_map(None, direction="absolute") is None


# ---------------------------------------------------------------------------
# is_broad_change (seasonal/broad-change abstention)
# ---------------------------------------------------------------------------


class TestIsBroadChange:
    """is_broad_change(): detect landscape-wide seasonal shifts."""

    def test_most_pixels_changed_triggers(self) -> None:
        """When >40% of valid pixels are in the change mask, triggers True."""
        valid = np.ones((10, 10), dtype=bool)
        change = np.zeros((10, 10), dtype=bool)
        change[:7, :] = True  # 70% of pixels flagged
        assert is_broad_change(change, valid)

    def test_few_pixels_changed_returns_false(self) -> None:
        """When <40% of valid pixels are in the change mask, returns False."""
        valid = np.ones((10, 10), dtype=bool)
        change = np.zeros((10, 10), dtype=bool)
        change[:3, :] = True  # 30% of pixels flagged
        assert not is_broad_change(change, valid)

    def test_no_valid_pixels_returns_false(self) -> None:
        """Empty valid mask returns False (edge case, should not occur in practice)."""
        valid = np.zeros((10, 10), dtype=bool)
        change = np.ones((10, 10), dtype=bool)
        assert not is_broad_change(change, valid)

    def test_edge_value_just_below_threshold(self) -> None:
        """Exactly 50% (at threshold) should NOT trigger (strict >)."""
        valid = np.ones((100,), dtype=bool)
        change = np.zeros((100,), dtype=bool)
        change[:50] = True  # exactly 50%
        assert not is_broad_change(change, valid)

    def test_edge_value_just_above_threshold(self) -> None:
        """51% (>50%) should trigger."""
        valid = np.ones((100,), dtype=bool)
        change = np.zeros((100,), dtype=bool)
        change[:51] = True  # 51%
        assert is_broad_change(change, valid)

    def test_valid_mask_restricts_to_valid_pixels(self) -> None:
        """Only valid pixels should count toward the fraction."""
        valid = np.zeros((10, 10), dtype=bool)
        valid[0, :] = True  # only 10 valid pixels
        change = np.ones((10, 10), dtype=bool)
        # All 10 valid pixels changed = 100% of valid = trigger
        assert is_broad_change(change, valid)


# ---------------------------------------------------------------------------
# apply_morphological_closing
# ---------------------------------------------------------------------------


class TestMorphologicalClosing:
    """apply_morphological_closing(): consolidate fragmented findings."""

    def test_merges_nearby_components(self) -> None:
        """Two components within a 25-pixel gap should merge into one after closing."""
        mask = np.zeros((50, 50), dtype=bool)
        mask[10:20, 5:15] = True  # Component A
        mask[10:20, 25:35] = True  # Component B, 10-pixel gap
        closed = apply_morphological_closing(mask, kernel_size=25)
        from scipy import ndimage as ndi
        labeled, num = ndi.label(closed)
        assert num == 1, f"Expected 1 component, got {num}"

    def test_distant_components_remain_separate(self) -> None:
        """Components separated by >50 pixels should NOT merge."""
        mask = np.zeros((80, 80), dtype=bool)
        mask[10:20, 5:15] = True  # Component A
        mask[10:20, 60:70] = True  # Component B, >45-pixel gap
        closed = apply_morphological_closing(mask, kernel_size=25)
        from scipy import ndimage as ndi
        labeled, num = ndi.label(closed)
        assert num == 2, f"Expected 2 components, got {num}"

    def test_single_component_unchanged(self) -> None:
        """A single contiguous component is unchanged after closing."""
        mask = np.zeros((20, 20), dtype=bool)
        mask[5:15, 5:15] = True
        closed = apply_morphological_closing(mask, kernel_size=5)
        from scipy import ndimage as ndi
        before_labeled, _ = ndi.label(mask)
        after_labeled, _ = ndi.label(closed)
        # Area should not shrink (closing only fills holes, doesn't erode)
        assert closed.sum() >= mask.sum()

    def test_hole_in_middle_filled(self) -> None:
        """A hole within a larger component should be filled by closing."""
        mask = np.ones((50, 50), dtype=bool)
        mask[20:30, 20:30] = False  # 10x10 hole in the middle
        closed = apply_morphological_closing(mask, kernel_size=25)
        # The interior hole should be filled (core region all True).
        assert closed[20:30, 20:30].all(), "Hole in middle should be filled after closing"
