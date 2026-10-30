# Cursor clobber: hover handler vs OrbitControls

## Symptom
User uploads a GLB → it renders in the 3D Digital Twin stage → the mouse cursor
disappears / reads as "dead" over the model. Orbit may still work but there is no
visible grab/drag affordance.

## Root cause (LunaV Studio Viewer3D.tsx)
- The canvas cursor is owned by ONE function: `handleMove` (a `pointermove`
  listener) that overwrites `renderer.domElement.style.cursor` on every move.
- It only wrote `pointer` (over a marker), `crosshair` (add-mode armed), or
  `default` (everything else, including the GLB).
- OrbitControls was created with default `cursorStyle` (never set to `grab`), so
  it never set a cursor. Mid-drag OrbitControls sets `grabbing`, but the very next
  `pointermove` from `handleMove` clobbered it back.
- No `cursor: none` existed anywhere (grep confirmed). The cursor wasn't hidden
  by CSS — it was stomped and the idle stage had no affordance.

## Fix (applied)
After `new OrbitControls(...)`:
```ts
let orbitDragging = false;
controls.addEventListener("start", () => { orbitDragging = true; });
controls.addEventListener("end",   () => { orbitDragging = false; });
renderer.domElement.style.cursor = "grab";   // idle affordance
```
In `handleMove`, right after the `readOnly` guard:
```ts
if (orbitDragging) return;   // don't fight OrbitControls mid-drag
```
And the non-hover fallback:
```ts
el.style.cursor = liveRef.current.addMarkerMode ? "crosshair" : "grab";
```

## Why it works
- `orbitDragging` blocks `handleMove` from touching the cursor while the user is
  actively orbiting, so `grabbing` survives.
- Idle stage shows `grab`, making it obviously orbitable; markers still show
  `pointer`, add-mode still shows `crosshair`.

## Verification
- `npx tsc --noEmit` passed (exit 0) — clean types.
- Visual check on a live GLB is the real proof (per MARU "UI done = visible" rule);
  build-green alone is not sufficient for a cursor fix.
