# Plan — Dashboard UI Hardening

**Parent**: [README.md](README.md)

## Repo facts

| Area | Verified fact |
|---|---|
| Static serving | Dashboard assets must remain flat in `dashboard/`. |
| Design register | Product UI; map is the frame, restrained color, local fonts. |
| Current defect | Portfolio creation exposed every field in one horizontally overflowing modal. |
| Current defect | AOI status injected duplicate text into a compact badge and clipped the sidebar layout. |

## Execution

1. Baseline `bounds validate --quick` and existing tests.
2. Replace the new portfolio sheet with a three-step wizard while keeping the
   same form fields and backend payload.
3. Move inline signal and generated component styling into CSS classes.
4. Tighten sidebar, logo, dialog, and mobile viewport constraints.
5. Add static regressions for local/offline UI, stepper markup, and no inline
   styling.
6. Run focused static tests, Bounds quick validation, and browser smoke checks.

## Risk register

| Risk | Mitigation |
|---|---|
| Stepper breaks WebMCP form submission | Keep the existing form and submit handler; step buttons are `type="button"`. |
| Signals look selectable | Present them as locked status rows; only Clay remains a checkbox. |
| Modal still overflows on narrow viewports | Cap dialog width and height with `dvw`/`dvh`; hide horizontal overflow. |
