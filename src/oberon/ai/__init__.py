"""AI model adapters — foundation model integration for Oberon.

All AI models live behind the ModelAdapter protocol. No torch or model
imports leak into the pipeline core. The orchestrator imports from this
package only when --use-ai is set.

The comparison module provides the evaluation harness for the
AI-vs-baseline decision gate (005).
"""

from oberon.ai.comparison import (
    ComparisonReport,
    ExampleResult,
    compute_abstention_accuracy,
    compute_fp_rate,
    compute_metrics,
    compute_precision_at_k,
    compute_recall_at_k,
    evaluate,
)

__all__ = [
    "ComparisonReport",
    "ExampleResult",
    "compute_abstention_accuracy",
    "compute_fp_rate",
    "compute_metrics",
    "compute_precision_at_k",
    "compute_recall_at_k",
    "evaluate",
]
