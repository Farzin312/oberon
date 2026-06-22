#!/usr/bin/env python
"""Evaluation runner: baseline vs AI on the benchmark dataset.

Runs the deterministic baseline pipeline and (optionally) the Clay-enhanced
AI branch on all benchmark examples, computes metrics, and produces a
ComparisonReport.

Usage:
    uv run python scripts/run_evaluation.py --baseline-only
    uv run python scripts/run_evaluation.py --ai-enabled
    uv run python scripts/run_evaluation.py --both

Output:
    docs/EVALUATION_REPORT.md  (formatted comparison report)
    stdout: summary metrics table

Note: This script requires live STAC/COG network access for each example.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path

# Add src to path for direct script execution.
PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from oberon.ai.comparison import ExampleResult  # noqa: E402

BENCHMARK_DIR = PROJECT_ROOT / "tests" / "data" / "benchmark"


def discover_examples() -> list[Path]:
    """Return sorted benchmark example directories."""
    if not BENCHMARK_DIR.exists():
        return []
    return sorted(
        d
        for d in BENCHMARK_DIR.iterdir()
        if d.is_dir() and (d / "expected.json").exists() and (d / "aoi.geojson").exists()
    )


def _load_example(example_dir: Path) -> dict:
    """Load all files for a benchmark example."""
    with open(example_dir / "aoi.geojson") as f:
        aoi = json.load(f)
    with open(example_dir / "expected.json") as f:
        expected = json.load(f)
    with open(example_dir / "request.json") as f:
        request_params = json.load(f)
    return {"aoi": aoi, "expected": expected, "request": request_params}


def _build_change_request(example_data: dict):  # type: ignore[no-untyped-def]
    """Build a ChangeRequest from example data."""
    from oberon.core import ChangeRequest

    params = example_data["request"]
    return ChangeRequest(
        geometry=example_data["aoi"]["geometry"],
        before=(date.fromisoformat(params["before"][0]), date.fromisoformat(params["before"][1])),
        after=(date.fromisoformat(params["after"][0]), date.fromisoformat(params["after"][1])),
        task=params.get("task", "vegetation_disturbance"),
        max_cloud_fraction=params.get("max_cloud_fraction", 0.15),
        min_valid_pixels=params.get("min_valid_pixels", 0.30),
        min_change_area_ha=params.get("min_change_area_ha", 0.5),
    )


def run_pipeline_on_example(  # type: ignore[no-untyped-def]
    example_dir: Path,
    use_ai: bool,
    output_base: Path,
):
    """Run the pipeline on a single example and return the evidence bundle."""
    from oberon.cli.orchestrator import run_analysis

    example_data = _load_example(example_dir)
    request = _build_change_request(example_data)

    output_dir = output_base / example_dir.name
    output_dir.mkdir(parents=True, exist_ok=True)

    return run_analysis(request, output_dir, use_ai=use_ai)


def result_to_example_result(  # type: ignore[no-untyped-def]
    bundle: object,
    expected: dict,
    example_id: str,
    holdout_group: str,
) -> ExampleResult:
    """Convert a pipeline EvidenceBundle to an ExampleResult for metrics."""
    from oberon.ai.comparison import ExampleResult

    prov = getattr(bundle, "provenance", {})
    abstention_reason = prov.get("abstention_reason")
    actual_outcome = "abstention" if abstention_reason is not None else "findings"

    findings = prov.get("findings", [])
    finding_count = len(findings) if isinstance(findings, list) else findings.get("count", 0)

    expected_outcome = expected["expected_outcome"]

    # Determine TP/FP/FN from expected vs actual.
    if expected_outcome == "findings" and actual_outcome == "findings":
        tp = finding_count
        fp = 0
        fn = 0
    elif expected_outcome == "findings" and actual_outcome == "abstention":
        tp = 0
        fp = 0
        fn = max(1, expected.get("finding_count", {}).get("min", 1))
    elif expected_outcome == "abstention" and actual_outcome == "findings":
        tp = 0
        fp = finding_count
        fn = 0
    else:  # both abstention
        tp = 0
        fp = 0
        fn = 0

    abstained_correctly = (
        expected_outcome == "abstention" and actual_outcome == "abstention"
    )

    return ExampleResult(
        example_id=example_id,
        expected_outcome=expected_outcome,
        actual_outcome=actual_outcome,
        finding_count=finding_count,
        true_positive_count=tp,
        false_positive_count=fp,
        false_negative_count=fn,
        abstained_correctly=abstained_correctly,
        holdout_group=holdout_group,
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run baseline vs AI evaluation on benchmark dataset.",
    )
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--baseline-only", action="store_true", help="Run deterministic baseline only")
    mode.add_argument("--ai-enabled", action="store_true", help="Run AI-enhanced pipeline only")
    mode.add_argument("--both", action="store_true", help="Run both and compare")
    parser.add_argument(
        "--output",
        type=Path,
        default=PROJECT_ROOT / "docs" / "EVALUATION_REPORT.md",
        help="Output report path (default: docs/EVALUATION_REPORT.md)",
    )
    args = parser.parse_args()

    examples = discover_examples()
    if not examples:
        print("No benchmark examples found in tests/data/benchmark/")
        return 1

    print(f"Found {len(examples)} benchmark examples")

    output_base = PROJECT_ROOT / "evaluation_output"
    baseline_results: list[ExampleResult] = []
    ai_results: list[ExampleResult] = []

    if args.baseline_only or args.both:
        print("\n=== Running baseline pipeline ===")
        for ex in examples:
            print(f"  {ex.name}...", end=" ", flush=True)
            try:
                data = _load_example(ex)
                bundle = run_pipeline_on_example(ex, use_ai=False, output_base=output_base / "baseline")
                result = result_to_example_result(
                    bundle, data["expected"], ex.name, data["expected"]["holdout_group"]
                )
                baseline_results.append(result)
                print("OK")
            except Exception as exc:
                print(f"ERROR: {exc}")

    if args.ai_enabled or args.both:
        print("\n=== Running AI-enhanced pipeline ===")
        for ex in examples:
            print(f"  {ex.name}...", end=" ", flush=True)
            try:
                data = _load_example(ex)
                bundle = run_pipeline_on_example(ex, use_ai=True, output_base=output_base / "ai")
                result = result_to_example_result(
                    bundle, data["expected"], ex.name, data["expected"]["holdout_group"]
                )
                ai_results.append(result)
                print("OK")
            except Exception as exc:
                print(f"ERROR: {exc}")

    if args.both and baseline_results and ai_results:
        print("\n=== Producing comparison report ===")
        from oberon.ai.comparison import evaluate, format_report

        report = evaluate(baseline_results, ai_results)
        report_text = format_report(report)

        with open(args.output, "w") as f:
            f.write(report_text)
        print(f"\nReport written to {args.output}")
        print(f"\nDecision: {report.decision}")
        print(f"Baseline precision@K: {report.baseline['precision_at_k']:.4f}")
        print(f"AI precision@K: {report.ai['precision_at_k']:.4f}")
        print(f"Delta: {report.delta['precision_at_k']:+.4f}")
    elif baseline_results:
        from oberon.ai.comparison import compute_metrics

        metrics = compute_metrics(baseline_results)
        print("\n=== Baseline metrics ===")
        for k, v in metrics.items():
            print(f"  {k}: {v:.4f}")
    elif ai_results:
        from oberon.ai.comparison import compute_metrics

        metrics = compute_metrics(ai_results)
        print("\n=== AI metrics ===")
        for k, v in metrics.items():
            print(f"  {k}: {v:.4f}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
