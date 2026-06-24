# Mini-SDD 017 — Dashboard UI Hardening

**Parent**: [../README.md](../README.md)

Fix the dashboard revamp regressions that made the portfolio creation flow and
left control panel feel unstable: horizontal modal overflow, crammed setup
fields, ambiguous signal controls, low-visibility transparent logo treatment,
and cut-off sidebar sections.

## Decisions

- Keep the flat `dashboard/` HTML/CSS/JS stack. A framework or build step would
  not fix these layout defects.
- Make portfolio creation a three-step form: identity/signals, analysis window,
  and review/optional AI.
- Keep NDVI/NBR/NDMI as a read-only signal plan in the create flow. Only Clay is
  a user-toggle today.
- Keep the map-first floating shell, but make panels viewport-bounded and remove
  inline component styling.

## Scope

- `dashboard/index.html`
- `dashboard/style.css`
- `dashboard/app.js`
- `tests/test_dashboard_static.py`

## Non-goals

- New backend behavior
- New signal APIs
- New frontend build tooling
