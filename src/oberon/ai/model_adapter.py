"""ModelAdapter protocol — the contract between the pipeline and any AI model.

Implementations (ClayAdapter, future models) conform to this protocol.
The orchestrator uses duck typing — it never imports the concrete adapter
directly, only the protocol.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

import numpy as np


@runtime_checkable
class ModelAdapter(Protocol):
    """Protocol for AI model adapters.

    Every adapter must expose:
    - version: adapter implementation version (e.g. "clay-v1.5-adapter-0.1")
    - required_bands: ordered list of band names the model expects
    - chip_size: spatial dimension of a single inference chip (e.g. 256)
    - extract_features: produce an embedding from a chip
    """

    @property
    def version(self) -> str: ...

    @property
    def required_bands(self) -> list[str]: ...

    @property
    def chip_size(self) -> int: ...

    def extract_features(
        self,
        chip: np.ndarray,  # (H, W, B) — H == W == chip_size, B == len(required_bands)
        metadata: dict[str, object],  # month, crs, etc.
    ) -> np.ndarray:
        """Extract features from a single chip.

        Returns a 1-D embedding vector. Raises if the model cannot run.
        """
        ...

    def compute_feature_diff(
        self,
        before_features: np.ndarray,  # (H, W, D) — feature map
        after_features: np.ndarray,  # (H, W, D)
    ) -> np.ndarray:
        """Compute pixel-wise feature distance between before/after.

        Returns (H, W) float32. NOT a probability. Called "change_score"
        everywhere in code and docs.
        """
        ...
