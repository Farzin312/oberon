"""Tests for the API contract layer (008 pre-work).

Verifies that the Pydantic models in api/contracts.py match the Product Brief §5
response shape, and that the serialization layer transforms EvidenceBundle +
Finding objects into the API response correctly.

These tests are the contract specification. If they fail, the API layer is wrong.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from pydantic import ValidationError

from oberon.api.contracts import (
    APIFinding,
    ArtifactPaths,
    ChangeRequestAPI,
    ChangeResponse,
    EvidenceMetrics,
    ModelInfo,
    ResponseStatus,
)
from oberon.api.serialization import (
    serialize_bundle_to_response,
    serialize_findings,
)
from oberon.core import EvidenceBundle, Finding

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_finding(
    score: float = 0.72,
    area_ha: float = 2.3,
    ndvi: float = -0.32,
    nbr: float = -0.45,
) -> Finding:
    return Finding(
        geometry={"type": "Polygon", "coordinates": [[[0, 0], [0, 1], [1, 1], [1, 0], [0, 0]]]},
        score=score,
        area_ha=area_ha,
        ndvi_delta_mean=ndvi,
        nbr_delta_mean=nbr,
        valid_pixels_in_finding=100,
        pixel_delta_mean=0.15,
    )


def _make_bundle(
    findings: list[Finding] | None = None,
    abstention_reason: str | None = None,
    model_versions: list[str] | None = None,
) -> EvidenceBundle:
    findings = findings or []
    mv = model_versions or ["deterministic-v1"]
    provenance: dict[str, Any] = {
        "oberon_version": "0.1.0",
        "model_versions": mv,
        "artifacts": {
            "before_image": "before.png",
            "after_image": "after.png",
            "overlay": "overlay.png",
            "findings": "findings.geojson",
        },
        "findings": [
            {
                "id": i + 1,
                "score": f.score,
                "area_ha": f.area_ha,
                "metrics": {
                    "ndvi_delta_mean": f.ndvi_delta_mean,
                    "nbr_delta_mean": f.nbr_delta_mean,
                    "pixel_delta_mean": f.pixel_delta_mean,
                    "valid_pixels_in_finding": f.valid_pixels_in_finding,
                },
            }
            for i, f in enumerate(findings)
        ],
        "software": {"oberon": "0.1.0"},
        "abstention": None,
    }
    if abstention_reason:
        provenance["abstention"] = {"reason": abstention_reason}

    return EvidenceBundle(
        output_dir=Path("/tmp/oberon/test-run"),
        before_image=Path("/tmp/oberon/test-run/before.png"),
        after_image=Path("/tmp/oberon/test-run/after.png"),
        overlay_image=Path("/tmp/oberon/test-run/overlay.png"),
        findings_geojson=Path("/tmp/oberon/test-run/findings.geojson"),
        provenance_manifest=Path("/tmp/oberon/test-run/provenance.json"),
        provenance=provenance,
    )


# ---------------------------------------------------------------------------
# ChangeRequestAPI (request model)
# ---------------------------------------------------------------------------

class TestChangeRequestAPI:
    def test_valid_request_parses(self) -> None:
        req = ChangeRequestAPI(
            geometry={"type": "Polygon", "coordinates": [[[0, 0], [0, 1], [1, 1], [1, 0], [0, 0]]]},
            before={"from": "2026-01-01", "to": "2026-02-01"},
            after={"from": "2026-06-01", "to": "2026-07-01"},
        )
        assert req.task == "vegetation_disturbance"
        assert req.max_cloud_fraction == 0.15

    def test_rejects_missing_geometry(self) -> None:
        with pytest.raises(ValidationError):
            ChangeRequestAPI(
                geometry={},  # type: ignore[arg-type]
                before={"from": "2026-01-01", "to": "2026-02-01"},
                after={"from": "2026-06-01", "to": "2026-07-01"},
            )

    def test_rejects_bad_date_order(self) -> None:
        with pytest.raises(ValidationError):
            ChangeRequestAPI(
                geometry={"type": "Polygon", "coordinates": []},
                before={"from": "2026-02-01", "to": "2026-01-01"},  # reversed
                after={"from": "2026-06-01", "to": "2026-07-01"},
            )

    def test_rejects_before_not_before_after(self) -> None:
        with pytest.raises(ValidationError):
            ChangeRequestAPI(
                geometry={"type": "Polygon", "coordinates": [[[0, 0], [0, 1], [1, 1], [1, 0], [0, 0]]]},
                before={"from": "2026-06-01", "to": "2026-07-01"},
                after={"from": "2026-01-01", "to": "2026-02-01"},  # before > after
            )

    def test_serializes_to_json(self) -> None:
        req = ChangeRequestAPI(
            geometry={"type": "Polygon", "coordinates": [[[0, 0], [0, 1], [1, 1], [1, 0], [0, 0]]]},
            before={"from": "2026-01-01", "to": "2026-02-01"},
            after={"from": "2026-06-01", "to": "2026-07-01"},
        )
        data = json.loads(req.model_dump_json())
        assert data["task"] == "vegetation_disturbance"
        assert "geometry" in data


# ---------------------------------------------------------------------------
# APIFinding + EvidenceMetrics (finding response model)
# ---------------------------------------------------------------------------

class TestAPIFinding:
    def test_finding_has_change_score_not_score(self) -> None:
        f = APIFinding(
            geometry={"type": "Polygon", "coordinates": []},
            change_score=0.72,
            changed_area_m2=23000.0,
            evidence=EvidenceMetrics(ndvi_delta=-0.32, nbr_delta=-0.45),
            model=ModelInfo(encoder="deterministic-v1", confidence=None),
        )
        assert f.change_score == 0.72
        # The field name must be change_score, not score
        assert not hasattr(f, "score")

    def test_area_is_m2_not_ha(self) -> None:
        f = APIFinding(
            geometry={"type": "Polygon", "coordinates": []},
            change_score=0.5,
            changed_area_m2=23000.0,
            evidence=EvidenceMetrics(ndvi_delta=-0.3, nbr_delta=-0.2),
            model=ModelInfo(encoder="deterministic-v1", confidence=None),
        )
        assert f.changed_area_m2 == 23000.0

    def test_evidence_uses_ndvi_delta_not_ndvi_delta_mean(self) -> None:
        f = APIFinding(
            geometry={"type": "Polygon", "coordinates": []},
            change_score=0.5,
            changed_area_m2=1000.0,
            evidence=EvidenceMetrics(ndvi_delta=-0.3, nbr_delta=-0.2),
            model=ModelInfo(encoder="deterministic-v1", confidence=None),
        )
        assert f.evidence.ndvi_delta == -0.3
        assert f.evidence.nbr_delta == -0.2
        assert not hasattr(f.evidence, "ndvi_delta_mean")

    def test_suggested_class_optional(self) -> None:
        f = APIFinding(
            geometry={"type": "Polygon", "coordinates": []},
            change_score=0.5,
            changed_area_m2=1000.0,
            evidence=EvidenceMetrics(ndvi_delta=-0.3, nbr_delta=-0.2),
            model=ModelInfo(encoder="deterministic-v1", confidence=None),
        )
        assert f.suggested_class is None

    def test_model_confidence_null_by_default(self) -> None:
        f = APIFinding(
            geometry={"type": "Polygon", "coordinates": []},
            change_score=0.5,
            changed_area_m2=1000.0,
            evidence=EvidenceMetrics(ndvi_delta=-0.3, nbr_delta=-0.2),
            model=ModelInfo(encoder="deterministic-v1"),
        )
        assert f.model.confidence is None


# ---------------------------------------------------------------------------
# ChangeResponse (top-level response)
# ---------------------------------------------------------------------------

class TestChangeResponse:
    def test_status_values(self) -> None:
        assert ResponseStatus.REVIEW == "review_recommended"
        assert ResponseStatus.ABSTAINED == "abstained"
        assert ResponseStatus.FAILED == "failed"

    def test_response_with_findings(self) -> None:
        resp = ChangeResponse(
            status=ResponseStatus.REVIEW,
            findings=[
                APIFinding(
                    geometry={"type": "Polygon", "coordinates": []},
                    change_score=0.8,
                    changed_area_m2=5000.0,
                    evidence=EvidenceMetrics(ndvi_delta=-0.4, nbr_delta=-0.3),
                    model=ModelInfo(encoder="deterministic-v1"),
                ),
            ],
            artifacts=ArtifactPaths(
                before="https://example.com/before.png",
                after="https://example.com/after.png",
                overlay="https://example.com/overlay.png",
            ),
        )
        assert resp.status == "review_recommended"
        assert len(resp.findings) == 1

    def test_response_abstained(self) -> None:
        resp = ChangeResponse(
            status=ResponseStatus.ABSTAINED,
            findings=[],
            artifacts=ArtifactPaths(before="", after="", overlay=""),
        )
        assert resp.status == "abstained"
        assert len(resp.findings) == 0

    def test_response_serializes_to_product_brief_shape(self) -> None:
        resp = ChangeResponse(
            status=ResponseStatus.REVIEW,
            findings=[
                APIFinding(
                    geometry={"type": "Polygon", "coordinates": []},
                    change_score=0.72,
                    changed_area_m2=23000.0,
                    evidence=EvidenceMetrics(ndvi_delta=-0.32, nbr_delta=-0.45),
                    model=ModelInfo(encoder="clay-v1.5", confidence=None),
                ),
            ],
            artifacts=ArtifactPaths(
                before="https://example.com/before.png",
                after="https://example.com/after.png",
                overlay="https://example.com/overlay.png",
            ),
        )
        data = json.loads(resp.model_dump_json())

        # Must match the Product Brief §5 top-level shape
        assert "status" in data
        assert "findings" in data
        assert "artifacts" in data

        # Finding must have the brief field names
        finding = data["findings"][0]
        assert "change_score" in finding
        assert "changed_area_m2" in finding
        assert "evidence" in finding
        assert "model" in finding
        assert "ndvi_delta" in finding["evidence"]
        assert "nbr_delta" in finding["evidence"]
        assert finding["model"]["confidence"] is None


# ---------------------------------------------------------------------------
# Serialization layer (Finding -> APIFinding, EvidenceBundle -> ChangeResponse)
# ---------------------------------------------------------------------------

class TestSerializeFindings:
    def test_converts_score_to_change_score(self) -> None:
        findings = [_make_finding(score=0.72)]
        result = serialize_findings(findings)
        assert result[0].change_score == 0.72

    def test_converts_ha_to_m2(self) -> None:
        findings = [_make_finding(area_ha=2.3)]
        result = serialize_findings(findings)
        assert result[0].changed_area_m2 == pytest.approx(23000.0)

    def test_converts_ndvi_delta_mean_to_ndvi_delta(self) -> None:
        findings = [_make_finding(ndvi=-0.32)]
        result = serialize_findings(findings)
        assert result[0].evidence.ndvi_delta == pytest.approx(-0.32)

    def test_converts_nbr_delta_mean_to_nbr_delta(self) -> None:
        findings = [_make_finding(nbr=-0.45)]
        result = serialize_findings(findings)
        assert result[0].evidence.nbr_delta == pytest.approx(-0.45)

    def test_empty_findings_returns_empty_list(self) -> None:
        result = serialize_findings([])
        assert result == []

    def test_multiple_findings_preserve_order(self) -> None:
        findings = [_make_finding(score=0.9), _make_finding(score=0.5), _make_finding(score=0.3)]
        result = serialize_findings(findings)
        assert [f.change_score for f in result] == [0.9, 0.5, 0.3]


class TestSerializeBundleToResponse:
    def test_complete_bundle_maps_to_review_recommended(self) -> None:
        bundle = _make_bundle(findings=[_make_finding()])
        resp = serialize_bundle_to_response(bundle)
        assert resp.status == ResponseStatus.REVIEW
        assert len(resp.findings) == 1

    def test_abstention_maps_to_abstained(self) -> None:
        bundle = _make_bundle(abstention_reason="Insufficient valid pixels")
        resp = serialize_bundle_to_response(bundle)
        assert resp.status == ResponseStatus.ABSTAINED
        assert len(resp.findings) == 0

    def test_model_versions_surface_from_provenance(self) -> None:
        bundle = _make_bundle(
            findings=[_make_finding()],
            model_versions=["deterministic-v1", "clay-v1.5"],
        )
        resp = serialize_bundle_to_response(bundle)
        # All findings use the encoder from model_versions
        encoders = {f.model.encoder for f in resp.findings}
        assert "deterministic-v1" in encoders or "clay-v1.5" in encoders

    def test_artifacts_use_paths_from_bundle(self) -> None:
        bundle = _make_bundle(findings=[_make_finding()])
        resp = serialize_bundle_to_response(bundle)
        assert "before.png" in resp.artifacts.before or resp.artifacts.before != ""
        assert "after.png" in resp.artifacts.after or resp.artifacts.after != ""

    def test_deterministic_only_uses_deterministic_encoder(self) -> None:
        bundle = _make_bundle(findings=[_make_finding()])
        resp = serialize_bundle_to_response(bundle)
        for f in resp.findings:
            assert f.model.encoder == "deterministic-v1"

    def test_serializes_to_json_roundtrip(self) -> None:
        bundle = _make_bundle(findings=[_make_finding()])
        resp = serialize_bundle_to_response(bundle)
        json_str = resp.model_dump_json()
        data = json.loads(json_str)
        assert data["status"] == "review_recommended"
        assert len(data["findings"]) == 1
        assert data["findings"][0]["change_score"] == 0.72
