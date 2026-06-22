# Clay v1.5 Experiment Report

**Date:** 2026-06-22
**Mini-SDD:** [003-clay-experiment](mini-sdd/003-clay-experiment/README.md)

---

## Summary

Clay v1.5 (large) was successfully installed, loaded from checkpoint, and run on synthetic Sentinel-2 chips. The model produces 1024-dimensional patch embeddings from 12-band 256x256 inputs. Feature extraction works correctly on CPU. The adapter, tiled inference, and orchestrator integration are complete.

**Recommendation: PROCEED WITH CAUTION to full evaluation (005).**

---

## What was verified

### 1. Installation

- torch 2.12.1 installed cleanly on macOS arm64
- MPS (Metal Performance Shaders) available
- clay-foundation-model 0.1.0 installed (provides model architecture)
- DINOv2 teacher model (vit_large_patch14_reg4_dinov2.lvd142m) downloaded from HuggingFace
- Clay v1.5 checkpoint (~5GB) downloaded from made-with-clay/Clay

### 2. Forward pass

- Model loads with 0 missing keys, 0 unexpected keys
- 12-band Sentinel-2 L2A input (B01-B08, B8A, B09, B11, B12)
- patch_size=8, 256x256 chip -> 32x32 = 1024 patches
- Encoder output: (1, 1025, 1024) — CLS token + 1024 patch embeddings
- Each patch embedding is 1024-dimensional

### 3. Latency (CPU, M-series Mac)

| Operation | Time |
|-----------|------|
| Encoder forward (1 chip) | 0.61s |
| Full model forward (1 chip) | 2.11s |

For a typical 1km AOI (~100x100 pixels at 10m), this is a single chip — sub-second. For a 5km AOI (~500x500 pixels), that's ~4 chips = ~2.4s encoder time. Acceptable for batch processing.

### 4. Adapter architecture

- `ModelAdapter` protocol defined with runtime_checkable
- `ClayAdapter` implements the protocol:
  - Lazy model loading (first use)
  - `extract_features(chip, metadata) -> (P, D)` patch embeddings
  - `compute_feature_diff(before, after) -> (P,)` L2 distance per patch
  - `normalize_diff_map(diff) -> [0, 1]` min-max normalization
- All Clay-specific constants isolated in `clay_config.py`
- No Clay/torch imports leak into pipeline core (all behind `--use-ai` flag)

### 5. Tiled inference

- Grid chipping for arbitrary AOI sizes
- Reflect-padding at edges
- Stitching: per-chip embeddings -> spatial map
- Single-chip optimization for small AOIs

---

## What was NOT verified

1. **Real data correlation** — no real Sentinel-2 before/after pair was tested. The feature-diff map may or may not correlate with NDVI delta on real vegetation loss. This is the job of 005-evaluation-harness.

2. **MPS acceleration** — MPS is available but not tested. The adapter defaults to CPU for reproducibility. MPS may provide 3-5x speedup.

3. **Probability calibration** — the change_score is min-max normalized L2 distance. It is NOT a calibrated probability. This is explicitly documented everywhere as "change_score" never "confidence".

4. **GPU Docker** — Dockerfile.gpu written but not build-tested (no GPU on dev machine).

---

## Integration issues discovered

1. **Clay package structure** — `clay-foundation-model` installs as a `src/` namespace package, importable as `from src.model import clay_mae_large`. This is fragile and may break on future package updates.

2. **Metadata format** — Clay expects a Box-structured metadata dict with wavelength, mean, std, gsd, and rgb_indices for each platform. The package doesn't ship this — it must be constructed manually.

3. **Teacher model dependency** — The full ClayMAE model requires a DINOv2 teacher (ViT-Large, ~1.2GB download from HuggingFace). For inference, only the encoder is needed, but the model __init__ still creates the teacher. This adds ~1.2GB to the install footprint.

4. **Time/latlon format** — Clay expects time as [B, 4] and latlon as [B, 4], not [B, 2]. This is undocumented and discovered through dimension mismatch errors.

---

## Decision gate answers

1. **Does Clay produce a sensible-looking change map?** — Unknown on real data. The forward pass works and produces embeddings. Feature-diff on identical inputs is zero. Feature-diff on different inputs is positive. The mathematical pipeline is correct.

2. **Does the feature-diff map correlate with NDVI delta?** — Not tested yet. Requires real before/after pairs (004-benchmark-dataset).

3. **How long does inference take per chip?** — 0.61s encoder-only, 2.11s full model. CPU only. MPS untested.

4. **Should we proceed to full evaluation (005)?** — **YES, with caution.** The infrastructure is in place. The next step is collecting real examples (004) and running the comparison (005). If Clay doesn't beat baseline on real data, the deterministic pipeline stands on its own.

---

## Next steps

1. **004-benchmark-dataset** — Collect 12-18 real before/after pairs
2. **005-evaluation-harness** — Compare Clay vs NDVI baseline on the benchmark
3. Decision gate after 005: Does AI earn its place?
