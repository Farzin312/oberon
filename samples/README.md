# Sample AOIs

Ready-to-use GeoJSON polygons for testing Oberon. Each file has recommended
date windows and expected results in its `properties` block.

## Available samples

| File | Location | Change type | Recommended before | Recommended after |
|------|----------|-------------|--------------------|--------------------|
| `amazon-deforestation.geojson` | Para, Brazil | Deforestation | 2024-01-01 to 2024-03-01 | 2024-07-01 to 2024-09-01 |
| `iowa-cropland.geojson` | Iowa, USA | Seasonal cropland | 2024-06-01 to 2024-08-01 | 2024-10-01 to 2024-12-01 |
| `california-wildfire.geojson` | California, USA | Wildfire scar | 2024-01-01 to 2024-06-01 | 2024-09-01 to 2024-12-01 |
| `portugal-wildfire.geojson` | Central Portugal | Wildfire scar | 2024-01-01 to 2024-06-01 | 2024-09-01 to 2024-12-01 |

## Usage

```bash
# Run analysis with a sample AOI
oberon analyze \
  --aoi samples/amazon-deforestation.geojson \
  --before-start 2024-01-01 --before 2024-03-01 \
  --after-start 2024-07-01 --after 2024-09-01 \
  -o output/
```

## Creating your own AOI

Three options, easiest first:

### 1. Use `oberon aoi` (built-in)

```bash
# Generate a 5km box around a coordinate
oberon aoi --lat -7.475 --lon -55.175 -o my-aoi.geojson

# Custom buffer (10km box)
oberon aoi --lat 41.82 --lon -93.62 --buffer 5.0 -o my-aoi.geojson

# Pipe directly into analyze
oberon aoi --lat -7.475 --lon -55.175 > /tmp/aoi.geojson
oberon analyze --aoi /tmp/aoi.geojson --before-start 2024-01-01 --before 2024-03-01 ...
```

### 2. Draw on a map (geojson.io)

1. Go to [geojson.io](https://geojson.io)
2. Click the polygon tool, draw your area
3. Copy the GeoJSON from the right panel
4. Save as `my-aoi.geojson`

### 3. Use QGIS or any GIS tool

Draw a polygon, export as GeoJSON. Oberon accepts both Feature and bare
Geometry objects, as well as FeatureCollections (uses the first feature).

## Tips

- Keep AOIs small (under 50,000 ha / 500 km^2). Larger areas hit memory limits.
- Tropical regions have frequent cloud cover. Use `--composite` or wider date
  windows.
- The `properties` block in each sample file is metadata only — Oberon reads
  the `geometry` block for analysis.
