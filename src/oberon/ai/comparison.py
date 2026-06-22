"""Evaluation metrics and AI-vs-baseline comparison for Oberon.

Compares the deterministic baseline pipeline against the Clay-enhanced AI branch
on the benchmark dataset. Produces a ComparisonReport with the decision gate:
does AI earn its place?

Metrics: precision@K, recall@K, false positive rate, abstention accuracy.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


@dataclass
class ExampleResult:
    """Result of running the pipeline on a single benchmark example."""

    example_id: str
    expected_outcome: str  # "findings" or "abstention"
    actual_outcome: str  # "findings" or "abstention"
    finding_count: int
    true_positive_count: int  # findings that match expected change
    false_positive_count: int  # spurious findings
    false_negative_count: int  # missed changes
    abstained_correctly: bool  # True if abstention was the right call
    holdout_group: str
    ndvi_delta_mean: float | None = None


def compute_precision_at_k(
    true_positives: int,
    false_positives: int,
) -> float:
    """Precision at K: TP / (TP + FP).

    Returns 1.0 when there are no findings and none expected (perfect precision).
    Returns 0.0 when findings exist but all are false positives.
    """
    total = true_positives + false_positives
    if total == 0:
        return 1.0
    return true_positives / total


def compute_recall_at_k(
    true_positives: int,
    false_negatives: int,
) -> float:
    """Recall: TP / (TP + FN).

    Returns 1.0 when no changes were expected and none were found.
    Returns 0.0 when changes were expected but none found.
    """
    if true_positives + false_negatives == 0:
        return 1.0
    return true_positives / (true_positives + false_negatives)


def compute_fp_rate(
    false_positive_count: int,
    total_aois: int,
) -> float:
    """False positive rate: spurious findings per 100 AOIs."""
    if total_aois == 0:
        return 0.0
    return (false_positive_count / total_aois) * 100.0


def compute_abstention_accuracy(
    correct_abstentions: int,
    total_abstention_calls: int,
) -> float:
    """Fraction of abstention calls that were correct."""
    if total_abstention_calls == 0:
        return 1.0  # No abstention calls = vacuously correct.
    return correct_abstentions / total_abstention_calls


def compute_metrics(results: list[ExampleResult]) -> dict[str, float]:
    """Compute aggregate metrics across a set of example results.

    Returns dict with: precision_at_k, recall_at_k, fp_rate, abstention_accuracy,
    mean_finding_count.
    """
    if not results:
        return {
            "precision_at_k": 0.0,
            "recall_at_k": 0.0,
            "fp_rate": 0.0,
            "abstention_accuracy": 0.0,
            "mean_finding_count": 0.0,
        }

    total_tp = sum(r.true_positive_count for r in results)
    total_fp = sum(r.false_positive_count for r in results)
    total_fn = sum(r.false_negative_count for r in results)

    # Abstention: only count examples where abstention was expected.
    abstention_expected = [r for r in results if r.expected_outcome == "abstention"]
    correct_abstentions = sum(1 for r in abstention_expected if r.abstained_correctly)
    total_abstention_calls = sum(1 for r in results if r.actual_outcome == "abstention")

    return {
        "precision_at_k": compute_precision_at_k(total_tp, total_fp),
        "recall_at_k": compute_recall_at_k(total_tp, total_fn),
        "fp_rate": compute_fp_rate(total_fp, len(results)),
        "abstention_accuracy": compute_abstention_accuracy(
            correct_abstentions,
            max(total_abstention_calls, len(abstention_expected)),
        ),
        "mean_finding_count": sum(r.finding_count for r in results) / len(results),
    }


@dataclass
class ComparisonReport:
    """Full comparison of baseline vs AI-augmented pipeline.

    The decision field is the gate: AI_wins means AI ships as default,
    AI_ties means deterministic-only, AI_loses means AI stays experimental.
    """

    baseline: dict[str, float]
    ai: dict[str, float]
    delta: dict[str, float]
    per_example: list[dict[str, object]]
    holdout_results: dict[str, dict[str, float]]
    limitations: list[str]
    decision: Literal["AI_wins", "AI_ties", "AI_loses", "insufficient_data"]


# Threshold for AI to earn its place: >= 10% precision@K improvement.
AI_PROMOTION_THRESHOLD = 0.10


def evaluate(
    baseline_results: list[ExampleResult],
    ai_results: list[ExampleResult],
    min_examples: int = 10,
) -> ComparisonReport:
    """Run the full evaluation: compute metrics, compare, produce decision.

    Args:
        baseline_results: Results from deterministic-only pipeline.
        ai_results: Results from Clay-enhanced pipeline on the same examples.
        min_examples: Minimum example count for a valid decision.

    Returns:
        ComparisonReport with the decision gate result.
    """
    baseline_metrics = compute_metrics(baseline_results)
    ai_metrics = compute_metrics(ai_results)

    delta = {k: ai_metrics[k] - baseline_metrics[k] for k in baseline_metrics}

    # Per-example breakdown.
    per_example: list[dict[str, object]] = []
    for b, a in zip(baseline_results, ai_results, strict=True):
        per_example.append({
            "example_id": b.example_id,
            "holdout_group": b.holdout_group,
            "baseline_finding_count": b.finding_count,
            "ai_finding_count": a.finding_count,
            "baseline_outcome": b.actual_outcome,
            "ai_outcome": a.actual_outcome,
        })

    # Per-holdout-group breakdown.
    holdout_groups = {r.holdout_group for r in baseline_results}
    holdout_results: dict[str, dict[str, float]] = {}
    for group in holdout_groups:
        group_baseline = [r for r in baseline_results if r.holdout_group == group]
        group_ai = [r for r in ai_results if r.holdout_group == group]
        holdout_results[group] = {
            "baseline_precision": compute_metrics(group_baseline)["precision_at_k"],
            "ai_precision": compute_metrics(group_ai)["precision_at_k"],
            "count": float(len(group_baseline)),
        }

    # Decision gate.
    limitations: list[str] = []
    total_examples = len(baseline_results)

    if total_examples < min_examples:
        limitations.append(
            f"Only {total_examples} examples (need {min_examples} for statistical confidence)"
        )
        decision: Literal["AI_wins", "AI_ties", "AI_loses", "insufficient_data"] = (
            "insufficient_data"
        )
    elif delta["precision_at_k"] >= AI_PROMOTION_THRESHOLD:
        decision = "AI_wins"
    elif delta["precision_at_k"] < 0:
        decision = "AI_loses"
    else:
        decision = "AI_ties"

    limitations.append(
        "12 examples is a technical benchmark, not a statistically powered evaluation"
    )

    return ComparisonReport(
        baseline=baseline_metrics,
        ai=ai_metrics,
        delta=delta,
        per_example=per_example,
        holdout_results=holdout_results,
        limitations=limitations,
        decision=decision,
    )


def format_report(report: ComparisonReport) -> str:
    """Format a ComparisonReport as markdown text for docs/EVALUATION_REPORT.md."""
    lines: list[str] = []
    lines.append("# Oberon AI Evaluation Report")
    lines.append("")
    lines.append("## Decision Gate")
    lines.append("")
    lines.append(f"**Result: {report.decision}**")
    lines.append("")
    lines.append("## Aggregate Metrics")
    lines.append("")
    lines.append("| Metric | Baseline | AI | Delta |")
    lines.append("|--------|----------|----|-------|")
    for key in report.baseline:
        b = report.baseline[key]
        a = report.ai[key]
        d = report.delta[key]
        lines.append(f"| {key} | {b:.4f} | {a:.4f} | {d:+.4f} |")
    lines.append("")
    lines.append("## Per-Holdout-Group")
    lines.append("")
    lines.append("| Group | Baseline Precision | AI Precision | Count |")
    lines.append("|-------|-------------------|-------------|-------|")
    for group, metrics in sorted(report.holdout_results.items()):
        lines.append(
            f"| {group} | {metrics['baseline_precision']:.4f} | "
            f"{metrics['ai_precision']:.4f} | {int(metrics['count'])} |"
        )
    lines.append("")
    lines.append("## Limitations")
    lines.append("")
    for lim in report.limitations:
        lines.append(f"- {lim}")
    lines.append("")
    return "\n".join(lines)
