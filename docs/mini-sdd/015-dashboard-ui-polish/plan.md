# Plan

**Parent**: [README.md](README.md)

## Verified Facts

- Dashboard files are plain static assets served by `control-plane/src/routes/dashboard.rs`.
- There is no frontend build pipeline or package manager in the dashboard.
- Bounds has no `dashboard` subsystem; project-level `bounds validate --quick` is still the applicable gate.
- `docs/TASK_CONTRACT.md` defines only `vegetation_disturbance`; burn severity is explicitly future scope.

## UX Direction

The dashboard should feel like an operations console used by land managers, analysts, and compliance users:

- Clear next action on first open.
- Portfolio list is compact and scannable.
- The map remains visible and primary.
- Run history is a status table, not a decorative drawer.
- Reviews and artifacts are available in the finding detail panel.

## Execution

1. Add static regression tests for design-system constraints.
2. Replace the decorative shell with a neutral operational layout.
3. Remove inline runtime styles from JS-generated UI.
4. Hide default Leaflet attribution behind an info toggle and restyle the basemap menu.
5. Reject unsupported control-plane portfolio tasks.
6. Update docs and mini-SDD index.
7. Run static tests, project gates, Rust tests, and browser smoke verification.

## Risk Register

| Risk | Mitigation |
|---|---|
| CSS-only polish misses runtime templates | Test/search `app.js` for inline styles and old classes |
| Stack rewrite delays the product | Keep static assets; no new dependencies |
| Dark mode remains low contrast | Use neutral surfaces, explicit semantic color tokens, and flatter buttons |
| UI offers tasks the engine does not support | Single task allowlist in UI and control-plane route |
