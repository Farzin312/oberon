"""Tests for GeoJSON findings output."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from oberon.artifacts.geojson import write_findings_geojson
from oberon.core import Finding


@pytest.fixture
def sample_finding() -> Finding:
    return Finding(
        geometry={
            "type": "Polygon",
            "coordinates": [[
                [10.0, 20.0],
                [11.0, 20.0],
                [11.0, 21.0],
                [10.0, 21.0],
                [10.0, 20.0],
            ]],
        },
        score=0.85,
        area_ha=2.5,
        ndvi_delta_mean=-0.32,
        nbr_delta_mean=-0.18,
        valid_pixels_in_finding=250,
    )


@pytest.fixture
def output_path(tmp_path: Path) -> Path:
    return tmp_path / "findings.geojson"


class TestWriteFindingsGeojson:
    """write_findings_geojson: list[Finding] -> GeoJSON FeatureCollection."""

    def test_valid_feature_collection(self, sample_finding: Finding, output_path: Path) -> None:
        findings = [sample_finding]

        result = write_findings_geojson(findings, output_path)

        assert result == output_path
        assert output_path.exists()
        with open(output_path) as f:
            data = json.load(f)

        assert data["type"] == "FeatureCollection"
        assert len(data["features"]) == 1

        feature = data["features"][0]
        assert feature["geometry"]["type"] == "Polygon"
        props = feature["properties"]
        assert props["score"] == 0.85
        assert props["area_ha"] == 2.5
        assert props["ndvi_delta_mean"] == -0.32
        assert props["nbr_delta_mean"] == -0.18
        assert props["valid_pixels_in_finding"] == 250

    def test_empty_findings_produces_valid_collection(self, output_path: Path) -> None:
        """Empty findings list -> valid FeatureCollection with 0 features."""
        result = write_findings_geojson([], output_path)

        assert result.exists()
        with open(output_path) as f:
            data = json.load(f)
        assert data["type"] == "FeatureCollection"
        assert data["features"] == []

    def test_multiple_findings_all_serialized(self, output_path: Path) -> None:
        """Multiple findings all appear as separate features."""
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

        write_findings_geojson(findings, output_path)

        with open(output_path) as f:
            data = json.load(f)
        assert len(data["features"]) == 2
        assert data["features"][0]["properties"]["score"] == 0.9
        assert data["features"][1]["properties"]["score"] == 0.5

    def test_each_feature_has_required_properties(self, sample_finding: Finding, output_path: Path) -> None:
        write_findings_geojson([sample_finding], output_path)

        with open(output_path) as f:
            data = json.load(f)
        props = data["features"][0]["properties"]
        required_keys = {"score", "area_ha", "ndvi_delta_mean", "nbr_delta_mean", "valid_pixels_in_finding"}
        assert required_keys.issubset(props.keys())

    def test_id_starts_at_1_and_increments(self, output_path: Path) -> None:
        """Each feature should get a sequential id property starting at 1."""
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

        write_findings_geojson(findings, output_path)

        with open(output_path) as f:
            data = json.load(f)
        assert data["features"][0]["properties"]["id"] == 1
        assert data["features"][1]["properties"]["id"] == 2
