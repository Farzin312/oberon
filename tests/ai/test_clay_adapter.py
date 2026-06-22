"""Tests for the Clay adapter — mocked model, real feature-diff logic.

Module: oberon/ai/clay_adapter.py

These tests verify adapter protocol conformance and the feature-diff math
without loading the 5GB Clay checkpoint.
"""

from __future__ import annotations

import numpy as np

from oberon.ai.clay_adapter import ADAPTER_VERSION, ClayAdapter


class TestClayAdapterProtocol:
    """ClayAdapter: protocol conformance and metadata."""

    def test_adapter_has_correct_version(self) -> None:
        adapter = ClayAdapter()
        assert adapter.version == ADAPTER_VERSION

    def test_adapter_has_required_bands(self) -> None:
        adapter = ClayAdapter()
        bands = adapter.required_bands
        assert len(bands) == 12
        assert "B02" in bands
        assert "B04" in bands
        assert "B08" in bands
        assert "B12" in bands

    def test_adapter_chip_size(self) -> None:
        adapter = ClayAdapter()
        assert adapter.chip_size == 256


class TestFeatureDiff:
    """compute_feature_diff: L2 distance between patch embeddings."""

    def test_identical_features_yield_zero(self) -> None:
        """Identical before/after features should produce zero diff."""
        adapter = ClayAdapter()
        features = np.ones((100, 64), dtype=np.float32)
        diff = adapter.compute_feature_diff(features, features)
        assert diff.shape == (100,)
        assert np.allclose(diff, 0.0)

    def test_different_features_yield_positive(self) -> None:
        """Different features should produce positive diff."""
        adapter = ClayAdapter()
        before = np.zeros((50, 32), dtype=np.float32)
        after = np.ones((50, 32), dtype=np.float32) * 3.0
        diff = adapter.compute_feature_diff(before, after)
        assert diff.shape == (50,)
        # L2 norm of (3, 3, ..., 3) across 32 dims = 3 * sqrt(32)
        assert np.allclose(diff, 3.0 * np.sqrt(32))

    def test_partial_difference(self) -> None:
        """Only some patches differ — only those should have positive diff."""
        adapter = ClayAdapter()
        before = np.zeros((4, 8), dtype=np.float32)
        after = before.copy()
        after[1] = 5.0  # Only patch 1 differs
        diff = adapter.compute_feature_diff(before, after)
        assert diff[0] == 0.0
        assert diff[1] > 0.0
        assert diff[2] == 0.0
        assert diff[3] == 0.0


class TestNormalizeDiffMap:
    """normalize_diff_map: min-max normalization to [0, 1]."""

    def test_normalization_range(self) -> None:
        diff = np.array([0.0, 5.0, 10.0], dtype=np.float32)
        normalized = ClayAdapter.normalize_diff_map(diff)
        assert normalized.min() == 0.0
        assert normalized.max() == 1.0

    def test_constant_array_returns_zeros(self) -> None:
        diff = np.full(10, 5.0, dtype=np.float32)
        normalized = ClayAdapter.normalize_diff_map(diff)
        assert np.allclose(normalized, 0.0)

    def test_preserves_order(self) -> None:
        diff = np.array([1.0, 3.0, 2.0], dtype=np.float32)
        normalized = ClayAdapter.normalize_diff_map(diff)
        # 1.0 -> 0.0, 3.0 -> 1.0, 2.0 -> 0.5
        assert normalized[0] < normalized[2] < normalized[1]
