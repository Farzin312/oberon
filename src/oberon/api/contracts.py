"""API contracts — Pydantic models matching the Product Brief §5 response shape.

These models define the canonical JSON contract between the Python pipeline and
any control plane (Rust Axum, or a future HTTP wrapper). The gap analysis in
docs/api/gaps_vs_product_brief.md identifies 10 gaps between the internal
EvidenceBundle shape and this target shape; this module resolves gaps 1, 2, 4,
5, 6, 8, 9, 10.

Gaps 3 (suggested_class) and 7 (calibrated confidence) are deferred — they
require a trained task head. suggested_class is Optional[None] and confidence is
None by default, matching the Product Brief pattern.
"""

from __future__ import annotations

from datetime import date
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field, field_validator, model_validator


class ResponseStatus(StrEnum):
    """Top-level response status matching Product Brief §5."""

    REVIEW = "review_recommended"
    ABSTAINED = "abstained"
    FAILED = "failed"


class TimeWindow(BaseModel):
    """A date range for scene selection."""

    from_: date = Field(..., alias="from")
    to: date

    model_config = {"populate_by_name": True}

    @model_validator(mode="after")
    def validate_order(self) -> TimeWindow:
        if self.from_ > self.to:
            raise ValueError("TimeWindow 'from' must be before or equal to 'to'")
        return self


class ChangeRequestAPI(BaseModel):
    """POST /v1/change request body.

    Matches the Product Brief §5 request shape. The Rust control plane will
    deserialize this and spawn the Python pipeline.
    """

    geometry: dict[str, Any] = Field(..., description="GeoJSON Polygon or MultiPolygon")
    before: TimeWindow
    after: TimeWindow
    task: str = "vegetation_disturbance"
    max_cloud_fraction: float = 0.15

    @field_validator("geometry")
    @classmethod
    def validate_geometry_non_empty(cls, v: dict[str, Any]) -> dict[str, Any]:
        if not v or "type" not in v:
            raise ValueError("geometry must be a GeoJSON geometry with a 'type' field")
        return v

    @model_validator(mode="after")
    def validate_date_order(self) -> ChangeRequestAPI:
        if self.before.to >= self.after.from_:
            raise ValueError("'before' window must end before 'after' window starts")
        return self


class EvidenceMetrics(BaseModel):
    """Spectral evidence for a finding — uses Product Brief field names."""

    ndvi_delta: float
    nbr_delta: float


class ModelInfo(BaseModel):
    """Per-finding model metadata. Confidence is null until calibrated."""

    encoder: str
    confidence: float | None = None


class APIFinding(BaseModel):
    """A single change finding in the API response shape.

    Field names match the Product Brief, NOT the internal Finding dataclass:
    - change_score (not score)
    - changed_area_m2 (not area_ha)
    - evidence.ndvi_delta (not ndvi_delta_mean)
    """

    geometry: dict[str, Any]
    change_score: float
    suggested_class: str | None = None
    changed_area_m2: float
    evidence: EvidenceMetrics
    model: ModelInfo


class ArtifactPaths(BaseModel):
    """Artifact URLs or paths. URLs when served via API, paths for CLI."""

    before: str
    after: str
    overlay: str


class ChangeResponse(BaseModel):
    """POST /v1/change response body — the canonical output shape.

    This is what the Rust API returns. The serialization layer
    (serialization.py) transforms an EvidenceBundle into this shape.
    """

    status: ResponseStatus
    findings: list[APIFinding]
    artifacts: ArtifactPaths
