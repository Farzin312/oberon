# 005 — Full AI Evaluation + Baseline Comparison

**Parent**: [../README.md](../README.md)

Roadmap Phase 4: Run the deterministic baseline AND the Clay-equipped pipeline on the benchmark dataset. Compare metrics. Publish the decision gate: does AI earn its place?

- **Reference:** Roadmap PDF Phase 4 (lines 513-559), Product Brief §8 Evaluation Plan
- **Prerequisite:** 003-clay-experiment, 004-benchmark-dataset
- **Decision gate:** decision gate (Gate 1 in Product Brief §12)

> **Hard rules:**
> 1. The same benchmark dataset is used for BOTH baseline and AI runs — identical inputs.
> 2. Geographic holdouts are strict: held-out regions are NEVER used for calibration.
> 3. The report must publish negative results honestly. A negative result is valuable evidence.
> 4. The comparison script is deterministic — rerunning produces the same numbers.

---

## Locked decisions

| # | Decision | Choice |
|---|----------|--------|
| 1 | Comparison tool | Python script: `scripts/run_evaluation.py` |
| 2 | Threshold for AI inclusion | >= 10% precision@5 improvement on held-out examples |
| 3 | Report format | `docs/EVALUATION_REPORT.md` — markdown with tables |
| 4 | Per-example detail | Included in report for transparency |
| 5 | If AI loses | Remove from default path; `--use-ai` remains as experimental flag |

---

## In scope vs NOT in scope

### IN SCOPE
- Comparison harness (baseline vs AI on same benchmark)
- Precision@K, recall@K, FP rate, abstention accuracy
- Per-geography and per-season breakdown
- Statistical confidence intervals
- Decision gate document

### NOT in scope
- Additional dataset collection (004- is the only source)
- Task-specific head training (post-pilot)
- Calibrated probabilities (post-pilot with task head)
- Production deployment changes

---

## Risk warnings

- A negative result (AI doesn't help) may feel like failure but is the most valuable possible outcome of this mini-SDD. It prevents unnecessary infrastructure investment.
- If 003-clay-experiment already showed Clay doesn't work, this mini-SDD confirms that formally and the result is deterministic-only.
