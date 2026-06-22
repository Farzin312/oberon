"""Tests for the Oberon CLI."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from click.testing import CliRunner

from oberon.cli.main import cli


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


@pytest.fixture
def sample_geojson_file(tmp_path: Path) -> Path:
    """Write a valid GeoJSON polygon to a temp file."""
    path = tmp_path / "aoi.geojson"
    geojson = {
        "type": "Feature",
        "geometry": {
            "type": "Polygon",
            "coordinates": [[
                [-84.0, 10.0],
                [-83.9, 10.0],
                [-83.9, 10.1],
                [-84.0, 10.1],
                [-84.0, 10.0],
            ]],
        },
        "properties": {},
    }
    with open(path, "w") as f:
        json.dump(geojson, f)
    return path


class TestAnalyzeHelp:
    """oberon analyze --help should list all options."""

    def test_help_shows_all_options(self, runner: CliRunner) -> None:
        result = runner.invoke(cli, ["analyze", "--help"])

        assert result.exit_code == 0
        assert "analyze" in result.output
        assert "--aoi" in result.output
        assert "--before" in result.output
        assert "--after" in result.output
        assert "--task" in result.output
        assert "--output" in result.output or "-o" in result.output
        assert "--max-cloud" in result.output
        assert "--min-valid" in result.output


class TestAnalyzeValidation:
    """CLI input validation (before calling orchestrator)."""

    def test_missing_aoi_shows_error(self, runner: CliRunner) -> None:
        result = runner.invoke(cli, ["analyze", "--before", "2026-01-01", "--after", "2026-06-01"])

        assert result.exit_code != 0
        assert "--aoi" in result.output

    def test_invalid_before_date(self, runner: CliRunner, sample_geojson_file: Path) -> None:
        result = runner.invoke(cli, [
            "analyze", "--aoi", str(sample_geojson_file),
            "--before", "not-a-date",
            "--after", "2026-06-01",
        ])

        assert result.exit_code != 0
        assert "not-a-date" in result.output or "Invalid" in result.output or "Error" in result.output

    def test_invalid_after_date(self, runner: CliRunner, sample_geojson_file: Path) -> None:
        result = runner.invoke(cli, [
            "analyze", "--aoi", str(sample_geojson_file),
            "--before", "2026-01-01",
            "--after", "bad-date",
        ])

        assert result.exit_code != 0
        assert "bad-date" in result.output or "Invalid" in result.output or "Error" in result.output

    def test_invalid_aoe_file_shows_error(self, runner: CliRunner) -> None:
        """A non-existent AOI file should fail."""
        result = runner.invoke(cli, [
            "analyze", "--aoi", "/nonexistent/file.geojson",
            "--before", "2026-01-01",
            "--after", "2026-06-01",
        ])

        assert result.exit_code != 0


class TestAnalyzeIntegration:
    """End-to-end tests with mocked pipeline stages."""

    def test_runs_with_valid_input(self, runner: CliRunner, sample_geojson_file: Path, tmp_path: Path) -> None:
        """With valid input, the CLI should complete or abstain — never crash."""
        output_dir = tmp_path / "oberon-output"

        result = runner.invoke(cli, [
            "analyze",
            "--aoi", str(sample_geojson_file),
            "--before", "2026-01-31",
            "--after", "2026-06-30",
            "-o", str(output_dir),
        ])

        # Either finds scenes and completes, or abstains — both are valid.
        assert result.exit_code == 0
        assert any(phrase in result.output for phrase in [
            "Analysis complete", "Abstained", "No suitable",
        ])

    def test_abstention_path_works(self, runner: CliRunner, sample_geojson_file: Path, tmp_path: Path) -> None:
        """The abstention path should produce clean output."""
        output_dir = tmp_path / "oberon-abstention"

        result = runner.invoke(cli, [
            "analyze",
            "--aoi", str(sample_geojson_file),
            "--before", "2026-01-31",
            "--after", "2026-06-30",
            "-o", str(output_dir),
            "--max-cloud", "1.0",  # Very strict cloud filter — likely yields abstention
        ])

        # Should either abstain or fail gracefully, never crash.
        assert result.exit_code == 0

    def test_exit_code_0_on_normal_completion(self, runner: CliRunner, sample_geojson_file: Path, tmp_path: Path) -> None:
        """A successful run or abstention both exit with code 0."""
        output_dir = tmp_path / "oberon-exit0"

        result = runner.invoke(cli, [
            "analyze",
            "--aoi", str(sample_geojson_file),
            "--before", "2026-01-31",
            "--after", "2026-06-30",
            "-o", str(output_dir),
        ])

        assert result.exit_code == 0
