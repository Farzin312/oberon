# Oberon AI Evaluation Report

## Decision Gate

**Result: AI_ties**

## Aggregate Metrics

| Metric | Baseline | AI | Delta |
|--------|----------|----|-------|
| precision_at_k | 0.1266 | 0.1266 | +0.0000 |
| recall_at_k | 0.9091 | 0.9091 | +0.0000 |
| fp_rate | 1150.0000 | 1150.0000 | +0.0000 |
| abstention_accuracy | 0.2500 | 0.2500 | +0.0000 |
| mean_finding_count | 13.1667 | 13.1667 | +0.0000 |

## Per-Holdout-Group

| Group | Baseline Precision | AI Precision | Count |
|-------|-------------------|-------------|-------|
| geo_africa | 0.2500 | 0.2500 | 1 |
| geo_asia | 1.0000 | 1.0000 | 2 |
| geo_central_america | 0.1200 | 0.1200 | 2 |
| geo_europe | 0.2000 | 0.2000 | 1 |
| geo_north_america | 0.1212 | 0.1212 | 2 |
| geo_south_america | 0.2000 | 0.2000 | 1 |
| temporal_cross_season | 0.0000 | 0.0000 | 3 |

## Per-Example Results

| Example | Holdout | Baseline | AI | Baseline Findings | AI Findings |
|---------|---------|----------|----|-------------------|-------------|
| 01-costa-rica-deforest | geo_central_america | findings | findings | 20 | 20 |
| 02-amazon-para-clearcut | geo_south_america | findings | findings | 20 | 20 |
| 03-borneo-palm-oil | geo_asia | abstention | abstention | 0 | 0 |
| 04-zambia-miombo-clearing | geo_africa | findings | findings | 20 | 20 |
| 05-borneo-stable-forest | geo_asia | abstention | abstention | 0 | 0 |
| 06-iowa-stable-cropland | geo_north_america | findings | findings | 13 | 13 |
| 07-temperate-summer-to-fall | temporal_cross_season | findings | findings | 20 | 20 |
| 08-finland-boreal-seasonal | temporal_cross_season | findings | findings | 20 | 20 |
| 09-costa-rica-cloud-wet | geo_central_america | findings | findings | 5 | 5 |
| 10-iowa-summer-vs-winter | temporal_cross_season | abstention | abstention | 0 | 0 |
| 11-portugal-wildfire-2024 | geo_europe | findings | findings | 20 | 20 |
| 12-california-fire-2024 | geo_north_america | findings | findings | 20 | 20 |

## Limitations

- 12 examples is a technical benchmark, not a statistically powered evaluation
