# Map Overlay Chrome (branding + disclaimer on the globe)

Reusable pattern for putting UI ON the 3D canvas (brand wordmark, data
disclaimer, legend, coordinate readout) WITHOUT stealing pointer events from
the Cesium globe underneath.

## The trap
Rendering a normal absolutely-positioned `<div>` over the `<Viewer>` (even with
`pointer-events: none` on the div itself) is fine — but if ANY ancestor or the
div has `pointer-events: auto`, dragging the globe through that region stops
working. Worse: a full-screen overlay that is itself interactive (e.g. a panel
with buttons) will block the entire map unless scoped to a corner.

## The pattern (verified green in MARU, my-digital-twin)
Wrap ALL non-interactive map chrome in ONE container that is itself
`pointer-events: none`, positioned `absolute; inset: 0` at a z-index ABOVE the
HUD but BELOW every flyout:

```jsx
<div className="map-chrome">              // pointer-events: none; z-index: 11
  <div className="map-brand">…M.A.R.U…</div>     // pointer-events: none inherits
  <p className="map-disclaimer">…simulated data…</p>
</div>
```

CSS:
```css
.map-chrome { position: absolute; inset: 0; z-index: 11; pointer-events: none; }
.map-brand   { position: absolute; top: 14px; left: 50%; transform: translateX(-50%); }
.map-disclaimer { position: absolute; right: 16px; bottom: 14px; max-width: 320px; }
```

Key rules:
- `z-index: 11` sits above the HUD (`.dt-hud` z-10) and below flyouts/drawers
  (z-20+). Pick a value that stays under your interactive surfaces.
- The container is `pointer-events: none`; children inherit it, so the globe
  stays fully draggable everywhere. Only the actual `<Viewer>` receives events.
- Use `backdrop-filter: blur()` + low-alpha bg so chrome reads over any terrain.
- Keep the brand top-CENTER: HUD is top-left, Map Control docks top-right,
  Locate-Me is bottom-left — center-top is the only free band.

## Where interactive overlays live (don't put them in map-chrome)
Buttons that MUST be clickable (Locate-Me, Map Control trigger) are separate
`position: fixed` elements with `pointer-events: auto` and their own z-index
(Locate-Me z-30, MCP trigger z-22). They are NOT children of `.map-chrome`.
If a flyout is open, shift them via a `.shifted` class (e.g. Locate-Me
`left: 458px` when the left drawer is open) so they don't sit under the panel.

## Content placement cheat-sheet (MARU layout)
- top-left    → status HUD (assets count, live/demo badge)
- top-center  → brand wordmark (mission-control chip)
- top-right   → Map Control panel trigger (docked, only when open)
- bottom-left → Locate-Me GPS crosshair (interactive)
- bottom-right→ data disclaimer (fine print)
Never put two interactive things in the same corner.
