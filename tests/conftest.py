"""Test configuration and shared fixtures."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

DATA_DIR = Path(__file__).parent / "data"


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
