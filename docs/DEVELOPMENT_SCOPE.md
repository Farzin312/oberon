# Development Scope

**Parent**: [README.md](README.md)

## What Oberon is

An open, self-hostable Earth observation monitoring engine that turns public satellite observations into ranked, evidence-backed change findings for repeated land portfolios.

### Initial user job

"Show me where this land portfolio materially changed between two periods, rank the findings, explain the evidence, and let my team verify or dismiss each result."

### First wired task: Vegetation Disturbance (NDVI loss)

Oberon's engine is a general land-change detector; it ships with **vegetation disturbance (NDVI loss)** as its first wired task. It detects likely change across defined polygons, ranks the most important regions, and provides before/after imagery, spectral evidence (NDVI/NBR/NDMI), change geometry, quality flags, and model provenance. NBR, NDMI, and pixel deltas are computed as supporting evidence on every finding; burn- and moisture-specific tasks are future expansions of the same pipeline.

## What Oberon is NOT

- Not a generic "ask the Earth anything" API
- Not a raw imagery marketplace
- Not a replacement for STAC, COG, or existing EO infrastructure
- Not a defense-ready air-gapped system at MVP
- Not a single-binary Rust purity project
- Not a global, multi-sensor platform (yet)

## Current Scope (Core Engine + Control Plane)

### In scope & Implemented

- Sentinel-2 L2A only (STAC search + cloud-masked median composite reads)
- Core task: vegetation disturbance detection (NDVI loss primary, pixel_delta secondary, NBR as supporting evidence)
- CLI tool (`oberon analyze`) for direct programmatic runs
- Multi-polygon portfolios for repeated site monitoring
- Ephemeral subprocess background job pipeline
- Rust Control Plane (Axum API server, SQLite state machine, jobs registry)
- API key authentication (SHA-256) and audit logging middleware
- Web Dashboard (Vanilla JS + Leaflet) for visual anomaly triage
- Interactive Before/After/Overlay comparative imagery side-by-side reviews
- Human-in-the-loop validation queue (Approve / Reject / Uncertain reviews)
- Model Calibration loop tracking review counts to optimize thresholds
- Explicit abstentions on high cloud/shadow cover and uniform seasonal changes
- Containerized packaging (Docker Compose, non-root runner, dev/GPU stages)

### Out of scope (MVP)

- Multi-sensor support (Sentinel-1, commercial high-resolution imagery)
- Production air-gapped military deployments
- Task-specific fine-tuned model heads (uses uncalibrated encoder distances)
- Managed SaaS cloud billing and tenant resource quotas
- Fully automated loop closure (always keeps humans in the loop for validation)

## Build gates

| Gate | Criteria |
|------|----------|
| Technical benchmark | Walking slice produces one reviewable land-change result from one real polygon |
| External reproducibility | Someone who is not the author can run the workflow and understand the result |
| Baseline vs AI | Deterministic baseline exists; AI compared and justified or removed |
| Pilot readiness | CLI + Docker + evidence bundles work on a customer portfolio |
