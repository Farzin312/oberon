# Development Scope

**Parent**: [README.md](README.md)

## What Oberon is

An open, self-hostable Earth observation monitoring engine that turns public satellite observations into ranked, evidence-backed change findings for repeated land portfolios.

### Initial user job

"Show me where this land portfolio materially changed between two periods, rank the findings, explain the evidence, and let my team verify or dismiss each result."

### First product: Oberon Vegetation Monitor

Monitor vegetation disturbance and restoration across defined polygons. Detect likely loss or recovery, rank the most important regions, and provide before/after imagery, spectral evidence, change geometry, quality flags, and model provenance.

## What Oberon is NOT

- Not a generic "ask the Earth anything" API
- Not a raw imagery marketplace
- Not a replacement for STAC, COG, or existing EO infrastructure
- Not a defense-ready air-gapped system at MVP
- Not a single-binary Rust purity project
- Not a full-stack dashboard (yet)

## MVP scope

### In scope

- Sentinel-2 L2A only
- One task: vegetation disturbance detection
- Single-polygon analysis via CLI
- Batch (offline) processing, no real-time
- Docker Compose packaging
- Deterministic baselines (NDVI, NBR, NDMI, pixel deltas)
- Optional Clay v1.5 AI inference
- Evidence bundles (GeoJSON, imagery, provenance)
- Explicit abstention on poor inputs

### Out of scope (MVP)

- Scheduled monitoring
- Multi-polygon portfolios
- Review queue / approval workflow
- Web dashboard
- User accounts
- Multi-sensor support (Sentinel-1, commercial)
- Rust control plane
- Task-specific trained models
- Managed cloud deployment
- Alerts and notifications

## Build gates

| Gate | Criteria |
|------|----------|
| Technical benchmark | Walking slice produces one reviewable vegetation-change result from one real polygon |
| External reproducibility | Someone who is not the author can run the workflow and understand the result |
| Baseline vs AI | Deterministic baseline exists; AI compared and justified or removed |
| Pilot readiness | CLI + Docker + evidence bundles work on a customer portfolio |
