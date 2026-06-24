# Product

## Register

product

## Users
Environmental compliance officers, forestry monitoring analysts, and land managers. They operate under variable lighting conditions (field laptops to operations centers) and need to rapidly verify land canopy changes without cognitive overload.

## Product Purpose
To automate spatial-temporal change detection (NDVI vegetation loss) over target Areas of Interest (AOIs) and collect human-in-the-loop review decisions (Approve/Reject) to calibrate noise-reduction algorithms.

## Brand Personality
* **Telemetry-Native:** Raw, functional GIS dashboard aesthetic inspired by advanced space instrumentation and terminal overlays.
* **Precise:** High informational density, clean layout, and razor-sharp typographic hierarchy.
* **Cyber-Minimalist:** Deep space-dark surfaces with vibrant, focused neon-cyan action colors and highly localized semantic statuses.

## Anti-references
* **AI-Slop Tropes:** Generic SaaS landing page layouts, cream/sand backgrounds, decorative text gradients, float animations.
* **Standard Bootstrap Admin Shells:** Heavy sidebar columns, white boxes, nested cards, and rounded borders.

## Design Principles
1. **The Map is the Frame:** The GIS map is the interface. All panels, lists, and forms float as non-obstructive translucent HUD panels over the coordinates.
2. **Context-Preserved Workflows:** Ensure clicking sidebar elements zooms directly to map features, and vice versa. Maintain layout consistency.
3. **Restrained Color:** Use colored indicators strictly to signify action, change detection intensity, or review status (Cyan for primary actions, Emerald for approved, Rose for rejected, Amber for abstained).
4. **No Inline Styling:** All design tokens must translate directly into global utility classes and functional CSS rules.

## Accessibility & Inclusion
* WCAG AA contrast compliance (minimum 4.5:1 text-to-background contrast).
* Offline/Airgapped rendering: Font choices must use fallback local system fonts without external CDN requests.
* Keyboard-navigable controls and screen-reader accessible headers.
