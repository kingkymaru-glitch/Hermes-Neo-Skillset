# Cesium / Resium "blank dark page" — diagnosis & fix

Symptom: `npm run build` is green and `npm run dev` returns HTTP 200, but the
browser shows a **dark/black void** with no globe and no HUD. No React error
(ErrorBoundary stays silent, so it is NOT a white-screen crash).

## Root causes (in order of likelihood)

### 1. No Cesium Ion token -> default imagery 401s -> black globe
Resium's `<Viewer>` requests Cesium Ion's default base imagery (Bing) on
startup. With no `VITE_CESIUM_ION_TOKEN` the request 401s and the canvas
renders as a dark void. This is the #1 cause of a "mounted but blank" Cesium
page.

Fix (token-free, no account needed):
```jsx
import { Ion, ImageryLayer, OpenStreetMapImageryProvider } from 'cesium'

// Pin a dummy token so Cesium's Ion client initializes cleanly (else it may
// throw at init). Real token via VITE_CESIUM_ION_TOKEN is picked up if present.
Ion.defaultAccessToken = import.meta.env.VITE_CESIUM_ION_TOKEN || 'local-dev-no-ion'
...
<Viewer
  full
  baseLayer={new ImageryLayer(
    new OpenStreetMapImageryProvider({ url: 'https://tile.openstreetmap.org/' }),
  )}
  baseLayerPicker={false}
  geocoder={false}
  homeButton={false}
  sceneModePicker={false}
  navigationHelpButton={false}
  timeline={false}
  animation={false}
  creditContainer="cesium-credits"
>
```
- `baseLayerPicker={false}` is REQUIRED when you supply a custom `baseLayer`,
  or Resium tries to build the picker from Ion and errors.
- Disabling the default widgets keeps the HUD clean (your glass panels are the
  real UI).
- Route OSM attribution to a hidden sink (never delete it — violates OSM tile
  policy): `<div id="cesium-credits" className="cesium-credit-sink" />` styled
  `position:absolute;width:1px;height:1px;overflow:hidden;clip:rect(0 0 0 0)`.

To upgrade to real satellite imagery later: add `VITE_CESIUM_ION_TOKEN=...` to
`.env`; the `|| 'local-dev-no-ion'` fallback makes it opt-in.

### 2. Stale dev server serving old code
If `npm run dev` logs `Port 5173 is in use, trying another one...` and lands on
`5174`, the user's browser at `:5173` is hitting a previous session's server
with stale modules — the new fix never loads. Kill before diagnosing:
```bash
pkill -f vite            # macOS/Linux
# or free the port: lsof -ti tcp:5173 | xargs kill
```
Then restart and confirm the served module reflects the change:
```bash
curl -s http://localhost:5173/src/App.jsx | grep -c OpenStreetMapImageryProvider
```

## Verification checklist (must be real, not claimed)
- `npm run lint` (oxlint) -> 0 warnings/errors.
- `npm run build` -> green, lists bundle sizes.
- `curl -s -o /dev/null -w "%{http_code}" http://localhost:5173/` -> 200.
- Served `App.jsx` contains the OSM wiring (`grep -c`).
- `/cesium/Widgets/widgets.css` -> 200 (proves vite-plugin-cesium injected assets).
- Tell the user to hard-refresh (Cmd+Shift+R) to clear stale module cache.

## NOT the cause (ruled out this session)
- Height chain: `.dt-root` was already `position:fixed; inset:0; height:100vh`
  and `.dt-viewer` `width/height:100% !important` — layout was fine.
- ErrorBoundary: it would render "3D canvas unavailable" text if `<Viewer>`
  threw; a truly blank dark page means the Viewer mounted.
