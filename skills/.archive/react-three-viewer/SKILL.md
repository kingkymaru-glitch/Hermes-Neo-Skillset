---
name: react-three-viewer
description: >-
  Three.js in React for mobile-fullscreen hero pages: a swappable center 3D model
  (procedural default, admin-uploaded GLB) on a full-screen Three.js stage, combined
  with a Cesium globe below the fold, admin-editable JSONB content, and touch-first
  mobile UX. Covers the cursor-vanishes-over-GLB trap, OrbitControls touch config,
  Next.js dynamic import, safe-area insets, and the admin-only model-swap security
  pattern. Trigger on: "3D model hero page", "Three.js + Cesium combo", "mobile 3D
  showcase", "admin swappable center model", "full-screen Three.js landing page",
  "cursor vanishes over GLB", "OrbitControls touch", or any React + Three.js viewer
  task.
---

# React + raw Three.js viewer

Use this for React components that mount a `THREE.WebGLRenderer` directly (NOT
react-three-fiber). The LunaV Studio `Viewer3D.tsx` is the canonical example:
canvas + CSS2D label overlay + OrbitControls, bootstrapped in a `useEffect`.

## When to use
- Editing/debugging a class that creates `new THREE.WebGLRenderer(...)` inside a
  React `useEffect` and appends `renderer.domElement` to a `containerRef`.
- Symptoms: cursor vanishes over the GLB, orbit feels "dead", clicks on markers
  don't register, model won't load.

## Bootstrap pattern (one effect, full cleanup)
- Append `renderer.domElement` AND a `CSS2DRenderer().domElement` to the container.
- `labelRenderer.domElement.style.pointerEvents = "none"` — CRITICAL (see Pitfall 1).
- OrbitControls created with default `cursorStyle` does NOT manage the cursor;
  your own `pointermove` handler owns it. Keep that in mind.
- Cleanup: `cancelAnimationFrame`, `ro.disconnect()`, remove listeners,
  `controls.dispose()`, `renderer.dispose()`, remove both DOM elements.

## PITFALL 1 — CSS2D overlay eats canvas clicks (classic)
If the CSS2D label layer is appended AFTER the canvas and has `pointerEvents`
not set to `none`, it silently sits on top and swallows every click/raycast.
Always set `labelRenderer.domElement.style.pointerEvents = "none"` and
`position:absolute; top:0; left:0`.

## PITFALL 2 — cursor clobber: hover handler vs OrbitControls (the "missing cursor" bug)
A `pointermove` handler that writes `el.style.cursor` on EVERY move will
overwrite OrbitControls' `grabbing` mid-drag, and if it writes `default` over the
model the stage reads as "dead". FIX (full recipe in references/cursor-orbitcontrols-clobber.md):
1. Track drag state: `controls.addEventListener("start", () => orbitDragging = true)`
   and `"end" => false`.
2. In the `pointermove` handler, `if (orbitDragging) return;` so you never stomp
   the `grabbing` cursor.
3. Set the idle canvas cursor to `"grab"` once after controls init (affordance),
   and use `"grab"` (not `"default"`) as the non-hover fallback.
4. `"pointer"` only over markers, `"crosshair"` only in add-marker-armed mode.

## PITFALL 3 — Next.js: dynamic import with ssr:false
Three touches `window`/`document` at module load. In a Next app, wrap the viewer:
`const Viewer3D = dynamic(() => import("@/components/Viewer3D"), { ssr: false });`
Otherwise you get SSR `window is not defined`.

## PITFALL 4 — model fit/centering
After load, `new THREE.Box3().setFromObject(obj)`, recenter `obj.position.sub(center)`,
uniform-scale to a fixed footprint (e.g. 25 units), capture base pos before applying
any persisted transform so live re-applies don't compound.

## PITFALL 5 — removing an object leaves its CSS2D label DOM stuck on screen
A `CSS2DObject(label)` wraps an `HTMLElement` that `CSS2DRenderer` injects into the
DOM. `scene.remove(obj)` + `obj.traverse(...)` disposing geometry/materials removes the
3D mesh but does NOT detach that DOM element — so after deleting the object, its text
label stays frozen on screen. When you tear down any object that owns a CSS2D label,
explicitly detach the element:
```ts
obj.traverse((c) => {
  // ...dispose geometry + material...
  const elc = (c as unknown as { element?: HTMLElement }).element; // CSS2DObject
  if (elc && elc.parentNode) elc.parentNode.removeChild(elc);
});
```
Apply this in EVERY object-removal path, not just cleanup-on-unmount: deleting a single
item from a synced list (e.g. a `proxies`/`markers` array) re-runs the sync and must
remove the orphaned label the same way. In LunaV this was the "deleting a dimension
doesn't remove the value text box immediately" bug — the line/grips vanished but the
label stayed. Also remember CSS2D labels must be `pointer-events:auto` to be clickable
(see Pitfall 1 — only the layer container is `none`).

## Verification (MARU rule: UI "done" = visibly on screen)
- `npx tsc --noEmit` for type safety across the project.
- Do NOT run `npm run build` as the "done" proof for a visual fix — build-green
  does not mean the cursor is visible. Eyeball on a live model first, then commit.
- Reference the specific fix in references/cursor-orbitcontrols-clobber.md.
