# Heavy GLB in-globe crashes Cesium — isolate in an iframe

## Symptom
`RangeError: Failed to set the 'length' property on 'Array': Invalid array length`
in `View.js updateFrustums` / `Scene.js executeCommandsInViewport`, surfaced to the
user as "An error occurred while rendering. Rendering has stopped." Adding a
`model` entity (via `viewer.entities.add({ model: {...} })` or resium
`<ModelGraphics>`) with a non-trivial GLB destabilizes the frustum culler.

## Fix
Render heavy 3D in a sandboxed iframe instead of inside Cesium:
- Keep a lightweight pin/marker on the globe; `onClick` opens a modal whose
  `<iframe sandbox="allow-scripts allow-same-origin allow-pointer-lock" src="...">`
  loads the standalone viewer (Three.js / `<model-viewer>` HTML). Same-origin so
  assets resolve; the iframe is fully decoupled from the Cesium WebGL context, so
  a slow or broken viewer can never crash the globe.
- This also sidesteps the "space in GLB filename" URI gotcha — the viewer loads
  from a normal path, not Cesium's entity URI resolver.

## When in-globe is unavoidable
Only for lightweight GLBs, gate on a verified viewer, wrap in try/catch, and never
track loaded IDs in React state (render-loop bug). Even then, accept crash risk.
