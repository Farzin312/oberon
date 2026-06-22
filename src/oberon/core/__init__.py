"""Core domain models for the Oberon pipeline.

All data that crosses pipeline stage boundaries is represented by one of these
dataclasses. They are the contracts between stages — if you change a field here,
update all consumers.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Any

import numpy as np


@dataclass
class ChangeRequest:
    """A user's request to analyze an area of interest for change."""

    geometry: dict[str, Any]  # GeoJSON Polygon geometry dict
    before: tuple[date, date]  # (from, to) date window
    after: tuple[date, date]
    task: str = "vegetation_disturbance"
    max_cloud_fraction: float = 0.15
    min_valid_pixels: float = 0.30
    min_change_area_ha: float = 0.5


@dataclass
class CandidateScene:
    """A candidate observation returned by a STAC catalog search."""

    stac_item_id: str
    datetime: datetime
    geometry: dict[str, Any]
    bbox: tuple[float, float, float, float]
    assets: dict[str, str]  # band name -> COG URL
    scl_url: str | None
    scene_cloud_pct: float


@dataclass
class SelectedScene:
    """A scene selected as the best representation for one time period."""

    candidate: CandidateScene
    local_valid_fraction: float
    period: str  # "before" or "after"


@dataclass
class RasterWindow:
    """A windowed read result from a COG, containing requested bands."""

    data: dict[str, np.ndarray]  # band -> 2D array
    crs: str
    transform: tuple[float, ...]
    bounds: tuple[float, float, float, float]
    scl_mask: np.ndarray | None  # boolean, True = valid pixel


@dataclass
class PreparedPair:
    """Aligned before/after arrays ready for comparison."""

    before: dict[str, np.ndarray]
    after: dict[str, np.ndarray]
    mask: np.ndarray  # boolean, True = valid in both
    crs: str
    transform: tuple[float, ...]
    bounds: tuple[float, float, float, float]

    @property
    def valid_fraction(self) -> float:
        """Fraction of pixels that are valid (not masked) in the AOI."""
        if self.mask.size == 0:
            return 0.0
        return float(self.mask.sum()) / self.mask.size

    @property
    def is_usable(self) -> bool:
        """At least 30% of the AOI must be valid in both observations."""
        return self.valid_fraction >= 0.30


@dataclass
class BaselineResult:
    """Output of deterministic baseline computation."""

    ndvi_diff: np.ndarray | None
    nbr_diff: np.ndarray | None
    ndmi_diff: np.ndarray | None
    pixel_delta_magnitude: np.ndarray | None
    valid_pixels_before: int
    valid_pixels_after: int
    abstain: bool = False
    abstain_reason: str | None = None


@dataclass
class Finding:
    """A single detected change region with metrics."""

    geometry: dict[str, Any]  # GeoJSON Polygon
    score: float
    area_ha: float
    ndvi_delta_mean: float
    nbr_delta_mean: float
    valid_pixels_in_finding: int


@dataclass
class EvidenceBundle:
    """Packaged output artifacts for a single analysis run."""

    output_dir: Path
    before_image: Path
    after_image: Path
    overlay_image: Path
    findings_geojson: Path
    provenance_manifest: Path
    provenance: dict[str, Any]


SENTINEL2_L2A_BANDS = ["B01", "B02", "B03", "B04", "B05", "B06", "B07", "B08", "B8A", "B11", "B12"]
"""Standard Sentinel-2 L2A bands used in the 10m/20m stack."""

TRUE_COLOR_BANDS = ["B04", "B03", "B02"]
"""Red, Green, Blue for true-color composites."""

CLAY_BANDS = ["B02", "B03", "B04", "B05", "B06", "B07", "B08", "B8A", "B11", "B12"]
"""10-band subset used by Clay v1.5 for inference."""

SCL_CLOUD_BITS = {1, 3, 7, 8, 9, 10, 11}
"""SCL values that indicate invalid/obstructed pixels (saturated, cloud shadow, cloud, cirrus, snow/ice)."""
