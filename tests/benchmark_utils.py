"""Shared helpers for benchmark dataset tests.

Used by both the integration golden tests and the unit validation tests.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

BENCHMARK_BASE = Path(__file__).resolve().parent / "data" / "benchmark"


def discover_benchmark_dirs() -> list[Path]:
    """Return all benchmark example directories with required files."""
    if not BENCHMARK_BASE.exists():
        return []
    return sorted(
        d
        for d in BENCHMARK_BASE.iterdir()
        if d.is_dir() and (d / "expected.json").exists() and (d / "aoi.geojson").exists()
    )


def validate_outcome(
    bundle: Any,
    expected: dict[str, Any],
    example_dir: Path,
) -> None:
    """Validate a pipeline EvidenceBundle against expected.json.

    Asserts:
    - Expected outcome type matches (findings vs abstention)
    - Abstention reason contains expected substring
    - Finding count falls within expected range
    - NDVI delta mean falls within expected range (when findings expected)
    """
    prov: dict[str, Any] = getattr(bundle, "provenance", {})

    abstention_reason = _abstention_reason(prov)
    expected_outcome = expected["expected_outcome"]

    if expected_outcome == "abstention":
        assert abstention_reason is not None, (
            f"{example_dir.name}: expected abstention but no abstention_reason in bundle"
        )
        reason_substring = expected.get("abstention_reason_substring")
        if reason_substring:
            assert reason_substring.lower() in abstention_reason.lower(), (
                f"{example_dir.name}: abstention reason '{abstention_reason}' "
                f"does not contain expected substring '{reason_substring}'"
            )
        return

    assert abstention_reason is None, (
        f"{example_dir.name}: expected findings but pipeline abstained: {abstention_reason}"
    )

    findings = prov.get("findings", [])
    if isinstance(findings, dict):
        finding_count = findings.get("count", 0)
    else:
        finding_count = len(findings)

    count_range = expected.get("finding_count", {})
    min_count = count_range.get("min", 0)
    max_count = count_range.get("max", 999)

    assert min_count <= finding_count <= max_count, (
        f"{example_dir.name}: finding count {finding_count} "
        f"not in expected range [{min_count}, {max_count}]"
    )

    if finding_count > 0 and expected.get("ndvi_delta_range"):
        ndvi_min, ndvi_max = expected["ndvi_delta_range"]
        ndvi_mean = _ndvi_delta_mean(prov, findings)
        if ndvi_mean is not None:
            assert ndvi_min <= ndvi_mean <= ndvi_max, (
                f"{example_dir.name}: NDVI delta mean {ndvi_mean} "
                f"not in expected range [{ndvi_min}, {ndvi_max}]"
            )


def _abstention_reason(prov: dict[str, Any]) -> str | None:
    """Read abstention reason from current or legacy provenance shape."""
    abstention = prov.get("abstention")
    if isinstance(abstention, dict):
        reason = abstention.get("reason")
        return str(reason) if reason is not None else None
    reason = prov.get("abstention_reason")
    return str(reason) if reason is not None else None


def _ndvi_delta_mean(prov: dict[str, Any], findings: object) -> float | None:
    """Read mean NDVI delta from current finding metrics or legacy provenance."""
    if isinstance(findings, list):
        values = []
        for finding in findings:
            if not isinstance(finding, dict):
                continue
            metrics = finding.get("metrics", {})
            if not isinstance(metrics, dict):
                continue
            ndvi = metrics.get("ndvi_delta_mean")
            if isinstance(ndvi, int | float):
                values.append(float(ndvi))
        if values:
            return sum(values) / len(values)

    ndvi = prov.get("ndvi_delta_mean")
    return float(ndvi) if isinstance(ndvi, int | float) else None


def load_aoi(example_dir: Path) -> dict[str, Any]:
    """Load the AOI polygon geometry from aoi.geojson."""
    with open(example_dir / "aoi.geojson") as f:
        feature = json.load(f)
    return feature["geometry"]


def load_request_params(example_dir: Path) -> dict[str, Any]:
    """Load request.json params."""
    with open(example_dir / "request.json") as f:
        return json.load(f)


def load_expected(example_dir: Path) -> dict[str, Any]:
    """Load expected.json."""
    with open(example_dir / "expected.json") as f:
        return json.load(f)
