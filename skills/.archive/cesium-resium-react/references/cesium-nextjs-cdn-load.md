# Cesium in Next.js (non-Resium) — the octal-escape bundling trap + CDN runtime-load fix

## Context
The rest of this skill covers Cesium via **Resium + Vite** (`vite-plugin-cesium` copies
Cesium static assets and sets `CESIUM_BASE_URL`). That path works because Vite/esbuild
bundle Cesium cleanly. **Next.js (App Router, Webpack/Turbopack/Terser) does NOT** — and
the failure is silent at build time but fatal in the browser. This note covers the
plain-`cesium` (no Resium) integration inside a Next.js app.

Real case (LUNAV ss-rover-cloud, route `/project/[id]/home`): a bird's-eye Cesium globe
was added with:
```ts
import { Viewer, Ion, Cartesian3, Color, ... } from "cesium";
import "cesium/Build/Cesium/Widgets/widgets.css";
```
Build was green. The deployed page threw in the browser and never rendered.

## Symptom
- `next build` SUCCEEDS (EXIT=0) — no build error.
- Browser console: `SyntaxError: The only valid numeric escape in strict mode is '\0'`
  (or `Octal escape sequences are not allowed in template strings`).
- The route's JS chunk fails to parse -> React never hydrates -> the page is blank / "click
  does nothing". A `<a href>` still navigates server-side, but any client JS on that chunk
  is dead.
- The error fires on the chunk that imports Cesium. `grep -c cesium <chunk>` returns dozens
  of hits.

## Root cause
Cesium's npm package embeds its wasm as a **base64 string that contains `\0` bytes**
(emscripten artifact). Inside a **template literal**, `\0` is ILLEGAL in strict-mode ES
modules — but it's legal in a regular string, which is why Vite/esbuild are fine and
Next's minifier is not. Next/Terser preserves the escape when minifying the Cesium bundle,
producing output that fails strict-mode parse.

## Diagnostic (run after `next build`)
This catches the break BEFORE you ship it — `node --check` parses every output chunk:
```bash
cd <next-app>
npx next build > /tmp/b.log 2>&1
BAD=0
for f in .next/static/chunks/*.js; do
  if ! node --check "$f" 2>/tmp/ck.err; then
    if grep -qi "octal\|numeric escape\|SyntaxError" /tmp/ck.err; then
      echo "BROKEN: $f"; BAD=1
    fi
  fi
done
[ "$BAD" = "0" ] && echo "ALL CHUNKS PARSE OK"
```
Only the Cesium chunk fails. This is the decisive proof (don't rely on "build passed").

## FAILED fix (don't waste the turn)
`transpilePackages: ["cesium"]` in `next.config.ts` does NOT fix it. The problem is the
wasm-as-base64 `\0` in a template literal, not transpilation. Confirmed: chunk still failed
`node --check` after adding it.

## WORKING fix — load Cesium from CDN at runtime (do NOT bundle it)
Drop the static `import` entirely. Inject the Cesium script + CSS at runtime and use the
global `window.Cesium`:

```tsx
"use client";
const CESIUM_VERSION = "1.144.0";
const CESIUM_BASE = `https://cdn.jsdelivr.net/npm/cesium@${CESIUM_VERSION}/Build/Cesium`;

function loadCesium(): Promise<any> {
  return new Promise((resolve, reject) => {
    if ((window as any).Cesium) return resolve((window as any).Cesium);
    const link = document.createElement("link");
    link.rel = "stylesheet";
    link.href = `${CESIUM_BASE}/Widgets/widgets.css`;
    document.head.appendChild(link);
    const script = document.createElement("script");
    script.src = `${CESIUM_BASE}/Cesium.js`;
    script.onload = () => resolve((window as any).Cesium);
    script.onerror = () => reject(new Error("Failed to load Cesium from CDN"));
    document.body.appendChild(script);
  });
}

// in the bootstrap useEffect:
const C = await loadCesium();
C.Ion.defaultAccessToken = process.env.NEXT_PUBLIC_CESIUM_ION_TOKEN || "local-dev-no-ion";
const viewer = new C.Viewer(container, { animation: false, timeline: false, /* ... */ });
```
Reference all Cesium types off the `C` global: `C.Cartesian3`, `C.Color`,
`C.GeoJsonDataSource`, `C.Cesium3DTileset`, `C.HeightReference`, etc.

Verify: `next build` (green) + the `node --check` loop above -> ALL CHUNKS PARSE OK.

## Offline-safe variant
If the CDN dependency is unacceptable, copy the prebuilt package into `public/` and load
from there instead of jsDelivr — same runtime-injection principle, no Next minifier
involvement:
```bash
cp -r node_modules/cesium/Build/Cesium public/cesium
# then loadCesium uses `/cesium/Cesium.js` + `/cesium/Widgets/widgets.css`
```
Either way: **never let Next's bundler process the Cesium package.** The wasm/base64
string is the trap.

## Cesium CDN async-load race condition (camera flyTo fires before Cesium is ready)

After switching to the CDN runtime-load pattern, the Viewer creates the globe and
sets a default view, but any camera operation (flyTo, setView) that depends on a
data-load coordinate MAY FIRE BEFORE CESIUM FINISHES LOADING. The coordinate
effect runs in 1 tick (async load → set state), while loadCesium() is a
multi-second CDN fetch. The flyTo sees viewerRef.current === null and skips,
then Cesium finishes loading but the coordinate hasn't changed since → camera
stays at the default (0, 20) view forever (never centers on the pin/site).

Fix — cesiumReady state as a dependency of the camera effect:

```tsx
const [cesiumReady, setCesiumReady] = useState(false);

// Bootstrap effect (runs once on mount):
useEffect(() => {
  (async () => {
    const C = await loadCesium();
    if (destroyed) return;
    const viewer = new C.Viewer(container, { baseLayer: ..., /* ... */ });
    viewerRef.current = viewer;
    setCesiumReady(true);  // signal that the engine is alive
    viewer.camera.setView({ destination: C.Cartesian3.fromDegrees(0, 20, 18000000) });
  })();
}, []);

// Camera effect (fires when center OR cesiumReady changes):
useEffect(() => {
  const viewer = viewerRef.current;
  const C = (window as any).Cesium;
  if (!viewer || !C || !cesiumReady) return;  // wait for CDN
  if (site?.center_lon != null && site?.center_lat != null) {
    viewer.camera.flyTo({
      destination: C.Cartesian3.fromDegrees(site.center_lon, site.center_lat, 8000),
      duration: 1.2,
    });
  }
}, [site?.center_lon, site?.center_lat, cesiumReady]);  // cesiumReady as dep
```

Without cesiumReady: the camera effect fires when site.center populates (fast),
viewer is null, skips, and never re-fires. With it: the effect fires twice
(once when center loads, viewer=null → skip; once when Cesium loads,
cesiumReady flips true AND center is already populated → flyTo runs). Same
pattern as Resium's viewerReady poll (G6) but simpler — no
requestAnimationFrame loop needed because the CDN script signals its own
completion.

## Key takeaways
- Next + plain `cesium` static import = silent build pass, browser parse crash.
- `transpilePackages` does NOT fix the `\0`/octal template-literal issue.
- CDN/static runtime-load of `Cesium.js` + `window.Cesium` sidesteps the bundler entirely.
- Always `node --check` the output chunks when a Next route that imports a heavy native/
  wasm-containing lib renders blank after a green build.
