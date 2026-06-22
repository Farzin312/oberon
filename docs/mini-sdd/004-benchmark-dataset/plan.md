# Plan — Benchmark Dataset + Golden Tests

**Parent**: [../README.md](../README.md)

---

## 1. Repo facts

| Area | Current state | Source |
|---|---|---|
| Test data | `tests/data/sample.geojson` (1 polygon) | `tests/data/` |
| Integration tests | None — all 114 use mocks | pytest |
| Task contract | Defined in 002 | `docs/TASK_CONTRACT.md` |
| Clay experiment | Optional feature-diff map | 003 |
| Calibration | Thresholds are ponytail defaults | `change_detection.py` |

---

## 2. Execution order

1. **Phase 0 — Structure** — directory layout, expected.json schema
2. **Phase 1 — Collect examples** — 10-20 via interactive search (manual + STAC)
3. **Phase 2 — Golden test harness** — pytest integration framework
4. **Phase 3 — Run + calibrate** — execute, record thresholds, produce calibration report
5. **Phase 4 — Document** — diversity table, holdout protocol, known limitations

---

## 3. Structure

### 3.1 Per-example layout

```
tests/data/benchmark/
├── README.md                    ← dataset description + holdout protocol
├── 01-costa-rica-deforest/
│   ├── aoi.geojson              ← input polygon (Feature)
│   ├── request.json             ← ChangeRequest fields (before/after dates, task)
│   ├── expected.json            ← expected outcome
│   └── review.md                ← human review notes
├── ...
└── 12-seasonal-variation/       ← known failure/edge case
```

### 3.2 expected.json schema

```json
{
  "expected_outcome": "findings" | "abstention",
  "abstention_reason_substring": null | "cloud" | "seasonal" | "insufficient",
  "finding_count": {"min": 1, "max": 5},
  "ndvi_delta_range": [-0.5, -0.1],
  "area_ha_min": 0.5,
  "region": "tropical" | "temperate" | "boreal" | "arid",
  "ecosystem": "rainforest" | "savanna" | "cropland" | "temperate_forest",
  "time_interval_months": 6,
  "season_comparison": "same_season" | "cross_season",
  "holdout_group": "geo_<region>" | "temporal_<pair>"
}
```

### 3.3 Required diversity (Roadmap PDF lines 453-476)

| Category | Count | Example location |
|---|---|---|
| Clear vegetation loss | 4-6 | Costa Rica, Amazon, Indonesia, Zambia |
| No change stable | 2-3 | Mature forest, well-watered agriculture |
| Seasonal variation | 2 | Temperate forest summer→fall |
| Cloud-contaminated | 1 | Tropical peak-wet |
| Cross-season mismatch | 1 | Summer vs winter same location |
| Burn/disturbance | 1-2 | Recent wildfire scar |
| Regional diversity | At least 3 regions | Central America, South America, Africa |

Total target: **12-18 examples**

### 3.4 Holdout protocol

- **Geographic groups:** geo_central_america, geo_south_america, geo_africa, geo_asia
- **Temporal groups:** temporal_same_season, temporal_cross_season, temporal_cloud
- Calibration uses all examples from N-1 geographic groups
- Validation uses held-out group
- Document exact splits in README

---

## 4. Golden test harness

### 4.1 conftest.py additions

```python
def pytest_addoption(parser):
    parser.addoption("--run-integration", action="store_true")

def pytest_collection_modifyitems(config, items):
    if not config.getoption("--run-integration"):
        skip = pytest.mark.skip(reason="pass --run-integration")
        for item in items:
            if "integration" in item.keywords:
                item.add_marker(skip)
```

### 4.2 Test structure

```python
@pytest.mark.integration
@pytest.mark.parametrize("example_dir", BENCHMARK_DIRS)
def test_golden_example(example_dir, tmp_path):
    aoi = load_json(...)
    request = ChangeRequest(**params)
    bundle = run_analysis(request, tmp_path)
    expected = load_json(f"{example_dir}/expected.json")
    validate_against_expected(bundle, expected)
```

### 4.3 Calibration output

After golden tests pass:
- `tests/data/benchmark/calibration_report.json` — per-example actual vs expected
- Key metrics: abstention accuracy, finding count range, NDVI delta fidelity

---

## 5. Risk register

| Risk | Mitigation |
|---|---|
| Live STAC/COG flaky in tests | retry decorator + skip-on-network-error |
| Reviewer bias in labeling | Cross-reference with external sources (Global Forest Watch, Hansen data) |
| Too few examples for statistical claims | Document as "technical benchmark" not "evaluation dataset" |
| COG URLs change | Centralized in stac_discovery.py — already done |
| Manual collection takes too long | Start with 8 clear examples, expand after 005 |
