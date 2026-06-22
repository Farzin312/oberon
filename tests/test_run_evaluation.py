"""Tests for the live evaluation runner conversion helpers."""

from __future__ import annotations

import importlib.util
from pathlib import Path
from types import SimpleNamespace

_SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "run_evaluation.py"
_SPEC = importlib.util.spec_from_file_location("run_evaluation", _SCRIPT)
assert _SPEC is not None
assert _SPEC.loader is not None
run_evaluation = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(run_evaluation)
result_to_example_result = run_evaluation.result_to_example_result


def test_result_to_example_result_reads_nested_abstention_reason() -> None:
    """Current provenance stores abstention as {'reason': ...}, not a flat key."""
    bundle = SimpleNamespace(provenance={"findings": [], "abstention": {"reason": "cloud"}})

    result = result_to_example_result(
        bundle,
        {"expected_outcome": "findings", "finding_count": {"min": 2, "max": 5}},
        "example-01",
        "geo_test",
    )

    assert result.actual_outcome == "abstention"
    assert result.false_negative_count == 2


def test_result_to_example_result_counts_excess_findings_as_false_positives() -> None:
    """Finding counts above the expected max are false positives, not extra true positives."""
    bundle = SimpleNamespace(
        provenance={
            "findings": [{"id": i} for i in range(8)],
            "abstention": None,
        },
    )

    result = result_to_example_result(
        bundle,
        {"expected_outcome": "findings", "finding_count": {"min": 1, "max": 5}},
        "example-02",
        "geo_test",
    )

    assert result.true_positive_count == 5
    assert result.false_positive_count == 3
    assert result.false_negative_count == 0


def test_result_to_example_result_uses_expected_ndvi_range() -> None:
    """Wrong-direction NDVI changes should not count as true positives."""
    bundle = SimpleNamespace(
        provenance={
            "findings": [
                {"metrics": {"ndvi_delta_mean": 0.4}},
                {"metrics": {"ndvi_delta_mean": -0.3}},
            ],
            "abstention": None,
        },
    )

    result = result_to_example_result(
        bundle,
        {
            "expected_outcome": "findings",
            "finding_count": {"min": 1, "max": 5},
            "ndvi_delta_range": [-0.5, -0.1],
        },
        "example-03",
        "geo_test",
    )

    assert result.true_positive_count == 1
    assert result.false_positive_count == 1
    assert result.false_negative_count == 0
