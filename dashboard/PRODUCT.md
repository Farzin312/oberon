# Product

## Register

product

## Users

Analysts, land stewards, and GIS technicians responsible for monitoring a
defined portfolio of land areas over time: forestry, conservation, agriculture,
infrastructure, water bodies, mining, and bare-ground sites. They sit down for a
focused session to answer one question — *"did this specific area change
between two dates, and can I trust the answer enough to act on it or report it?"*

They are methodical, often work under data-sovereignty constraints (government,
NGO, research), and have been burned by two extremes: raw Copernicus data
(accurate but laborious) and closed SaaS dashboards (easy but opaque). They
read methodology. They want to see the scenes, the bands, the cloud, the model.
Provenance is not a nicety for them; it is the deliverable.

## Product Purpose

Oberon is a deterministic, auditable, self-hostable Earth-observation change
engine. It turns free Sentinel-2 imagery into ranked, evidence-backed change
findings for any AOI polygon over a before/after window.

- **Inputs:** AOI polygon + before/after date windows + max cloud cover + signal/analysis choice.
- **Signals (the UI must show these, not hide behind "vegetation"):**
  - NDVI — vegetation loss/gain (primary, default)
  - NBR — burn severity
  - NDMI — moisture change
  - Clay v1.5 — optional AI embeddings (general-purpose spectral features; must prove itself against the baseline)
- **Outputs:** ranked findings (GeoJSON), before/after imagery, spectral
  evidence, and a full provenance bundle (scene IDs, bands, processing config,
  model + software version, artifact paths).

It fills the gap between raw Copernicus (manual, labor-intensive) and closed
proprietary SaaS (opaque, expensive): deterministic, auditable, self-hostable
change detection on public satellite data. Success = a user can defend a finding
to a stakeholder without taking Oberon's word for it.

## Brand Personality

**Precise. Auditable. Sovereign.**

Calm-technical, never flashy. The interface reads like a trusted instrument, not
a marketing dashboard. It is confident enough to say "I don't know" (abstention)
and transparent enough to show exactly why. It never implies dependence on a
vendor cloud — sovereignty is the point.

## Anti-references

- **Opaque "AI insights" dashboards** that present a confidence score with no
  method, no scenes, no bands. (The exact thing Oberon exists to replace.)
- **Closed/consumer mapping apps** with gratuitous motion, drenched gradients,
  and decorative glassmorphism that buries data.
- **Raw embedding distance presented as a probability.** Never present Clay
  feature distance as confidence without calibration.
- **SaaS that gates you from your own data.** The dashboard must never imply a
  phone-home dependency.

## Design Principles

1. **Show your work.** Provenance is first-class UI, not a log line. Every
   finding links to its scenes, bands, dates, cloud, and model/software version.
2. **Abstain honestly.** Weak inputs (cloud over threshold, alignment failure,
   too few valid pixels) produce an explicit abstention, never a fabricated
   result. The UI treats abstention as a legitimate, well-designed state.
3. **Baseline before AI.** A deterministic spectral baseline is always visible
   alongside any AI result. AI never gets the headline by default — it earns it.
4. **Land change, not just vegetation.** NDVI/NBR/NDMI/AI are a visible signal
   vocabulary. Vegetation is one lens, not the whole product. The signal in use
   is always labeled and color-coded.
5. **Sovereign by default.** Every affordance assumes self-hosting: no telemetry
   nags, no "upgrade" gates, evidence bundles you can export and own.

## Accessibility & Inclusion

- Target **WCAG 2.2 AA**. Body text ≥4.5:1 against surfaces; the muted-gray text
  in the current dark theme is a known risk to verify.
- **Color-blind-safe signal encoding:** NDVI / NBR / NDMI / AI must be
  distinguishable without relying on red-vs-green alone (pair hue with icon +
  label + pattern).
- **Reduced motion** respected on every transition (the slide/chevron animation
  included).
- Long analytical sessions: dark theme tuned to avoid harsh contrast spikes;
  no auto-playing motion.
