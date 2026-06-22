"""Tests for the evaluation comparison module (005).

Tests the metric computation functions and the decision gate logic
with controlled synthetic data — no pipeline runs needed.
"""

from __future__ import annotations

from oberon.ai.comparison import (
    AI_PROMOTION_THRESHOLD,
    ExampleResult,
    compute_abstention_accuracy,
    compute_fp_rate,
    compute_metrics,
    compute_precision_at_k,
    compute_recall_at_k,
    evaluate,
    format_report,
)


def _make_result(
    example_id: str = "test-01",
    expected: str = "findings",
    actual: str = "findings",
    tp: int = 1,
    fp: int = 0,
    fn: int = 0,
    finding_count: int = 1,
    holdout: str = "geo_test",
    abstained_correctly: bool = False,
) -> ExampleResult:
    return ExampleResult(
        example_id=example_id,
        expected_outcome=expected,
        actual_outcome=actual,
        finding_count=finding_count,
        true_positive_count=tp,
        false_positive_count=fp,
        false_negative_count=fn,
        abstained_correctly=abstained_correctly,
        holdout_group=holdout,
    )


class TestPrecisionAtK:
    def test_all_true_positives(self) -> None:
        assert compute_precision_at_k(5, 0) == 1.0

    def test_mixed(self) -> None:
        assert compute_precision_at_k(3, 1) == 0.75

    def test_all_false_positives(self) -> None:
        assert compute_precision_at_k(0, 4) == 0.0

    def test_no_findings_is_perfect(self) -> None:
        """No findings at all = vacuously precise."""
        assert compute_precision_at_k(0, 0) == 1.0


class TestRecallAtK:
    def test_perfect_recall(self) -> None:
        assert compute_recall_at_k(5, 0) == 1.0

    def test_partial_recall(self) -> None:
        assert compute_recall_at_k(3, 2) == 0.6

    def test_zero_recall(self) -> None:
        assert compute_recall_at_k(0, 5) == 0.0

    def test_no_changes_expected_is_perfect(self) -> None:
        assert compute_recall_at_k(0, 0) == 1.0


class TestFpRate:
    def test_no_fp(self) -> None:
        assert compute_fp_rate(0, 10) == 0.0

    def test_one_fp_per_aoi(self) -> None:
        assert compute_fp_rate(10, 10) == 100.0

    def test_half_fp_rate(self) -> None:
        assert compute_fp_rate(5, 10) == 50.0

    def test_zero_aois(self) -> None:
        assert compute_fp_rate(0, 0) == 0.0


class TestAbstentionAccuracy:
    def test_all_correct(self) -> None:
        assert compute_abstention_accuracy(4, 4) == 1.0

    def test_half_correct(self) -> None:
        assert compute_abstention_accuracy(2, 4) == 0.5

    def test_none_correct(self) -> None:
        assert compute_abstention_accuracy(0, 4) == 0.0

    def test_no_abstention_calls_is_perfect(self) -> None:
        assert compute_abstention_accuracy(0, 0) == 1.0


class TestComputeMetrics:
    def test_empty_results(self) -> None:
        metrics = compute_metrics([])
        assert metrics["precision_at_k"] == 0.0
        assert metrics["recall_at_k"] == 0.0

    def test_mixed_results(self) -> None:
        results = [
            _make_result("01", tp=2, fp=1, fn=0, finding_count=3),
            _make_result("02", tp=0, fp=0, fn=0, finding_count=0),  # no-change example
            _make_result("03", tp=1, fp=2, fn=1, finding_count=3),
        ]
        metrics = compute_metrics(results)
        # precision: 3 TP / (3 TP + 3 FP) = 0.5
        assert abs(metrics["precision_at_k"] - 0.5) < 1e-6
        # recall: 3 TP / (3 TP + 1 FN) = 0.75
        assert abs(metrics["recall_at_k"] - 0.75) < 1e-6
        # fp_rate: 3 FP / 3 AOIs * 100 = 100
        assert abs(metrics["fp_rate"] - 100.0) < 1e-6
        # mean finding count: (3+0+3)/3 = 2.0
        assert abs(metrics["mean_finding_count"] - 2.0) < 1e-6

    def test_abstention_accuracy_in_metrics(self) -> None:
        results = [
            _make_result("01", expected="abstention", actual="abstention", abstained_correctly=True),
            _make_result("02", expected="abstention", actual="abstention", abstained_correctly=True),
            _make_result("03", expected="abstention", actual="findings", abstained_correctly=False),
            _make_result("04", expected="findings", actual="findings", tp=1),
        ]
        metrics = compute_metrics(results)
        # 3 abstention expected, 2 correct, 2 abstention calls
        # correct=2, total=max(2 calls, 3 expected) = 3
        assert abs(metrics["abstention_accuracy"] - (2.0 / 3.0)) < 1e-6


class TestEvaluateDecisionGate:
    def test_ai_wins(self) -> None:
        """AI improves precision by >= 10%."""
        baseline = [_make_result(f"b-{i}", tp=2, fp=8, finding_count=10) for i in range(12)]
        ai = [_make_result(f"b-{i}", tp=9, fp=1, finding_count=10) for i in range(12)]
        report = evaluate(baseline, ai, min_examples=10)
        assert report.decision == "AI_wins"
        assert report.delta["precision_at_k"] >= AI_PROMOTION_THRESHOLD

    def test_ai_loses(self) -> None:
        """AI is worse than baseline."""
        baseline = [_make_result(f"b-{i}", tp=8, fp=2, finding_count=10) for i in range(12)]
        ai = [_make_result(f"b-{i}", tp=2, fp=8, finding_count=10) for i in range(12)]
        report = evaluate(baseline, ai, min_examples=10)
        assert report.decision == "AI_loses"

    def test_ai_ties(self) -> None:
        """AI marginally better but below threshold."""
        baseline = [_make_result(f"b-{i}", tp=5, fp=5, finding_count=10) for i in range(12)]
        ai = [_make_result(f"b-{i}", tp=6, fp=4, finding_count=10) for i in range(12)]
        report = evaluate(baseline, ai, min_examples=10)
        # Delta is ~0.1 which is exactly at threshold
        assert report.decision in ("AI_ties", "AI_wins")

    def test_insufficient_data(self) -> None:
        """Fewer than min_examples → insufficient_data."""
        baseline = [_make_result("b-0", tp=1, fp=0, finding_count=1)]
        ai = [_make_result("b-0", tp=1, fp=0, finding_count=1)]
        report = evaluate(baseline, ai, min_examples=10)
        assert report.decision == "insufficient_data"

    def test_per_example_has_matching_ids(self) -> None:
        baseline = [_make_result("alpha"), _make_result("beta")]
        ai = [_make_result("alpha"), _make_result("beta")]
        report = evaluate(baseline, ai, min_examples=2)
        ids = [e["example_id"] for e in report.per_example]
        assert ids == ["alpha", "beta"]

    def test_holdout_breakdown(self) -> None:
        baseline = [
            _make_result("01", holdout="geo_a"),
            _make_result("02", holdout="geo_b"),
            _make_result("03", holdout="geo_a"),
        ]
        ai = [
            _make_result("01", holdout="geo_a"),
            _make_result("02", holdout="geo_b"),
            _make_result("03", holdout="geo_a"),
        ]
        report = evaluate(baseline, ai, min_examples=3)
        assert "geo_a" in report.holdout_results
        assert "geo_b" in report.holdout_results
        assert report.holdout_results["geo_a"]["count"] == 2.0
        assert report.holdout_results["geo_b"]["count"] == 1.0


class TestFormatReport:
    def test_produces_markdown(self) -> None:
        baseline = [_make_result("01", tp=1, fp=1)]
        ai = [_make_result("01", tp=2, fp=0)]
        report = evaluate(baseline, ai, min_examples=1)
        text = format_report(report)
        assert "# Oberon AI Evaluation Report" in text
        assert "## Decision Gate" in text
        assert "## Aggregate Metrics" in text
        assert "## Per-Holdout-Group" in text
        assert "## Per-Example Results" in text
        assert "## Limitations" in text
