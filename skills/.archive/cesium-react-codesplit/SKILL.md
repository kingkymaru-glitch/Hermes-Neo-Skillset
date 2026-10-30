---
name: cesium-react-codesplit
description: Lazy Cesium globe in React crashes or needs code-split.
---

# Cesium + React code-split & unmount-race

## When to use
- A React app has a heavy Cesium/Resium globe AND a lightweight page (showcase, labs, docs).
- You want the light page to load fast (not wait on Cesium's ~300 kB chunk).
- Symptom: swapping the globe for another view produces a blank page; console shows `TypeError: t.remove is not a function` in the GlobeView chunk, or `An error occurred in the <GlobeView> component`.

## Root cause
Cesium's `Viewer.destroy()` runs during React's unmount commit. If the globe subtree unmounts in the SAME commit as a sibling mounts (view toggle), React interleaves Cesium's entity/`primitive.remove()` with the new mount and throws. Stack points at the GlobeView chunk, not your code.

## Fix A — lagged unmount (keep SPA switch)
Keep globe mounted one tick after the new view mounts, then tear it down in a separate macrotask so destroy() runs alone:
```
const [globeAlive, setGlobeAlive] = useState(initial === 'globe')
const openLabs = () => { setView('labs'); setTimeout(() => setGlobeAlive(false), 0) }
const closeLabs = () => { setGlobeAlive(true); setView('globe') }
// render: {globeAlive && view==='globe' && <GlobeView .../>}
```

## Fix B — standalone page (most robust)
Make the light page a SEPARATE route/deploy. Navigate with a real link (`<a href>` / router), not a state toggle. The globe app fully unmounts natively before the new page mounts — no shared React commit, crash impossible. Preferred when the light page is its own landing/roadmap.

## Code-split pattern
```
const GlobeView = lazy(() => import('./GlobeView.jsx'))
{showGlobe && <ErrorBoundary><Suspense fallback={<Spinner/>}><GlobeView .../></Suspense></ErrorBoundary>}
```
Extract EVERY cesium/resium import + `<Viewer>` + globe-only chrome into GlobeView.jsx. Keep the light page in the main chunk (no cesium import there).

## Pitfalls
- Every prop GlobeView uses must be BOTH destructured in its signature AND passed from the parent. A missing `setScene`/`setProjectsError`/`onOpenLabs` throws `X is not defined` at render. After extracting, grep GlobeView for `set*` and cross-check props.
- `vite-plugin-cesium` still handles static assets globally even when Cesium is in a lazy chunk — no extra config.
- Don't `React.lazy` something you also `import` at top level — defeats the split.

## references/
See references/globe-crash-example.md for the worked R-Tessera → LunaV Labs case and the static-site verification gotcha.
