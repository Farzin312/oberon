"""Tests for the model registry (006 Phase 0)."""

from __future__ import annotations

import pytest

from oberon.config.model_registry import (
    REGISTERED_MODELS,
    get_model_entry,
    model_entry_to_dict,
)


class TestModelRegistry:
    """REGISTERED_MODELS: all expected entries present."""

    def test_has_deterministic_v1(self) -> None:
        assert "deterministic-v1" in REGISTERED_MODELS
        entry = REGISTERED_MODELS["deterministic-v1"]
        assert entry.type == "deterministic"
        assert "ndvi" in entry.stages
        assert "nbr" in entry.stages
        assert "pixel_delta" in entry.stages

    def test_has_clay_v15(self) -> None:
        assert "clay-v1.5" in REGISTERED_MODELS
        entry = REGISTERED_MODELS["clay-v1.5"]
        assert entry.type == "foundation_model"
        assert entry.adapter is not None
        assert "clay_adapter" in entry.adapter
        assert entry.chip_size == 256
        assert len(entry.required_bands) == 10

    def test_deterministic_has_no_adapter(self) -> None:
        entry = REGISTERED_MODELS["deterministic-v1"]
        assert entry.adapter is None

    def test_deterministic_has_no_chip_size(self) -> None:
        entry = REGISTERED_MODELS["deterministic-v1"]
        assert entry.chip_size is None


class TestGetModelEntry:
    """get_model_entry: lookup by version string."""

    def test_valid_lookup(self) -> None:
        entry = get_model_entry("deterministic-v1")
        assert entry.version == "deterministic-v1"

    def test_invalid_lookup_raises(self) -> None:
        with pytest.raises(KeyError, match="not in registry"):
            get_model_entry("nonexistent-v99")


class TestModelEntryToDict:
    """model_entry_to_dict: serialization for provenance."""

    def test_serializes_all_fields(self) -> None:
        entry = REGISTERED_MODELS["clay-v1.5"]
        d = model_entry_to_dict(entry)
        assert d["version"] == "clay-v1.5"
        assert d["type"] == "foundation_model"
        assert d["chip_size"] == 256
        assert isinstance(d["required_bands"], list)

    def test_serializes_deterministic(self) -> None:
        entry = REGISTERED_MODELS["deterministic-v1"]
        d = model_entry_to_dict(entry)
        assert d["adapter"] is None
        assert d["chip_size"] is None
        assert "ndvi" in d["stages"]


class TestModelEntryFrozen:
    """ModelEntry is frozen — immutable after creation."""

    def test_cannot_mutate(self) -> None:
        import dataclasses

        entry = get_model_entry("deterministic-v1")
        with pytest.raises(dataclasses.FrozenInstanceError):
            entry.version = "hacked"  # type: ignore[misc]
