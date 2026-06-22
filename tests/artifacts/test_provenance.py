"""Tests for provenance manifest construction."""

from __future__ import annotations

from pathlib import Path

import pytest

from oberon.artifacts.provenance import build_provenance
from oberon.core import EvidenceBundle, Finding


@pytest.fixture
def sample_finding() -> Finding:
    return Finding(
        geometry={"type": "Polygon", "coordinates": [[[0, 0], [1, 0], [1, 1], [0, 1], [0, 0]]]},
        score=0.72,
        area_ha=2.3,
        ndvi_delta_mean=-0.32,
        nbr_delta_mean=-0.18,
        valid_pixels_in_finding=230,
    )


@pytest.fixture
def sample_bundle(tmp_path: Path) -> EvidenceBundle:
    out = tmp_path / "output"
    out.mkdir()
    return EvidenceBundle(
        output_dir=out,
        before_image=out / "before.png",
        after_image=out / "after.png",
        overlay_image=out / "overlay.png",
        findings_geojson=out / "findings.geojson",
        provenance_manifest=out / "provenance.json",
        provenance={},
    )


class TestBuildProvenance:
    """build_provenance: constructs reproducibility manifest."""

    def test_contains_required_top_level_fields(
        self, sample_finding: Finding, sample_bundle: EvidenceBundle
    ) -> None:
        result = build_provenance([sample_finding], sample_bundle)

        required_keys = {"oberon_version", "artifacts", "findings", "software"}
        assert required_keys.issubset(result.keys())

    def test_artifacts_section_has_all_paths(
        self, sample_finding: Finding, sample_bundle: EvidenceBundle
    ) -> None:
        result = build_provenance([sample_finding], sample_bundle)

        artifacts = result["artifacts"]
        assert "before_image" in artifacts
        assert "after_image" in artifacts
        assert "overlay" in artifacts
        assert "findings" in artifacts

    def test_findings_section_serialized(
        self, sample_finding: Finding, sample_bundle: EvidenceBundle
    ) -> None:
        result = build_provenance([sample_finding], sample_bundle)

        assert len(result["findings"]) == 1
        f = result["findings"][0]
        assert f["id"] == 1
        assert f["score"] == 0.72
        assert f["area_ha"] == 2.3
        assert f["metrics"]["ndvi_delta_mean"] == -0.32

    def test_empty_findings_produces_empty_findings_list(
        self, sample_bundle: EvidenceBundle
    ) -> None:
        result = build_provenance([], sample_bundle)

        assert result["findings"] == []

    def test_software_versions_present(
        self, sample_finding: Finding, sample_bundle: EvidenceBundle
    ) -> None:
        result = build_provenance([sample_finding], sample_bundle)

        software = result["software"]
        assert "oberon" in software
        assert "python" in software
        assert "numpy" in software

    def test_abstention_case(
        self, sample_bundle: EvidenceBundle
    ) -> None:
        """When abstention_reason is set, manifest reflects it."""
        result = build_provenance([], sample_bundle, abstention_reason="Insufficient valid pixels")

        assert result["abstention"] is not None
        assert "Insufficient valid pixels" in result["abstention"]["reason"]
        assert result["findings"] == []

    def test_multiple_findings_get_sequential_ids(
        self, sample_bundle: EvidenceBundle
    ) -> None:
        findings = [
            Finding(
                geometry={"type": "Polygon", "coordinates": [[[0, 0], [1, 0], [1, 1], [0, 1], [0, 0]]]},
                score=0.9,
                area_ha=1.0,
                ndvi_delta_mean=-0.4,
                nbr_delta_mean=-0.2,
                valid_pixels_in_finding=100,
            ),
            Finding(
                geometry={"type": "Polygon", "coordinates": [[[2, 2], [3, 2], [3, 3], [2, 3], [2, 2]]]},
                score=0.5,
                area_ha=0.8,
                ndvi_delta_mean=-0.15,
                nbr_delta_mean=0.0,
                valid_pixels_in_finding=80,
            ),
        ]

        result = build_provenance(findings, sample_bundle)

        assert result["findings"][0]["id"] == 1
        assert result["findings"][1]["id"] == 2
