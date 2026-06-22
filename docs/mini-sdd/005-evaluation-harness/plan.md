# Plan — Full AI Evaluation + Baseline Comparison

**Parent**: [../README.md](../README.md)

---

## 1. Repo facts

| Area | Current state | After prerequisite |
|---|---|---|
| Clay adapter | Not built | Built in 003 |
| Benchmark dataset | None | 12-18 examples from 004 |
| Comparison harness | None | Will be built here |
| Decision gate | Not run | Roadmap Phase 4 gate |

---

## 2. Execution order

1. **Phase 0 — Comparison harness** — `src/oberon/ai/comparison.py` with metrics
2. **Phase 1 — Run baseline on benchmark** — record deterministic-only results
3. **Phase 2 — Run AI on benchmark** — record Clay + baseline results
4. **Phase 3 — Statistical comparison** — produce metrics, evaluate significance
5. **Phase 4 — Decision gate** — publish `docs/EVALUATION_REPORT.md`

---

## 3. Metrics (from Product Brief §8 + Roadmap PDF lines 538-555)

| Metric | Computation | Minimum release gate |
|---|---|---|
| Precision at K | Of top-K findings, fraction confirmed true | >0.7 on held-out |
| Recall at review budget | True changes found within N reviewed | >0.8 at K=5 |
| False positive rate | Spurious findings per 100 AOIs | <15 |
| Abstention accuracy | Correct abstention / total abstention calls | >0.9 |
| Performance by geography | Per-holdout-group breakdown | Within 10% of overall |
| Performance by season | Per-season-pair breakdown | Documented if worse |
| AI delta | Improvement of AI+branch over baseline-only | >= 10% precision@K |

### 3.1 ComparisonReport dataclass

```python
@dataclass
class ComparisonReport:
    baseline: dict[str, float]           # prec@K, recall@K, fp_rate, abstain_acc
    ai: dict[str, float]                 # same metrics with AI enabled
    delta: dict[str, float]              # ai - baseline
    per_example: list[dict]              # per-example breakdown
    holdout_results: dict[str, dict]    # per-holdout-group metrics
    limitations: list[str]
    decision: Literal["AI_wins", "AI_ties", "AI_loses", "insufficient_data"]
```

---

## 4. Exact changes

### 4.1 New files
- `src/oberon/ai/comparison.py` — ComparisonReport, evaluate(), compute_metrics()
- `scripts/run_evaluation.py` — CLI script that runs both paths on benchmark

### 4.2 Modified files
- `src/oberon/ai/__init__.py` — export comparison.py
- `pyproject.toml` — add `scripts` entry if needed

### 4.3 Test files
- `tests/ai/test_comparison.py` — precision@K, recall@K, fp_rate, abstention accuracy

---

## 5. Decision gate criteria (Roadmap PDF lines 538-559)

| Outcome | Condition | Action |
|---|---|---|
| AI wins | Precision@5 improvement > 10% over baseline on held-out | Ship AI as default, baseline as fallback |
| AI ties | Improvement < 10% or confidence interval overlaps zero | Ship deterministic-only, document AI experimental |
| AI loses | Baseline outperforms AI | Remove AI from default path; keep adapter for experiments |
| Insufficient data | < 10 examples or confidence intervals unreasonably wide | Publish report, say "more data needed" |

---

## 6. Risk register

| Risk | Mitigation |
|---|---|
| Too few examples for statistical significance | Phase 3: produce confidence intervals; decision falls to "insufficient_data" |
| AI slower than baseline but marginally better | Phase 4: note latency trade-off in report |
| Clay fails on some regions but not others | Phase 2: per-geography breakdown catches this |
| Decision ambiguous | Phase 4: document honestly; default to deterministic-only for robustness |

---

## 7. End-phase cleanup

- `docs/EVALUATION_REPORT.md` published (NOT a private doc — committed to repo)
- If AI wins: update SYSTEM_DESIGN.md AI branch, update AGENTS.md
- IF AI loses: no architecture changes; keep adapter code as documented experiment
