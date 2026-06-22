"""Test configuration and shared fixtures."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

DATA_DIR = Path(__file__).parent / "data"


def pytest_addoption(parser: pytest.Parser) -> None:
    """Add --run-integration flag for live STAC/COG golden tests."""
    parser.addoption(
        "--run-integration",
        action="store_true",
        default=False,
        help="Run integration tests that hit live STAC catalogs and COG endpoints.",
    )


def pytest_configure(config: pytest.Config) -> None:
    """Register the integration marker."""
    config.addinivalue_line("markers", "integration: needs --run-integration flag")


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    """Skip integration tests unless --run-integration is passed."""
    if not config.getoption("--run-integration"):
        skip = pytest.mark.skip(reason="pass --run-integration to run live STAC/COG tests")
        for item in items:
            if "integration" in item.keywords:
                item.add_marker(skip)


@pytest.fixture
def sample_geojson() -> dict:
    """Load the sample Costa Rica polygon fixture."""
    path = DATA_DIR / "sample.geojson"
    with open(path) as f:
        return json.load(f)


@pytest.fixture
def sample_polygon_geometry() -> dict:
    """A small sample AOI polygon geometry (Costa Rica, ~100 ha)."""
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
