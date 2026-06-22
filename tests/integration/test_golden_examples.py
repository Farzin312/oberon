"""Golden-case integration tests for the benchmark dataset.

These tests run the full pipeline (live STAC + COG) against each benchmark
example and validate the output against expected.json.

Run with: pytest tests/integration/ --run-integration -v
Skip by default (network is the point).
"""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest
from benchmark_utils import (
    discover_benchmark_dirs,
    load_aoi,
    load_expected,
    load_request_params,
    validate_outcome,
)

BENCHMARK_DIRS = discover_benchmark_dirs()


def _build_change_request(example_dir: Path):  # type: ignore[no-untyped-def]
    """Build a ChangeRequest from benchmark example files."""
    from oberon.core import ChangeRequest

    geometry = load_aoi(example_dir)
    params = load_request_params(example_dir)

    before_from, before_to = params["before"]
    after_from, after_to = params["after"]

    return ChangeRequest(
        geometry=geometry,
        before=(date.fromisoformat(before_from), date.fromisoformat(before_to)),
        after=(date.fromisoformat(after_from), date.fromisoformat(after_to)),
        task=params.get("task", "vegetation_disturbance"),
        max_cloud_fraction=params.get("max_cloud_fraction", 0.15),
        min_valid_pixels=params.get("min_valid_pixels", 0.30),
        min_change_area_ha=params.get("min_change_area_ha", 0.5),
    )


@pytest.mark.integration
@pytest.mark.parametrize("example_dir", BENCHMARK_DIRS, ids=lambda d: d.name)
def test_golden_example(example_dir: Path, tmp_path: Path) -> None:
    """Run the full pipeline on a benchmark example and validate the result."""
    from oberon.cli.orchestrator import run_analysis

    request = _build_change_request(example_dir)
    expected = load_expected(example_dir)

    bundle = run_analysis(request, tmp_path)
    validate_outcome(bundle, expected, example_dir)
