"""Model registry — versioned entries for every model used in the pipeline.

Every finding's provenance records which model(s) produced it. Deterministic
baselines are registered as "deterministic-v1" so they have the same
provenance status as AI models. No model is used without being registered.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class ModelEntry:
    """A registered model with version metadata."""

    version: str
    type: str  # "deterministic" | "foundation_model"
    stages: list[str] = field(default_factory=list)  # e.g. ["ndvi", "nbr", "ndmi", "pixel_delta"]
    adapter: str | None = None  # e.g. "oberon.ai.clay_adapter.ClayAdapter"
    required_bands: list[str] = field(default_factory=list)
    chip_size: int | None = None


REGISTERED_MODELS: dict[str, ModelEntry] = {
    "deterministic-v1": ModelEntry(
        version="deterministic-v1",
        type="deterministic",
        stages=["ndvi", "nbr", "ndmi", "pixel_delta"],
    ),
    "clay-v1.5": ModelEntry(
        version="clay-v1.5",
        type="foundation_model",
        adapter="oberon.ai.clay_adapter.ClayAdapter",
        required_bands=["B02", "B03", "B04", "B05", "B06", "B07", "B08", "B8A", "B11", "B12"],
        chip_size=256,
    ),
}


def get_model_entry(version: str) -> ModelEntry:
    """Look up a model entry by version string.

    Raises KeyError if the version is not registered.
    """
    if version not in REGISTERED_MODELS:
        raise KeyError(f"Model version '{version}' not in registry. Registered: {list(REGISTERED_MODELS)}")
    return REGISTERED_MODELS[version]


def model_entry_to_dict(entry: ModelEntry) -> dict[str, Any]:
    """Serialize a ModelEntry to a JSON-safe dict for provenance."""
    return {
        "version": entry.version,
        "type": entry.type,
        "stages": entry.stages,
        "adapter": entry.adapter,
        "required_bands": entry.required_bands,
        "chip_size": entry.chip_size,
    }
