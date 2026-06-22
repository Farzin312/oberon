# Plan — Clay Feature Extraction Experiment

**Parent**: [../README.md](../README.md)

---

## 1. Repo facts

| Area | Current state | Source |
|---|---|---|
| Clay dependency | Not installed | pyproject.toml |
| ModelAdapter protocol | Does not exist | N/A |
| AI director | Does not exist | `src/oberon/ai/` dir not created |
| PreparedPair | Has all bands needed for Clay (10-band B02-B8A-B11-B12) | `core/__init__.py` |
| Orchestrator | Runs deterministic pipeline only | `cli/orchestrator.py` |
| CLI | No --use-ai flag | `cli/main.py` |
| Torch | Not installed | uv.lock |

---

## 2. Execution order

1. **Phase 0 — Adapter protocol** — define ModelAdapter Protocol, ModelResult dataclass, ai/ package
2. **Phase 1 — Install + smoke test** — get Clay running on one 256x256 chip
3. **Phase 2 — Tiled inference** — chip AOI, batch, stitch
4. **Phase 3 — Feature-diff map** — compare before/after features
5. **Phase 4 — Wire into orchestrator** — behind --use-ai flag
6. **Phase 5 — Decision gate document** — publish `docs/CLAY_EXPERIMENT_REPORT.md`

---

## 3. Architecture (minimal — experiment, not production)

### 3.1 ModelAdapter protocol

```python
class ModelAdapter(Protocol):
    @property
    def version(self) -> str: ...
    @property
    def required_bands(self) -> list[str]: ...
    @property
    def chip_size(self) -> int: ...
    def extract_features(self, chip: np.ndarray, metadata: dict) -> np.ndarray: ...
```

One implementation: `ClayAdapter` wrapping clay-v1.5.

### 3.2 ModelResult dataclass (core/__init__.py)

```python
@dataclass
class ModelResult:
    feature_diff_map: np.ndarray | None   # (H, W) float32
    change_score_map: np.ndarray | None   # (H, W) float32, NOT probability
    adapter_version: str
    model_version: str
    chip_count: int
    abstain: bool = False
    abstain_reason: str | None = None
```

### 3.3 Tiled inference

- Chip: 256x256, 10 bands (B02-B03-B04-B05-B06-B07-B08-B8A-B11-B12)
- Overlap: 32px
- Batch: 4 chips per batch (CPU-safe default)
- Stitch: feathered blending at overlap boundaries
- Padding: reflect-pad AOI edges that don't fill a full chip

### 3.4 Feature-diff

```
diff_map = L2_distance(before_features, after_features, axis=last)
normalized = (diff_map - diff_map.min()) / (diff_map.max() - diff_map.min() + eps)
# NOT a probability. Called "change_score" everywhere.
```

---

## 4. Exact changes

### 4.1 New
- `src/oberon/ai/__init__.py`
- `src/oberon/ai/model_adapter.py` — Protocol + ModelResult
- `src/oberon/ai/clay_adapter.py` — Clay v1.5 implementation
- `src/oberon/ai/tiled_inference.py` — chip → batch → stitch

### 4.2 Modified
- `src/oberon/core/__init__.py` — add ModelResult
- `src/oberon/cli/main.py` — add `--use-ai` flag
- `src/oberon/cli/orchestrator.py` — optional AI branch, parallel to baseline
- `src/oberon/artifacts/provenance.py` — model_version, adapter_version fields
- `pyproject.toml` — add `[ai]` extras (torch, clay)
- `docs/CLAY_EXPERIMENT_REPORT.md` (NEW) — findings

### 4.3 Test files (mocked)
- `tests/ai/test_model_adapter.py`
- `tests/ai/test_clay_adapter.py`
- `tests/ai/test_tiled_inference.py`
- `tests/cli/test_analyze.py` — --use-ai flag test

---

## 5. Risk register

| Risk | Mitigation |
|---|---|
| Clay requires GPU, runs slowly on CPU | Phase 1: document known; CPU mode with torch.set_num_threads() |
| Clay chip preprocessing wrong (band order, normalization) | Validate against Clay's own Sentinel-2 example; unit test synthetic chip |
| Feature-diff map looks random on real data | That is a valid experimental result; publish honestly |
| Torch is a heavy dependency | Keep in `[ai]` extras; --use-ai flag errors gracefully if not installed |

---

## 6. Decision gate

The experiment report must answer :
1. Does Clay produce a sensible-looking change map on a clear vegetation-loss example?
2. Does the feature-diff map correlate with NDVI delta?
3. How long does inference take per chip (CPU)?
4. Should we proceed to full evaluation (mini-SDD 005)?

Gate output: `docs/CLAY_EXPERIMENT_REPORT.md` with explicit yes/no/uncertain recommendation.
