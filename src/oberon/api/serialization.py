"""Serialization layer — transforms internal pipeline objects to API response shape.

Resolves the gaps identified in docs/api/gaps_vs_product_brief.md:
  - Gap 1: adds top-level status field
  - Gap 2: renames score -> change_score
  - Gap 4: converts area_ha -> changed_area_m2
  - Gap 5: restructures ndvi_delta_mean -> evidence.ndvi_delta
  - Gap 6: surfaces model version per-finding
  - Gap 8: resolves artifact paths
  - Gap 9: surfaces model_versions from provenance
  - Gap 10: artifact paths included in response

The Rust control plane will call the Python pipeline via subprocess, receive an
EvidenceBundle on disk, and use this serialization (or its Rust equivalent) to
produce the API response.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from oberon.api.contracts import (
    APIFinding,
    ArtifactPaths,
    ChangeResponse,
    EvidenceMetrics,
    ModelInfo,
    ResponseStatus,
)
from oberon.core import EvidenceBundle, Finding

# 1 hectare = 10,000 square meters.
HA_TO_M2 = 10_000.0


def serialize_findings(
    findings: list[Finding],
    model_versions: list[str] | None = None,
) -> list[APIFinding]:
    """Convert internal Finding objects to API response shape.

    Args:
        findings: Internal Finding dataclasses from the pipeline.
        model_versions: Model version strings from provenance. The primary
            (first) model version is used as the encoder for all findings.

    Returns:
        List of APIFinding matching the Product Brief §5 shape.
    """
    if not findings:
        return []

    # Determine encoder. Use the first model version (primary model).
    # ponytail: single-encoder assumption. Upgrade path: per-finding model
    # tracking when mixed-model runs become possible.
    encoder = (model_versions or ["deterministic-v1"])[0]

    return [
        APIFinding(
            geometry=f.geometry,
            change_score=f.score,
            suggested_class=None,  # No task head yet (gap 3, deferred)
            changed_area_m2=f.area_ha * HA_TO_M2,
            evidence=EvidenceMetrics(
                ndvi_delta=f.ndvi_delta_mean,
                nbr_delta=f.nbr_delta_mean,
            ),
            model=ModelInfo(
                encoder=encoder,
                confidence=None,  # Uncalibrated (gap 7, deferred)
            ),
        )
        for f in findings
    ]


def _resolve_artifact_path(path: Path) -> str:
    """Convert a local Path to a string for the API response.

    The Rust control plane resolves these to URLs when serving via HTTP.
    For CLI usage, the path string is returned directly.
    """
    return str(path)


def serialize_bundle_to_response(
    bundle: EvidenceBundle,
    findings: list[Finding] | None = None,
) -> ChangeResponse:
    """Transform an EvidenceBundle into the canonical API ChangeResponse.

    This is the primary serialization entry point. It reads provenance from the
    bundle, extracts findings from provenance if not provided directly, and
    builds the Product Brief §5 response shape.

    Args:
        bundle: The pipeline output EvidenceBundle.
        findings: Optional explicit Finding list. If None, findings are
            reconstructed from the provenance manifest.

    Returns:
        ChangeResponse matching the Product Brief §5 shape.
    """
    provenance: dict[str, Any] = bundle.provenance
    model_versions: list[str] = provenance.get("model_versions", ["deterministic-v1"])

    # Determine status from provenance.
    abstention = provenance.get("abstention")
    if abstention and abstention.get("reason"):
        return ChangeResponse(
            status=ResponseStatus.ABSTAINED,
            findings=[],
            artifacts=ArtifactPaths(
                before=_resolve_artifact_path(bundle.before_image),
                after=_resolve_artifact_path(bundle.after_image),
                overlay=_resolve_artifact_path(bundle.overlay_image),
            ),
        )

    # Serialize findings.
    if findings is not None:
        api_findings = serialize_findings(findings, model_versions)
    else:
        api_findings = _findings_from_provenance(provenance, model_versions)

    return ChangeResponse(
        status=ResponseStatus.REVIEW,
        findings=api_findings,
        artifacts=ArtifactPaths(
            before=_resolve_artifact_path(bundle.before_image),
            after=_resolve_artifact_path(bundle.after_image),
            overlay=_resolve_artifact_path(bundle.overlay_image),
        ),
    )


def _findings_from_provenance(
    provenance: dict[str, Any],
    model_versions: list[str],
) -> list[APIFinding]:
    """Reconstruct APIFindings from the provenance manifest.

    Used when Finding objects are not available (e.g., reading from disk).
    """
    raw_findings: list[dict[str, Any]] = provenance.get("findings", [])
    if not raw_findings:
        return []

    encoder = model_versions[0] if model_versions else "deterministic-v1"

    return [
        APIFinding(
            geometry={"type": "Polygon", "coordinates": []},  # Geometry is in the GeoJSON file
            change_score=f["score"],
            suggested_class=None,
            changed_area_m2=f["area_ha"] * HA_TO_M2,
            evidence=EvidenceMetrics(
                ndvi_delta=f["metrics"]["ndvi_delta_mean"],
                nbr_delta=f["metrics"]["nbr_delta_mean"],
            ),
            model=ModelInfo(encoder=encoder, confidence=None),
        )
        for f in raw_findings
    ]
