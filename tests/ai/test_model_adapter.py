"""Tests for the ModelAdapter protocol and ModelResult dataclass.

Module: oberon/ai/model_adapter.py, oberon/core/__init__.py

These tests verify the contracts that any adapter implementation must
satisfy, without requiring torch or Clay to be installed.
"""

from __future__ import annotations

import numpy as np

from oberon.ai.model_adapter import ModelAdapter
from oberon.core import ModelResult

# ---------------------------------------------------------------------------
# ModelResult
# ---------------------------------------------------------------------------

class TestModelResult:
    """ModelResult: dataclass for AI inference output."""

    def test_construction_with_all_fields(self) -> None:
        """ModelResult should accept all fields and store them."""
        diff_map = np.zeros((10, 10), dtype=np.float32)
        score_map = np.ones((10, 10), dtype=np.float32) * 0.5
        result = ModelResult(
            feature_diff_map=diff_map,
            change_score_map=score_map,
            adapter_version="clay-v1.5-adapter-0.1",
            model_version="clay-v1.5",
            chip_count=4,
        )
        assert result.abstain is False
        assert result.abstain_reason is None
        assert result.adapter_version == "clay-v1.5-adapter-0.1"
        assert result.chip_count == 4

    def test_abstention_construction(self) -> None:
        """ModelResult should support abstention with None maps."""
        result = ModelResult(
            feature_diff_map=None,
            change_score_map=None,
            adapter_version="clay-v1.5-adapter-0.1",
            model_version="clay-v1.5",
            chip_count=0,
            abstain=True,
            abstain_reason="torch not installed",
        )
        assert result.abstain is True
        assert result.abstain_reason == "torch not installed"
        assert result.feature_diff_map is None
        assert result.change_score_map is None

    def test_defaults(self) -> None:
        """abstain defaults to False, abstain_reason to None."""
        result = ModelResult(
            feature_diff_map=None,
            change_score_map=None,
            adapter_version="test",
            model_version="test",
            chip_count=0,
        )
        assert result.abstain is False
        assert result.abstain_reason is None


# ---------------------------------------------------------------------------
# ModelAdapter protocol conformance
# ---------------------------------------------------------------------------

class _DummyAdapter:
    """Minimal adapter that satisfies the ModelAdapter protocol."""

    @property
    def version(self) -> str:
        return "dummy-0.1"

    @property
    def required_bands(self) -> list[str]:
        return ["B02", "B03", "B04"]

    @property
    def chip_size(self) -> int:
        return 64

    def extract_features(
        self,
        chip: np.ndarray,
        metadata: dict[str, object],
    ) -> np.ndarray:
        return np.ones(chip.shape[:2] + (8,), dtype=np.float32)

    def compute_feature_diff(
        self,
        before_features: np.ndarray,
        after_features: np.ndarray,
    ) -> np.ndarray:
        diff = np.linalg.norm(
            after_features - before_features, axis=-1,
        )
        return diff.astype(np.float32)


class TestModelAdapterProtocol:
    """ModelAdapter: protocol conformance checks."""

    def test_dummy_adapter_isinstance_of_protocol(self) -> None:
        """A class implementing all protocol members should pass isinstance."""
        adapter = _DummyAdapter()
        assert isinstance(adapter, ModelAdapter)

    def test_adapter_has_required_properties(self) -> None:
        """Adapter must expose version, required_bands, chip_size."""
        adapter = _DummyAdapter()
        assert isinstance(adapter.version, str)
        assert isinstance(adapter.required_bands, list)
        assert isinstance(adapter.chip_size, int)

    def test_extract_features_returns_array(self) -> None:
        """extract_features must return a numpy array."""
        adapter = _DummyAdapter()
        chip = np.ones((64, 64, 3), dtype=np.float32)
        features = adapter.extract_features(chip, {"month": 6})
        assert isinstance(features, np.ndarray)
        assert features.shape[:2] == (64, 64)

    def test_compute_feature_diff_returns_2d(self) -> None:
        """compute_feature_diff must return a (H, W) float32 array."""
        adapter = _DummyAdapter()
        before = np.ones((10, 10, 8), dtype=np.float32)
        after = np.ones((10, 10, 8), dtype=np.float32) * 2
        diff = adapter.compute_feature_diff(before, after)
        assert diff.shape == (10, 10)
        assert diff.dtype == np.float32

    def test_identical_features_yield_zero_diff(self) -> None:
        """Feature diff of identical arrays should be ~0 everywhere."""
        adapter = _DummyAdapter()
        features = np.random.randn(10, 10, 8).astype(np.float32)
        diff = adapter.compute_feature_diff(features, features)
        assert np.allclose(diff, 0.0, atol=1e-5)

    def test_different_features_yield_positive_diff(self) -> None:
        """Feature diff of different arrays should be positive."""
        adapter = _DummyAdapter()
        before = np.zeros((10, 10, 8), dtype=np.float32)
        after = np.ones((10, 10, 8), dtype=np.float32)
        diff = adapter.compute_feature_diff(before, after)
        assert np.all(diff > 0.0)
