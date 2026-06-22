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

    abstention_reason = prov.get("abstention_reason")
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
        ndvi_mean = prov.get("ndvi_delta_mean")
        if ndvi_mean is not None:
            assert ndvi_min <= ndvi_mean <= ndvi_max, (
                f"{example_dir.name}: NDVI delta mean {ndvi_mean} "
                f"not in expected range [{ndvi_min}, {ndvi_max}]"
            )


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
