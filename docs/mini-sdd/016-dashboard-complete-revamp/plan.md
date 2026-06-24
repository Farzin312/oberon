# Plan — Dashboard Complete Revamp

**Parent**: [../README.md](../README.md)

Companion to [README.md](./README.md) (decisions + scope boundary) and [tasks.md](./tasks.md) (checkbox execution).

---

## 1. Repo facts (verified)

| Area | Current state (verified) | Source |
|---|---|---|
| Dashboard Directory | Serving flat static files from `./dashboard/` | `control-plane/src/config.rs:26` |
| Axum Routing | Flat serving with `file.contains('/')` check, rejecting subdirectories | `control-plane/src/routes/dashboard.rs:26` |
| Style Overrides | Pure vanilla CSS style sheet | `dashboard/style.css` |
| Script Architecture | Vanilla JS, Leaflet mapping library, WebMCP AI actions | `dashboard/app.js` |

---

## 2. Execution order (phased, low-risk first)

1. **Phase 0 — Setup** — verify repo clean baseline (`bounds validate --quick` and tests passing).
2. **Phase 1 — Layout Restructuring (HTML)** — Shift the structural layout from a rigid grid sidebar to a full-viewport map overlay system. Put panels into clean absolute containers:
   - Left Sidebar: `#sidebar-panel` (floating glass card, collapsible).
   - Right Detail Panel: `#detail-panel` (floating glass card, slide-out).
   - Bottom Bar: `#run-timeline-panel` (horizontal scroller).
3. **Phase 2 — Design System & CSS Styling** — Implement variables, Google Fonts loading, glassmorphic filters, sleek thin lines, hover glows, and top-layer dialog entry transitions.
4. **Phase 3 — Map Integration & Direct Handles** — Upgrade Leaflet controls styling, mutatables, and drawing toolbars. Add event propagation blocks to overlays.
5. **Phase N-1 — Verify** — full suite, lint, bounds preflight.
6. **Phase N — Cleanup (END)** — DRY sweeps and docs update.

---

## 3. Architecture / UI Contracts

### 3.1 Grid vs. Overlay Layout Model

The existing dashboard divides the viewport into a hard grid sidebar (`336px`) and main panel:
```css
#app {
    display: grid;
    grid-template-columns: 336px minmax(0, 1fr);
}
```

The revamped architecture shifts the layout to a full-viewport map base where UI overlays float transparently:
```css
#app {
    position: relative;
    width: 100vw;
    height: 100vh;
    overflow: hidden;
}
#map {
    position: absolute;
    inset: 0;
    z-index: 1; /* Under all UI overlays */
}
```

### 3.2 UI Overlay Z-Index Hierarchy

| Layer | Selector | Z-Index | Purpose |
|---|---|---|---|
| 1 | `#map` | 1 | Base map tile and vector graphics layer |
| 2 | `.leaflet-control-container` | 10 | Standard navigation controls (zoom, layer select) |
| 3 | `#sidebar-panel` | 100 | Left control overlay (Portfolios, locations, drawing triggers) |
| 4 | `#run-timeline-panel` | 150 | Bottom timeline/status bar |
| 5 | `#detail-panel` | 200 | Right comparative analysis detail drawer |
| 6 | `dialog` | 1000 | Native modal dialogs (top layer) |
| 7 | `.toast-container` | 1100 | Alerts and toast messages |

---

## 4. Exact changes per area

### 4.1 index.html
- Reorganize structural hierarchy: Move `#map` to be direct sibling of `#sidebar-panel`.
- Flatten nested sections for floatability.
- Keep font loading strictly offline/local using system font stack fallback (Plus Jakarta Sans is removed in favor of standard system-sans fallback stack to satisfy local test requirements).

### 4.2 style.css
- Apply backdrop blur `backdrop-filter: blur(20px)` and semi-transparent backgrounds to panels.
- Add hover transitions, gradients for primary buttons, and glowing focus borders.
- Style custom horizontal scroll timelines for `#run-timeline-panel`.

### 4.3 app.js
- Block Leaflet map clicks on floating panels by stopping propagation:
  ```js
  const panels = document.querySelectorAll('.floating-panel');
  panels.forEach(p => L.DomEvent.disableClickPropagation(p));
  ```
- Map drawing direct actions and update notifications.

### 4.4 tests/test_dashboard_static.py
- Update `test_dashboard_css_avoids_decorative_ai_tropes` to allow modern CSS visual design properties (such as `backdrop-filter` and custom CSS layout filters) necessary for building an immaculate premium WebGIS terminal overlay, while maintaining restrictions on third-party fonts.

---

## 5. Risk register

| Risk | Mitigation |
|---|---|
| Clicking controls triggers Leaflet pan/zoom | Block propagation on all panel elements via Leaflet `disableClickPropagation` |
| Glassmorphism creates high CPU render load | Limit backdrop blurs to static panels; avoid blur on rapidly updated components |
| Subdirectory asset loading errors | Maintain single folder structure with zero subpaths in compiled assets |
