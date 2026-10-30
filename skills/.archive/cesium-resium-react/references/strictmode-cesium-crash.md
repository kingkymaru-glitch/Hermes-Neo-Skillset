# StrictMode + Cesium/Resium crash pack (G28, G29)

Two real failures from a R-Tessera rebuild (Vite + React 19 + Cesium 1.143 +
Resium), both reproduced and fixed in-browser.

## G28 — React StrictMode double-mount tears down Cesium → `DeveloperError: This object was destroyed, i.e., destroy() was called.`

### Symptom
App either whitescreens with a Cesium `DeveloperError`, or the `<Viewer>` canvas
shows its own error card ("An error occurred while rendering. Rendering has
stopped. DeveloperError: This object was destroyed…"). Happens in **dev only**
(StrictMode mounts → unmounts → remounts; the first `viewer` instance gets
`destroy()`-ed, but a stale effect closure still touches it).

### Why
Resium's `<Viewer>` is NOT StrictMode-safe. The classic premise is "StrictMode is
just a dev check, harmless" — for Cesium it is NOT. The first mount's
`viewer.imageryLayers.add(...)` / `scene.morphTo*(...)` effects run, then
StrictMode tears the viewer down, then the second mount runs them again — but a
closure from the first pass can fire against the destroyed viewer.

### FIX (preferred): drop StrictMode for Cesium apps
Cesium/Resium are well-known StrictMode-incompatible; the accepted fix is to not
wrap the Cesium tree in `<StrictMode>`. Keep QueryClientProvider etc.

```jsx
// main.jsx — BEFORE (crashes Cesium in dev)
import { StrictMode } from 'react'
createRoot(document.getElementById('root')).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}><App /></QueryClientProvider>
  </StrictMode>,
)
// AFTER
createRoot(document.getElementById('root')).render(
  <QueryClientProvider client={queryClient}><App /></QueryClientProvider>,
)
```
(Remove the now-unused `import { StrictMode }` to keep oxlint clean.)

### FIX (defense-in-depth): guard every bridge effect against a destroyed viewer
Even without StrictMode, a mid-unmount effect can touch a torn-down `viewer`.
Guard with `viewer.isDestroyed?.()` + try/catch on every viewer-touching effect
in the `useCesium` bridge:

```jsx
useEffect(() => {
  if (!viewer || viewer.isDestroyed?.() || !rasterLayer) return
  try {
    const existing = viewer.imageryLayers
    for (let i = existing.length - 1; i >= 0; i--) existing.remove(existing.get(i))
    viewer.imageryLayers.add(rasterLayer)
  } catch (err) {
    console.warn('[base] raster swap skipped (viewer not ready):', err?.message)
  }
}, [viewer, rasterLayer])

useEffect(() => {
  if (!viewer || viewer.isDestroyed?.()) return
  try {
    const mode = scene === '2d' ? SceneMode.SCENE2D : SceneMode.SCENE3D
    if (viewer.scene.mode !== mode) {
      if (mode === SceneMode.SCENE2D) viewer.scene.morphTo2D(0)
      else viewer.scene.morphTo3D(0)   // exactly ONE morph, never both (see base-layer section)
    }
  } catch (err) {
    console.warn('[scene] morph skipped (viewer not ready):', err?.message)
  }
}, [viewer, scene])

useEffect(() => {
  if (!viewer || viewer.isDestroyed?.()) return
  viewerRef.current = viewer
}, [viewer, viewerRef])
```
Verified green (oxlint 0/0, vite build OK, globe renders in-browser).

---

## G29 — A React render ReferenceError whitescreens the whole app because nothing catches it

### Symptom
Blank page, but the console only shows the generic React warning
`An error occurred in the <SomeComponent> component. Consider adding an error
boundary…` — NOT the actual exception. You cannot see *what* threw. If the
throwing component is rendered OUTSIDE the app's `<ErrorBoundary>` (e.g. a sibling
to `<Viewer>` rather than a child), the boundary can't catch it and the app fully
whitescreens.

### Why
React swallows the real error into the generic "error occurred in component"
warning and does not print the stack to console by default. Runtime errors that
happen during render (e.g. referencing a prop you forgot to destructure) are
invisible unless you surface them.

### FIX (temporary diagnostic, revert after): capture + render the real error
Patch `main.jsx` to install `window.onerror` / `unhandledrejection` handlers that
write the exception stack into the `#root` element. Reload, read the actual
`ReferenceError: <name> is not defined` + line number, fix the root cause, then
REVERT this patch.

```jsx
// main.jsx — TEMP diagnostic, REMOVE after fix
window.addEventListener('error', (e) => {
  const el = document.getElementById('root')
  if (el) el.innerHTML = '<pre style="color:#f88;padding:20px;white-space:pre-wrap;font-family:monospace">RUNTIME ERROR:\n' + ((e.error && e.error.stack) || e.message) + '</pre>'
})
window.addEventListener('unhandledrejection', (e) => {
  const el = document.getElementById('root')
  if (el) el.innerHTML = '<pre style="color:#f88;padding:20px;white-space:pre-wrap;font-family:monospace">UNHANDLED PROMISE:\n' + ((e.reason && e.reason.stack) || e.reason) + '</pre>'
})
```
Real-world catch this way: `ReferenceError: showWeather is not defined at
MapControlPanel (MapControlPanel.jsx:30)` — caused by adding the prop to `<MapControlPanel ... />`
in App.jsx but forgetting it in the component's destructured `function
MapControlPanel({ ..., showWeather, setShowWeather })` signature. The fix was
adding the two props to the signature; the patch was then reverted.

### Hardening takeaway
Avoid the root cause: when you pass a new prop into a component call site, ALWAYS
add it to that component's destructured parameter list in the same edit — a single
`patch` per file won't catch the other. Grep the call site vs the signature
(`search_files` for the prop name across the component file) before claiming done.
Also: wrap *every* top-level UI panel (not just the `<Viewer>`) in an error
boundary, or render it as a child of the boundary, so one panel's throw can't
blank the globe.
