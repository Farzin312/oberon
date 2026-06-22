"""Tests for the `oberon aoi` CLI command."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from click.testing import CliRunner

from oberon.cli.main import cli


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


class TestAoiCommand:
    """Tests for the aoi subcommand."""

    def test_generates_valid_geojson_to_stdout(self, runner: CliRunner) -> None:
        """aoi command should output valid GeoJSON to stdout."""
        result = runner.invoke(cli, ["aoi", "--lat", "41.82", "--lon", "-93.62"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["type"] == "Feature"
        assert data["geometry"]["type"] == "Polygon"
        coords = data["geometry"]["coordinates"][0]
        assert len(coords) == 5  # closed ring
        assert coords[0] == coords[-1]  # first == last

    def test_writes_file_with_output_flag(self, runner: CliRunner, tmp_path: Path) -> None:
        """aoi command should write to file when -o is given."""
        out = tmp_path / "aoi.geojson"
        result = runner.invoke(cli, [
            "aoi", "--lat", "-7.475", "--lon", "-55.175", "-o", str(out),
        ])
        assert result.exit_code == 0
        assert out.exists()
        data = json.loads(out.read_text())
        assert data["geometry"]["type"] == "Polygon"

    def test_polygon_centered_on_coordinate(self, runner: CliRunner) -> None:
        """The polygon should roughly center on the given lat/lon."""
        result = runner.invoke(cli, ["aoi", "--lat", "0.0", "--lon", "0.0", "--buffer", "1.0"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        coords = data["geometry"]["coordinates"][0]
        lons = [c[0] for c in coords]
        lats = [c[1] for c in coords]
        # Center should be near 0,0
        assert min(lons) < 0.0 < max(lons)
        assert min(lats) < 0.0 < max(lats)

    def test_custom_buffer_changes_size(self, runner: CliRunner) -> None:
        """Larger buffer should produce a larger polygon."""
        small = runner.invoke(cli, ["aoi", "--lat", "45.0", "--lon", "0.0", "--buffer", "0.5"])
        large = runner.invoke(cli, ["aoi", "--lat", "45.0", "--lon", "0.0", "--buffer", "5.0"])
        small_data = json.loads(small.output)
        large_data = json.loads(large.output)
        small_lats = [c[1] for c in small_data["geometry"]["coordinates"][0]]
        large_lats = [c[1] for c in large_data["geometry"]["coordinates"][0]]
        assert (max(large_lats) - min(large_lats)) > (max(small_lats) - min(small_lats))

    def test_invalid_lat_rejected(self, runner: CliRunner) -> None:
        """Out-of-range latitude should be rejected."""
        result = runner.invoke(cli, ["aoi", "--lat", "91.0", "--lon", "0.0"])
        assert result.exit_code != 0

    def test_invalid_lon_rejected(self, runner: CliRunner) -> None:
        """Out-of-range longitude should be rejected."""
        result = runner.invoke(cli, ["aoi", "--lat", "0.0", "--lon", "181.0"])
        assert result.exit_code != 0

    def test_required_args(self, runner: CliRunner) -> None:
        """Missing lat or lon should error."""
        result = runner.invoke(cli, ["aoi", "--lat", "45.0"])
        assert result.exit_code != 0
