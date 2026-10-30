---
name: cesium-scrollytelling
description: Cesium globe scroll dolly-out, steady spin, no flicker.
---

# Cesium / Resium Scrollytelling (steady globe, scroll-driven camera)

Use for any web page with a real Cesium (or Resium) 3D globe driven by page scroll:
scroll-linked dolly-out/zoom, rotating globe backdrop, per-project camera travel, globe behind
copy with dim veil. Built and verified on the LunaV Labs project (Vite + React + vite-plugin-cesium,
token-free Esri base layer).

## CORE PITFALL — the per-frame flicker
Symptom: globe judders/flickers while scrolling or spinning.
Cause: TWO camera writers per frame collide — your own `requestAnimationFrame` loop calling
`camera.setView(...)` every frame, AND Cesium's internal render loop also touching the camera.
Out of sync → judder.

CORRECT PATTERN (single writer, GPU-synced):
1. Get the viewer once: `const viewer = viewerRef.current.cesiumElement`.
2. Ensure the clock runs: `viewer.clock.shouldAnimate = true` (else onTick won't fire continuously).
3. Drive EVERY camera move from `viewer.clock.onTick.addEventListener(...)` — exactly ONE
   `camera.setView(...)` per tick. Cesium's clock is synced to the render loop, so the write
   lands when the renderer draws. No collision, no flicker.
4. Scroll only UPDATES a target object (height/pitch/lat). The onTick lerps current→target with
   `approach(cur, tgt, 0.05)` and advances heading by a fixed amount (e.g. `+0.025` deg/tick =
   one rotation ~25s). Do NOT use `flyTo` alongside onTick — it interrupts the spin.
5. Constant axial spin: `heading = (heading + SPIN) % 360` inside onTick. Smooth, scroll-independent.

## SCROLL → DOLLY-OUT (the "1/4 → whole globe" beat)
- progress 0..1 from `scrollY / (scrollHeight - innerHeight)`.
- Smoothstep it: `p = prog*prog*(3-2*prog)`.
- height: `600000 * Math.pow(2.4e6/600000, p)` (600k tight → 2.4M whole globe, exponential).
- pitch: `-55 + p*50` (-55° top-down crop → -5° whole globe).
- Keep lon/lat ~0 (centered) so it's a pure pull-back, not a pan.
- The globe stays in a fixed `position:fixed` panel behind the scroll document; veil dims it
  (e.g. `filter: brightness(0.7) sepia(0.12)` + gradient) so foreground copy stays crisp.

## RESIUM SETUP NOTES
- `<Viewer ref={viewerRef} baseLayer={esriBaseLayer} className="globe-canvas" animation={false}
   timeline={false} baseLayerPicker={false} geocoder={false} homeButton={false}
   sceneModePicker={false} navigationHelpButton={false} fullscreenButton={false} infoBox={false}
   selectionIndicator={false} scene3DOnly={true} />`
- Token-free base: `Ion.defaultAccessToken = import.meta.env.VITE_CESIUM_ION_TOKEN || 'local-dev-no-ion'`
  and use `UrlTemplateImageryProvider` (Esri World_Imagery) so no Ion token is required.
- Bundle: vite-plugin-cesium lazy-loads Cesium from CDN; your app chunk stays ~260kB. Deploy via
  Vercel — the plugin handles static asset serving; set `buildCommand: null` ONLY if you've gone
  fully static (don't, if using Vite build).

## SECOND BLINK ROOT CAUSE — React re-mount on section change
Symptom: globe flashes/re-blinks specifically when scrolling from one page/section to the next
(different from the per-frame judder). Build passes, single onTick writer is correct — yet the
canvas flickers only at section boundaries.
Cause: the parent re-renders on every scroll (e.g. `setProgress`/`setActive` state updates), and
the globe component is NOT memoized. Each re-render re-runs its body and churns the `<Viewer>`,
so Cesium tears down and rebuilds the WebGL canvas → flash. A subtler variant: the section you're
navigating TO was never registered in the navigator's `sectionsRef`, so `goTo(idx)` hits
`undefined` and does nothing (the "last arrow doesn't work" bug).
FIX (decouple globe from React render cycle entirely):
1. `export default memo(GlobeStage)` — mount once, never re-render on parent scroll.
2. Pass scroll progress via a **ref**, not a prop that changes every scroll:
   `const progressRef = useRef(0)` in the parent; update `progressRef.current = p` in a
   throttled (rAF-gated) scroll handler WITHOUT calling setState for the globe. `GlobeStage`
   reads `progressRef.current` inside its onTick. No re-render → no canvas rebuild.
3. Keep `setState` (throttled) only for UI bits like the navigator counter.
4. Register EVERY section (including the final CTA footer) in `sectionsRef` so `goTo(last)` resolves.
   Bug seen: CTA footer had `data-idx="6"` for the active-tracker but no
   `ref={(el)=>(sectionsRef.current[6]=el)}` → `goTo(6)` was a no-op.
VERIFY: after fix, the `<canvas>` node is the SAME DOM element before and after scrolling to the
last section (`sameCanvasNode: true` via identity check). That proves no re-mount = blink gone.

## VERIFY (no Cesium on window in build)
Can't introspect camera from DOM. Verify instead: build passes, zero JS console errors on the
live preview (the onTick callback must not throw), and visually confirm steady rotation on desktop.
If `onTick` throws, the spin silently stops — so a clean console is the practical gate.

## RELATED
Design/theme bar for these pages: skill `elegant-web-design-language` (user-owned — recommend
`hermes curator adopt`). Narrative skeleton (Hero→Opportunity→Return→Capabilities→Insight→Case→CTA)
lives there too.
