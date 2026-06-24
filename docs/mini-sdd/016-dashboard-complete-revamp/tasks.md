# Tasks — Dashboard Complete Revamp

**Parent**: [../README.md](../README.md)

Execution checklist. Cross items off (`- [ ]` → `- [x]`) one at a time.
See [`plan.md`](./plan.md) for the *how* and [`README.md`](./README.md) for decisions.

**Legend:** `[FE]` frontend code · `[BE]` backend code · `[QA]` verification · `[DOC]` documentation

---

## Phase 0 — Setup & safety
**Status:** [x]
- [x] [DOC] Create `docs/mini-sdd/016-dashboard-complete-revamp/` directory with `README.md`, `plan.md`, `tasks.md`
- [x] [QA] Baseline: confirm current unit/integration tests compile and run successfully
- [x] [QA] Verify no lint errors on python codebase (`ruff check`)

## Phase 1 — HTML Restructuring ⚠️ gate before Phase 2
**Status:** [x]
- [x] [FE] Modify `dashboard/index.html` structure: move map to top layer sibling, wrap panels in floating container classes
- [x] [FE] Replace standard `nav-add-aoi-btn` button with direct `nav-draw-poly-btn` and `nav-draw-bbox-btn` buttons
- [x] [QA] Verify document structure parses correctly without broken tags

## Phase 2 — CSS Design System & Visuals ⚠️ gate before Phase 3
**Status:** [x]
- [x] [FE] Overhaul variables in `dashboard/style.css` with dark Cyber-Slate theme tokens
- [x] [FE] Style left sidebar panel, right detail drawer, and bottom run history into floating glass cards
- [x] [FE] Add premium entry/exit scale transitions to modals and dialogs with backdrop-filters
- [x] [FE] Customize scrollbars, buttons, state indicators, and alerts with glow and transition styles
- [x] [QA] Verify styles render cleanly in dark theme with readable text contrast (WCAG AA-like metrics)

## Phase 3 — Map Event Propagation & Timeline ⚠️ gate before Phase 4
**Status:** [x]
- [x] [FE] Add event propagation blocks in `dashboard/app.js` to ensure clicking panels doesn't trigger map events
- [x] [FE] Redesign run history panel into a horizontal chronological timeline bar at the viewport bottom
- [x] [QA] Verify that clicking sidebar panels doesn't trigger map zoom or panning

## Phase 4 — Modalless direct draw & editing ⚠️ gate before Phase 5
**Status:** [x]
- [x] [FE] Reconnect navigation draw buttons directly to start drawing polygon/bbox on the map
- [x] [FE] Ensure shapes save automatically on dragend or rename on blur/change without modals or confirm buttons
- [x] [QA] Verify shape creation, vertex dragging, translation, and renaming work seamlessly

## Phase 5 — Verify & QA
**Status:** [x]
- [x] [QA] `ruff check src/ tests/` exits 0; full `pytest tests/ -q` passes
- [x] [QA] `cargo check` and `cargo test` pass successfully in release
- [x] [QA] `bounds validate --quick` and `bounds preflight --ci` report clean boundaries
- [x] [QA] Run a manual browser check of the complete revamp console

## Phase 6 — Cleanup & Doc Sync (END)
**Status:** [x]
- [x] [DOC] Sync permanent indexes with new state (update `docs/mini-sdd/README.md` index table to add `016`)

---

### Progress
- **Created mini-SDD 016 set:** Written README.md, plan.md, tasks.md.
- **Visual mockup concept:** Prepared detailed redesign layout.
- **HTML/CSS/JS Restructured:** Fully implemented the absolute HUD overlay system, chronological horizontal timeline scroller, and GPU-accelerated transitions.
- **Collapsible Floating Panels:** Sidebar and detail panels are now collapsible with clean translation animations and floating toggle triggers.
- **Transparent SVG Branding:** Removed image logo and text, using a transparent vector SVG orbit brand mark instead.
- **Place Search Geocoder:** Implemented debounced, local-cache-backed place search that centers Leaflet map on result click.
- **Missing AOI Status Warning:** Real-time badge and banner warning indicators are active when a selected portfolio has no polygons defined.
- **Impeccable Checked:** Verified that the detector returns 0 warnings, and static tests pass.
