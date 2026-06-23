# Mini-SDD 015 — Dashboard UI Polish

**Parent**: [README.md](../README.md)

Revamp the Rust control-plane dashboard into a restrained land-monitoring operations console.

## Decisions

- Keep the current static HTML/CSS/JS stack. A React rewrite would add build debt without fixing the main problem: poor hierarchy, contrast, and workflow clarity.
- Make the map the primary workspace. Empty states should point users to the next action, not sell the product back to them.
- Use system fonts and local assets only. Remove imported marketing-style font treatment.
- Keep dark mode, but use neutral contrast, flat controls, and a small set of semantic colors.
- Hide technical depth behind workflow: portfolio -> AOI -> run -> review -> artifacts.

## Scope

- `dashboard/index.html`
- `dashboard/style.css`
- `dashboard/app.js`
- Static regression tests for the dashboard shell
- Documentation index updates

## Non-goals

- New frontend framework
- New API behavior
- New icon package
- Pipeline or model changes
