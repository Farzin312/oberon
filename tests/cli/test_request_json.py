"""Tests for --request flag and upgraded --json output (008 CLI wiring).

Tests that:
1. --request reads a JSON file matching ChangeRequestAPI schema and runs analysis
2. --json output uses the full ChangeResponse shape (via serialization layer)
3. --request is mutually exclusive with --aoi/--before/--after
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from click.testing import CliRunner

from oberon.cli.main import cli


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


@pytest.fixture
def sample_geometry() -> dict[str, Any]:
    return {
        "type": "Polygon",
        "coordinates": [[
            [-84.0, 10.0],
            [-83.9, 10.0],
            [-83.9, 10.1],
            [-84.0, 10.1],
            [-84.0, 10.0],
        ]],
    }


@pytest.fixture
def request_json_file(tmp_path: Path, sample_geometry: dict[str, Any]) -> Path:
    """Write a valid ChangeRequestAPI JSON to a temp file."""
    path = tmp_path / "request.json"
    request_data = {
        "geometry": sample_geometry,
        "before": {"from": "2026-01-01", "to": "2026-02-01"},
        "after": {"from": "2026-06-01", "to": "2026-07-01"},
        "task": "vegetation_disturbance",
        "max_cloud_fraction": 0.15,
    }
    with open(path, "w") as f:
        json.dump(request_data, f)
    return path


@pytest.fixture
def request_json_minimal(tmp_path: Path, sample_geometry: dict[str, Any]) -> Path:
    """Minimal request with only required fields."""
    path = tmp_path / "request_minimal.json"
    request_data = {
        "geometry": sample_geometry,
        "before": {"from": "2026-01-01", "to": "2026-02-01"},
        "after": {"from": "2026-06-01", "to": "2026-07-01"},
    }
    with open(path, "w") as f:
        json.dump(request_data, f)
    return path


@pytest.fixture
def request_json_bad_dates(tmp_path: Path, sample_geometry: dict[str, Any]) -> Path:
    """Request with reversed before window."""
    path = tmp_path / "request_bad.json"
    request_data = {
        "geometry": sample_geometry,
        "before": {"from": "2026-02-01", "to": "2026-01-01"},
        "after": {"from": "2026-06-01", "to": "2026-07-01"},
    }
    with open(path, "w") as f:
        json.dump(request_data, f)
    return path


class TestRequestFlag:
    """--request reads a JSON file and runs analysis."""

    def test_request_flag_in_help(self, runner: CliRunner) -> None:
        result = runner.invoke(cli, ["analyze", "--help"])
        assert result.exit_code == 0
        assert "--request" in result.output

    def test_request_runs_analysis(
        self, runner: CliRunner, request_json_file: Path, tmp_path: Path
    ) -> None:
        """--request should produce the same outcomes as --aoi mode."""
        output_dir = tmp_path / "output"
        result = runner.invoke(cli, [
            "analyze",
            "--request", str(request_json_file),
            "-o", str(output_dir),
        ])
        # Either completes or abstains, never crashes.
        assert result.exit_code == 0
        assert any(phrase in result.output for phrase in [
            "Analysis complete", "Abstained", "No suitable",
        ])

    def test_request_minimal_defaults_applied(
        self, runner: CliRunner, request_json_minimal: Path, tmp_path: Path
    ) -> None:
        """Minimal request (no task, no cloud fraction) should use defaults."""
        output_dir = tmp_path / "output"
        result = runner.invoke(cli, [
            "analyze",
            "--request", str(request_json_minimal),
            "-o", str(output_dir),
        ])
        assert result.exit_code == 0

    def test_request_rejects_bad_dates(
        self, runner: CliRunner, request_json_bad_dates: Path, tmp_path: Path
    ) -> None:
        """Request with reversed before window should fail validation."""
        output_dir = tmp_path / "output"
        result = runner.invoke(cli, [
            "analyze",
            "--request", str(request_json_bad_dates),
            "-o", str(output_dir),
        ])
        assert result.exit_code != 0

    def test_request_conflicts_with_aoi(
        self, runner: CliRunner, request_json_file: Path, tmp_path: Path
    ) -> None:
        """--request and --aoi cannot be used together."""
        # Create a dummy aoi file too
        aoi_path = tmp_path / "aoi.geojson"
        aoi_path.write_text('{"type":"Polygon","coordinates":[]}')

        result = runner.invoke(cli, [
            "analyze",
            "--request", str(request_json_file),
            "--aoi", str(aoi_path),
            "--before", "2026-01-01",
            "--after", "2026-06-01",
        ])
        assert result.exit_code != 0

    def test_request_nonexistent_file(
        self, runner: CliRunner, tmp_path: Path
    ) -> None:
        """Non-existent request file should fail."""
        result = runner.invoke(cli, [
            "analyze",
            "--request", "/nonexistent/request.json",
        ])
        assert result.exit_code != 0

    def test_request_applies_overrides(
        self, runner: CliRunner, request_json_file: Path, tmp_path: Path
    ) -> None:
        """CLI flags like --composite and --use-ai should work with --request."""
        output_dir = tmp_path / "output"
        result = runner.invoke(cli, [
            "analyze",
            "--request", str(request_json_file),
            "--composite",
            "-o", str(output_dir),
        ])
        # May abstain (no network), but should not crash on flag parsing.
        assert result.exit_code == 0


class TestJsonOutputUpgrade:
    """--json output should use ChangeResponse shape from serialization layer."""

    def test_json_output_has_api_fields(
        self, runner: CliRunner, request_json_file: Path, tmp_path: Path
    ) -> None:
        """--json with --request should output the full API response shape."""
        output_dir = tmp_path / "output"
        result = runner.invoke(cli, [
            "analyze",
            "--request", str(request_json_file),
            "--json",
            "-o", str(output_dir),
        ])
        assert result.exit_code == 0

        # The JSON output should have the Product Brief fields.
        data = json.loads(result.output)
        assert "status" in data
        assert "findings" in data
        assert "artifacts" in data

        # Status must be one of the API enum values.
        assert data["status"] in ("review_recommended", "abstained", "failed")

    def test_json_abstained_has_no_findings(
        self, runner: CliRunner, request_json_file: Path, tmp_path: Path
    ) -> None:
        """Abstained response should have empty findings list."""
        output_dir = tmp_path / "output"
        result = runner.invoke(cli, [
            "analyze",
            "--request", str(request_json_file),
            "--json",
            "--max-cloud", "0.0",  # Force abstention
            "-o", str(output_dir),
        ])
        if result.exit_code == 0:
            data = json.loads(result.output)
            if data["status"] == "abstained":
                assert data["findings"] == []

    def test_json_finding_shape_matches_brief(
        self, runner: CliRunner, request_json_file: Path, tmp_path: Path
    ) -> None:
        """Each finding should have the Product Brief field names."""
        output_dir = tmp_path / "output"
        result = runner.invoke(cli, [
            "analyze",
            "--request", str(request_json_file),
            "--json",
            "-o", str(output_dir),
        ])
        assert result.exit_code == 0
        data = json.loads(result.output)

        if data["findings"]:
            f = data["findings"][0]
            assert "change_score" in f
            assert "changed_area_m2" in f
            assert "evidence" in f
            assert "ndvi_delta" in f["evidence"]
            assert "model" in f
            # Should NOT have the old field names
            assert "score" not in f
            assert "area_ha" not in f
