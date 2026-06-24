# Design

Captured from the existing dashboard token system (`style.css`). Authoritative
for on-brand variants. Dark, glass, instrument-like — see [PRODUCT.md](PRODUCT.md).

## Color strategy

**Restrained, with a signal vocabulary.** One neutral dark surface family + a
sky-blue accent for primary actions/selection, plus a distinct, color-blind-safe
color per analysis signal. Decoration stays near zero; color carries state and
signal identity, nothing else.

### Tokens (existing — do not rename without a migration)

```css
/* Surfaces — near-black, layered glass */
--bg-dark: #070a13;
--surface-glass: rgba(18, 25, 38, 0.7);
--surface-solid: #121926;
--surface-hover: rgba(255, 255, 255, 0.05);
--surface-border: rgba(255, 255, 255, 0.1);

/* Accent — primary action, current selection, focus ring only */
--primary: #0ea5e9;
--primary-hover: #38bdf8;
--primary-glow: rgba(14, 165, 233, 0.2);

/* Text ramp — verify 4.5:1 (see a11y note) */
--text: #f8fafc;
--text-muted: #94a3b8;   /* body/secondary — check contrast on surface-glass */
--text-subtle: #64748b;  /* metadata only — never body */

/* State */
--success: #10b981;  --danger: #f43f5e;  --warning: #f59e0b;
```

### Signal palette (NEW — needed for multi-signal surfacing)

Each signal gets a hue **+ an icon + a label**, so it is never hue-only.
Hues are chosen to stay separable for deuteranopia/protanopia (sky vs amber vs
violet vs green are distinguishable; avoid red/green pairings for adjacent data).

| Signal | Role | Color | Icon |
|--------|------|-------|------|
| NDVI   | Vegetation loss/gain (default) | `#34d399` emerald | leaf |
| NBR    | Burn severity                 | `#f59e0b` amber   | flame |
| NDMI   | Moisture change               | `#38bdf8` sky     | droplet |
| Clay AI | General spectral features     | `#a78bfa` violet  | spark |

> Semantic `--success/danger/warning` stay for status (run completed/failed),
> not for signals — keep the two vocabularies separate.

## Typography

One family. **Inter**, system-ui fallback. Fixed rem scale (product UI — no
fluid clamp on headings). Base 14px / 1.5 line-height.

```css
--font-family: "Inter", system-ui, -apple-system, sans-serif;
```

Scale ratio ~1.125–1.2. Body line length capped 65–75ch for prose; data/tables
may run denser.

## Shape & elevation

```css
--radius-lg: 16px;  --radius-md: 12px;  --radius-sm: 8px;
--shadow-soft: 0 8px 32px rgba(0,0,0,0.3);
--shadow-strong: 0 16px 48px rgba(0,0,0,0.6);
--blur-strength: 24px;          /* backdrop-filter on .glass-panel only */
```

Glass (`backdrop-filter`) is used purposefully for map overlays — it lets the
satellite base read through panels. Not as a decorative card treatment.

## Layout

- Map is the canvas (`#map`, full-bleed, z-1). All chrome floats as glass
  overlays with explicit `pointer-events` so the map stays interactive.
- **Z-index scale** (rationalize, never ad-hoc 999): map `1` → bottom-left/right
  badges `~500` → glass panels `800` → top-nav `1000` → drawers/modals `1100+`
  → toast `1200` → tooltip `1300`.
- Floating panels position with insets, not translated fl/grid that fights the
  map. **A panel must not extend past the viewport** (current bottom-sheet corner
  clip is a bug to fix).

## Motion

```css
--transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
```

150–300ms, ease-out, **state-conveying only** (collapse, selection, loading,
reveal). No orchestrated load sequences, no bounce/elastic. Every animation has
a `@media (prefers-reduced-motion: reduce)` fallback (crossfade/instant).

## Components (vocabulary — keep consistent across screens)

`.glass-panel` · `.btn` (+ `-primary/-secondary/-ghost`, sizes) · `.btn-icon` ·
`.input-modern` · `.select-modern` · `.config-section` (collapsible) ·
`.bottom-sheet` (Run History, collapses via `.collapsed`) · `.side-drawer`
(finding detail) · `.modern-dialog` (`<dialog>`) · `.timeline-card` ·
`.status-pill` / `.status-indicator` · `.toast`.

Every interactive component ships **all** states: default, hover, focus, active,
disabled, loading, error.
