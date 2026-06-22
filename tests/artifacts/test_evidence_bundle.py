"""Tests for evidence bundle construction and output directory management."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest
from PIL import Image

from oberon.artifacts import build_evidence_bundle, create_output_dir
from oberon.core import Finding, PreparedPair


@pytest.fixture
def synthetic_pair() -> PreparedPair:
    """A small synthetic PreparedPair with RGB + NIR bands for image rendering."""
    shape = (30, 30)
    rng = np.random.default_rng(seed=42)
    before = {
        "B02": rng.integers(500, 3000, shape, dtype=np.uint16),
        "B03": rng.integers(500, 3000, shape, dtype=np.uint16),
        "B04": rng.integers(500, 3000, shape, dtype=np.uint16),
        "B08": rng.integers(1000, 5000, shape, dtype=np.uint16),
    }
    after = {
        "B02": rng.integers(500, 3000, shape, dtype=np.uint16),
        "B03": rng.integers(500, 3000, shape, dtype=np.uint16),
        "B04": rng.integers(500, 3000, shape, dtype=np.uint16),
        "B08": rng.integers(1000, 5000, shape, dtype=np.uint16),
    }
    return PreparedPair(
        before=before,
        after=after,
        mask=np.ones(shape, dtype=bool),
        crs="EPSG:32616",
        transform=(10.0, 0.0, 500000.0, 0.0, -10.0, 2000000.0),
        bounds=(500000.0, 1999700.0, 500300.0, 2000000.0),
    )


@pytest.fixture
def sample_finding() -> Finding:
    return Finding(
        geometry={"type": "Polygon", "coordinates": [[[0, 0], [1, 0], [1, 1], [0, 1], [0, 0]]]},
        score=0.8,
        area_ha=1.5,
        ndvi_delta_mean=-0.3,
        nbr_delta_mean=-0.1,
        valid_pixels_in_finding=150,
    )


class TestCreateOutputDir:
    def test_creates_nested_directory(self, tmp_path: Path) -> None:
        target = tmp_path / "a" / "b" / "c"
        result = create_output_dir(target)
        assert result == target
        assert target.exists()
        assert target.is_dir()

    def test_existing_dir_is_ok(self, tmp_path: Path) -> None:
        target = tmp_path / "existing"
        target.mkdir()
        result = create_output_dir(target)
        assert result.exists()


class TestBuildEvidenceBundle:
    def test_all_artifacts_created(self, synthetic_pair: PreparedPair, sample_finding: Finding, tmp_path: Path) -> None:
        output_dir = tmp_path / "output"

        bundle = build_evidence_bundle([sample_finding], synthetic_pair, output_dir)

        assert bundle.before_image.exists()
        assert bundle.after_image.exists()
        assert bundle.overlay_image.exists()
        assert bundle.findings_geojson.exists()
        assert bundle.provenance_manifest.exists()

    def test_geojson_is_valid(self, synthetic_pair: PreparedPair, sample_finding: Finding, tmp_path: Path) -> None:
        bundle = build_evidence_bundle([sample_finding], synthetic_pair, tmp_path / "out")

        with open(bundle.findings_geojson) as f:
            data = json.load(f)
        assert data["type"] == "FeatureCollection"
        assert len(data["features"]) == 1

    def test_provenance_is_valid_json(self, synthetic_pair: PreparedPair, sample_finding: Finding, tmp_path: Path) -> None:
        bundle = build_evidence_bundle([sample_finding], synthetic_pair, tmp_path / "out")

        with open(bundle.provenance_manifest) as f:
            data = json.load(f)
        assert data["oberon_version"] == "0.1.0"
        assert len(data["findings"]) == 1
        assert data["abstention"] is None

    def test_images_are_valid_pngs(self, synthetic_pair: PreparedPair, sample_finding: Finding, tmp_path: Path) -> None:
        bundle = build_evidence_bundle([sample_finding], synthetic_pair, tmp_path / "out")

        for img_path in [bundle.before_image, bundle.after_image, bundle.overlay_image]:
            img = Image.open(img_path)
            assert img.format == "PNG"
            assert img.size == (30, 30)
            img.close()

    def test_empty_findings_still_produces_bundle(self, synthetic_pair: PreparedPair, tmp_path: Path) -> None:
        """Zero findings should still write all artifacts (empty GeoJSON, provenance with no findings)."""
        bundle = build_evidence_bundle([], synthetic_pair, tmp_path / "out")

        with open(bundle.findings_geojson) as f:
            data = json.load(f)
        assert data["features"] == []
        assert bundle.provenance_manifest.exists()

    def test_abstention_in_provenance(self, synthetic_pair: PreparedPair, tmp_path: Path) -> None:
        bundle = build_evidence_bundle(
            [], synthetic_pair, tmp_path / "out",
            abstention_reason="Insufficient valid pixels: 12%",
        )

        with open(bundle.provenance_manifest) as f:
            data = json.load(f)
        assert data["abstention"] is not None
        assert "12%" in data["abstention"]["reason"]
