# Glossary

**Parent**: [README.md](../README.md)

| Term | Definition |
|------|-----------|
| **AOI** | Area of Interest — a GeoJSON polygon defining the land area to analyze |
| **COG** | Cloud-Optimized GeoTIFF — a TIFF with internal tiling and HTTP range requests enabling partial reads |
| **CRS** | Coordinate Reference System — defines how geographic coordinates map to positions on Earth |
| **Embedding** | A dense vector representation of an image chip produced by a neural network (e.g., Clay) |
| **Evidence bundle** | A packaged set of artifacts (imagery, GeoJSON, measurements, provenance) for a single finding |
| **Finding** | A detected change region with location, score, evidence, and provenance |
| **L2A** | Level-2A — atmospherically corrected surface reflectance product |
| **NBR** | Normalized Burn Ratio — (NIR - SWIR2) / (NIR + SWIR2), sensitive to burn scars |
| **NDMI** | Normalized Difference Moisture Index — (NIR - SWIR1) / (NIR + SWIR1), sensitive to moisture |
| **NDVI** | Normalized Difference Vegetation Index — (NIR - Red) / (NIR + Red), sensitive to vegetation health |
| **Provenance** | Full record of source scenes, bands, processing config, model version, and software version for a finding |
| **SCL** | Scene Classification Layer — Sentinel-2 quality band classifying pixels as cloud, shadow, snow, etc. |
| **STAC** | Spatiotemporal Asset Catalog — standard for describing geospatial assets and metadata |
| **STAC Item** | A single STAC record representing one scene/product with geometry, datetime, assets, and properties |
| **Abstention** | The system's refusal to produce a finding when inputs are unreliable (clouds, poor alignment, insufficient valid pixels) |
