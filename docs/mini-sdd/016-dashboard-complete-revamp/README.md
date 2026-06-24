# Mini-SDD 016 — Dashboard Complete Revamp

**Parent**: [../README.md](../README.md)

Revamp the Oberon WebGIS Land Monitoring Console from scratch into a state-of-the-art analytical GIS terminal. This change completely discards the basic grid layout and traditional developer sidebar styling, transitioning to a full-viewport map overlay system with floating glass panels, high-tech cybernetic styling, and brand-new orbital telemetry branding.

- **Branch:** `dashboard-complete-revamp`
- **Status tracking:** see [`tasks.md`](./tasks.md) — checkboxes crossed off one at a time.
- **Strategy / architecture:** see [`plan.md`](./plan.md).

> ⚠️ **Hard rules (breaking any sinks the change):**
> 1. Preserve Axum serving compatibility: All front-end assets must remain flat inside the `dashboard/` directory. No subdirectories are allowed in URL paths due to the Axum path-traversal guard (`file.contains('/')` rejection).
> 2. Zero-build architecture: Keep pure HTML/CSS/JS without npm/webpack compilation to maintain lightweight dev iterations and prevent build debt.
> 3. Zero loss of functionality: Keep all existing endpoints, calibration counters, reviews, and runs intact.

---

## Locked decisions (confirmed)

| # | Decision | Choice | Rationale |
|---|----------|--------|-----------|
| 1 | Visual Layout | Full-screen map + Floating overlays | Maximizes map space; panels float as HUD-style card overlays that feel like a professional telemetry suite. |
| 2 | Branding & Logo | Minimalist telemetry brand mark | Replaces the outdated logo with a newly generated high-tech vector design featuring neon orbital paths. |
| 3 | Component Stack | Flat HTML/CSS/JS | Avoids build pipelines and node_modules while remaining fully compliant with Rust's flat static file router. |
| 4 | Aesthetic Theme | Cyber-Slate Glassmorphism | Uses `backdrop-filter: blur(20px)` and subtle glowing borders (`rgba(255,255,255,0.06)`) to create a high-end, premium feel. |
| 5 | Drawing Flow | Modalless direct draw + Auto-save | Completely removes modal dialogues for drawing shapes. Dragging and resizing shapes auto-saves geometry updates instantly. |

---

## In scope vs. NOT in scope

### ✅ IN SCOPE
- **New Branding/Logo:** Replace the existing `dashboard/logo.jpg` and `dashboard/favicon.jpg` with the newly generated high-tech minimalist orbital telemetry brand mark.
- **Layout Revamp:** Adjusting `#app` structure in `index.html` to a 100% viewport map overlay architecture.
- **Floating HUD Panels:** Designing floating overlays for Portfolio/AOI controls (Left) and Finding Details (Right).
- **Chronological Run Bar:** Replacing the heavy run history table with a compact, linear timeline tracker at the bottom of the viewport.
- **Interactive States:** Enhancing all hover states, active indicators, and input focus highlights with neon cyan accents.
- **Dialog Animations:** Polishing portfolio creation modals with smooth, GPU-accelerated entry/exit transitions.

### ❌ NOT in scope / preserved as-is
- **Rust Backend logic:** The DB layer, pipeline stages, subprocess orchestrator, and endpoints remain untouched.
- **STAC/COG Logic:** Image generation and evidence collection remain as-is.

---

## Risk warnings

- ⚠️ **Leaflet Event Collisions:** Custom overlay panels blocking map clicks.
  *Mitigation:* Apply `pointer-events: none` on wrapper containers, and `pointer-events: auto` explicitly on active control panels. Use `L.DomEvent.stopPropagation` on panel clicks to prevent map panning.
- ⚠️ **Axum Flat Router Constraint:** Vite outputs assets under `/assets/`, which Axum rejects due to path-traversal protection.
  *Mitigation:* Remain on vanilla HTML/CSS/JS without build directories to avoid path slashes.
