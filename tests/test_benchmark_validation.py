"""Unit tests for the golden test validation logic.

Tests the validate_outcome helper with synthetic data — no network needed.
These ensure the validation assertions are correct before running real golden tests.
"""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest
from benchmark_utils import discover_benchmark_dirs, validate_outcome


def _make_bundle(
    abstention_reason: str | None = None,
    finding_count: int = 0,
    ndvi_delta_mean: float | None = None,
    nested: bool = False,
) -> SimpleNamespace:
    """Build a minimal object that looks like an EvidenceBundle for validation."""
    prov: dict[str, object] = {}
    if abstention_reason is not None:
        if nested:
            prov["abstention"] = {"reason": abstention_reason}
        else:
            prov["abstention_reason"] = abstention_reason
    if finding_count > 0:
        if nested:
            prov["findings"] = [
                {"score": 0.9, "metrics": {"ndvi_delta_mean": ndvi_delta_mean}}
                for _ in range(finding_count)
            ]
        else:
            prov["findings"] = [{"score": 0.9} for _ in range(finding_count)]
    else:
        prov["findings"] = []
    if ndvi_delta_mean is not None:
        prov["ndvi_delta_mean"] = ndvi_delta_mean
    return SimpleNamespace(provenance=prov)


class TestValidateOutcomeFindings:
    """validate_outcome: when findings are expected."""

    def test_correct_finding_count(self) -> None:
        bundle = _make_bundle(finding_count=3, ndvi_delta_mean=-0.3)
        expected = {
            "expected_outcome": "findings",
            "finding_count": {"min": 1, "max": 5},
            "ndvi_delta_range": [-0.5, -0.1],
        }
        validate_outcome(bundle, expected, Path("01-test"))

    def test_finding_count_below_min_fails(self) -> None:
        bundle = _make_bundle(finding_count=0)
        expected = {
            "expected_outcome": "findings",
            "finding_count": {"min": 1, "max": 5},
        }
        with pytest.raises(AssertionError, match="not in expected range"):
            validate_outcome(bundle, expected, Path("01-test"))

    def test_finding_count_above_max_fails(self) -> None:
        bundle = _make_bundle(finding_count=10)
        expected = {
            "expected_outcome": "findings",
            "finding_count": {"min": 1, "max": 5},
        }
        with pytest.raises(AssertionError, match="not in expected range"):
            validate_outcome(bundle, expected, Path("01-test"))

    def test_ndvi_out_of_range_fails(self) -> None:
        bundle = _make_bundle(finding_count=2, ndvi_delta_mean=-0.8)
        expected = {
            "expected_outcome": "findings",
            "finding_count": {"min": 1, "max": 5},
            "ndvi_delta_range": [-0.5, -0.1],
        }
        with pytest.raises(AssertionError, match="not in expected range"):
            validate_outcome(bundle, expected, Path("01-test"))

    def test_pipeline_abstained_but_findings_expected(self) -> None:
        bundle = _make_bundle(abstention_reason="No suitable scenes found")
        expected = {"expected_outcome": "findings"}
        with pytest.raises(AssertionError, match="expected findings but pipeline abstained"):
            validate_outcome(bundle, expected, Path("01-test"))

    def test_zero_findings_expected_passes(self) -> None:
        """No-change examples expect finding_count 0,0 — should pass with 0 findings."""
        bundle = _make_bundle(finding_count=0)
        expected = {
            "expected_outcome": "findings",
            "finding_count": {"min": 0, "max": 0},
        }
        validate_outcome(bundle, expected, Path("05-test"))


class TestValidateOutcomeAbstention:
    """validate_outcome: when abstention is expected."""

    def test_correct_abstention_with_substring(self) -> None:
        bundle = _make_bundle(abstention_reason="Abstained: cloud cover too high")
        expected = {
            "expected_outcome": "abstention",
            "abstention_reason_substring": "cloud",
        }
        validate_outcome(bundle, expected, Path("09-test"))

    def test_correct_abstention_without_substring(self) -> None:
        bundle = _make_bundle(abstention_reason="No suitable scenes")
        expected = {"expected_outcome": "abstention"}
        validate_outcome(bundle, expected, Path("09-test"))

    def test_current_nested_abstention_shape(self) -> None:
        bundle = _make_bundle(abstention_reason="No suitable scenes", nested=True)
        expected = {"expected_outcome": "abstention"}
        validate_outcome(bundle, expected, Path("09-test"))

    def test_wrong_abstention_substring_fails(self) -> None:
        bundle = _make_bundle(abstention_reason="Abstained: insufficient pixels")
        expected = {
            "expected_outcome": "abstention",
            "abstention_reason_substring": "cloud",
        }
        with pytest.raises(AssertionError, match="does not contain expected substring"):
            validate_outcome(bundle, expected, Path("09-test"))

    def test_no_abstention_but_abstention_expected(self) -> None:
        bundle = _make_bundle(finding_count=2)
        expected = {"expected_outcome": "abstention"}
        with pytest.raises(AssertionError, match="expected abstention but no abstention_reason"):
            validate_outcome(bundle, expected, Path("09-test"))


class TestBenchmarkDiscovery:
    """Benchmark dir discovery: finds and validates example directories."""

    def test_finds_all_examples(self) -> None:
        dirs = discover_benchmark_dirs()
        assert len(dirs) == 12, f"Expected 12 benchmark dirs, got {len(dirs)}"

    def test_dirs_are_sorted(self) -> None:
        dirs = discover_benchmark_dirs()
        names = [d.name for d in dirs]
        assert names == sorted(names), "Benchmark dirs should be sorted by name"

    def test_each_dir_has_required_files(self) -> None:
        for d in discover_benchmark_dirs():
            assert (d / "aoi.geojson").exists(), f"{d.name} missing aoi.geojson"
            assert (d / "expected.json").exists(), f"{d.name} missing expected.json"
            assert (d / "request.json").exists(), f"{d.name} missing request.json"
            assert (d / "review.md").exists(), f"{d.name} missing review.md"
