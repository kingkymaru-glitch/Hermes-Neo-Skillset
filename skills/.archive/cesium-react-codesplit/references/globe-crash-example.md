# Worked case: R-Tessera globe → LunaV Labs

## Setup
R-Tessera (Vite + React 19 + Cesium/Resium) had a "LunaV Labs" button that toggled
`view` state between `globe` and `labs` inside ONE React tree. Labs was lightweight;
globe was Cesium-heavy (~300 kB chunk).

## Symptom
- Labs loaded via `?view=labs` directly → fine (globe never mounted).
- Click "LunaV Labs" from inside the globe → BLANK PAGE.
- Console: `TypeError: t.remove is not a function` at GlobeView chunk; or
  `An error occurred in the <GlobeView> component`.

## Diagnosis
`window.addEventListener('error')` injected BEFORE the click captured the real stack —
the dev-server console was stale and misled. Root cause: Cesium `Viewer.destroy()`
racing with Labs mount in the same commit.

## Fix applied (Fix B — standalone)
Lifted Labs into its own private Vercel repo (`lunav-labs`), pure Vite+React, NO Cesium.
The R-Tessera "LunaV Labs" button became a plain `<a href>` to the new site. Crash gone
structurally because the two apps never share a React tree.

## Lagged-unmount variant (Fix A) — for when you must keep SPA switch
```
const [globeAlive, setGlobeAlive] = useState(initial === 'globe')
const openLabs = () => { setView('labs'); setTimeout(() => setGlobeAlive(false), 0) }
const closeLabs = () => { setGlobeAlive(true); setView('globe') }
```
This was written and built clean but NOT runtime-verified before the pivot to Fix B.

## Prop-destructuring trap (hit twice during extraction)
Moving globe code into `GlobeView.jsx` left these undefined until passed through:
`onOpenLabs`, `setProjectsError`, `setScene`. Each threw `X is not defined` at render.
Rule: after extracting, `grep` GlobeView for `set*`/`on*` and ensure each is in BOTH the
function signature destructuring AND the parent's JSX props.

## Static-site verification gotcha (Vercel)
When `lunav-labs` became a pure static `index.html` (no build), the build-reminder
heuristic suggested `npm run build` — which would FAIL (no entry, Vite removed).
Correct verification for a static site:
  - `vercel.json`: `{ "version":2, "buildCommand": null, "outputDirectory": ".", "framework": null }`
  - Verify by serving locally: `python3 -m http.server 4195` then
    `curl -s localhost:4195/index.html | grep -c 'id="globe"|three.min.js|...'`
    and check HTTP 200 + byte size. NOT by running the framework build.
  - Browser tool BLOCKS `file://` URLs — serve over http to verify visually.
