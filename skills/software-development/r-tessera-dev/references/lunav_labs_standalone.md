# LunaV Labs — code-split, Cesium-unmount crash, and standalone-page direction

## 1. WHY Labs was slow to open (root cause)
Before the fix, `App.jsx` statically imported `resium` + `cesium` at the top, so
the ENTIRE app (globe engine included) was ONE JS chunk. Build proof:
`dist/assets/index-*.js` = **531 kB** (149 kB gzip). The browser had to
download + parse all 531 kB (mostly Cesium) before React could paint ANYTHING —
including the lightweight Labs page. Opening `?view=labs` still waited on
Cesium's weight. On top of that, the Cesium Viewer also booted its WebGL context
+ workers on every load.

## 2. FIX — code-split the globe (React.lazy)
Extract everything Cesium-related into `src/GlobeView.jsx` and lazy-load it:

```jsx
// App.jsx
import { lazy, Suspense, useMemo, useRef, useState } from 'react'
import LabsPage from './labs/LabsPage.jsx'   // eager — stays in main chunk
import ErrorBoundary from './ErrorBoundary.jsx'

const GlobeView = lazy(() => import('./GlobeView.jsx'))

function GlobeFallback() {
  return (
    <div className="rt-globe-loading">
      <span className="rt-globe-spinner" />
      <p>Loading 3D engine…</p>
    </div>
  )
}
```
Render the globe behind `<ErrorBoundary><Suspense fallback={<GlobeFallback/>}>`.
Labs stays in the tiny main chunk (eager import). Result after split:
`index-*.js` = **228 kB** (72 kB gzip) + `GlobeView-*.js` = **306 kB** (79 kB gzip).
Labs now opens in well under a second; the Cesium chunk streams only when the
globe is actually shown.

**Gotcha when extracting:** `GlobeView` receives many props from `App`. Any prop
used inside GlobeView (e.g. `onOpenLabs`, `setProjectsError`, `setScene`) MUST
be both (a) destructured in GlobeView's signature AND (b) passed from App.
Missing one = `ReferenceError: X is not defined` at render, surfaced only at
runtime (build stays green). Verify by loading `/` in the browser after
splitting — a blank page + console `ReferenceError` means a prop wasn't plumbed.

## 3. CRASH — `TypeError: t.remove is not a function` on globe→Labs
Symptom: clicking "LunaV Labs" from the globe header leaves a BLANK page.
Root cause (captured via `window.addEventListener('error')`): Cesium's
`Viewer.destroy()` runs during the SAME React commit as Labs mounting. React
interleaves the Cesium teardown (which calls `.remove()` on entity collections
already torn down by child components) with the new Labs mount →
`viewer.destroy()` throws `t.remove is not a function`. The `<ErrorBoundary>`
around the globe then blanks the tree.

**FIX — lagged unmount (keep globe alive one tick, then tear down):**
```jsx
const [view, setView] = useState(initialView)
// globeAlive lags view by a macrotask so Cesium.destroy() never races Labs mount
const [globeAlive, setGlobeAlive] = useState(initialView === 'globe')

const openLabs = () => {
  const u = new URL(window.location.href)
  u.searchParams.set('view', 'labs')
  window.history.replaceState({}, '', u)
  setView('labs')                       // Labs mounts immediately…
  setTimeout(() => setGlobeAlive(false), 0)  // …globe unmounts NEXT tick, alone
}
const closeLabs = () => {
  setGlobeAlive(true)                  // remount globe before flipping view
  setView('globe')
}
// render gate:
{globeAlive && view === 'globe' && (<ErrorBoundary><Suspense>…<GlobeView/></Suspense></ErrorBoundary>)}
```
This guarantees Cesium's destroy runs in its OWN commit, with no sibling mount
interleaving → no crash.

## 4. MARU's DIRECTIONAL CALL — Labs as its own clean page (2026-08-12)
During the build MARU said: rather than parking LunaV Labs *under* R-Tessera's
`view` state, make it a **clean standalone landing page**. Rationale he accepted:
- Eliminates the globe↔Labs crash class entirely (separate entry points = no
  shared Cesium lifecycle / no unmount-during-WebGL).
- A standalone page is more presentable/bookmarkable for a customer roadmap at a
  demo; opens instantly with ZERO Cesium.
- The "LunaV Labs" button becomes a plain `<a href>` navigation, not a state toggle.

Two implementation options discussed:
- **A (recommended): separate ROUTE in the same R-Tessera Vercel project**
  (`r-tessera.vercel.app/labs`), one repo, one deploy. Button = real link.
- **B: separate Vercel deploy / subdomain** (`lunavlabs.vercel.app` or
  `labs.r-tessera.vercel.app`) — fully isolated build, zero Cesium, can even be
  static HTML.
At session end MARU said "standby, let's create a clean page for this on Vercel"
→ pending specifics (A vs B, repo name/visibility, whether to reuse the existing
`LabsPage.jsx` + `projects.js` verbatim). The in-tree `view`-based Labs still
works (builds + renders) but the standalone page is the intended end state.

When implementing the standalone page, LIFT the existing
`src/labs/LabsPage.jsx` + `src/labs/projects.js` (data-driven: edit
`projects.js` to add/rename/reorder cards or fill `images: [...]` slots — no JSX
changes). Keep the `LunaV ***` naming prefix and the 3-image-slot + floating
↑/↓ nav layout already verified.
