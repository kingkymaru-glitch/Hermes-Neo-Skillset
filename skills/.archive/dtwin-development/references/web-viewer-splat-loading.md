# DTwin web viewer — splat LOADING failures (3 distinct verified root causes)

This session (2026-08-15) fixed three DIFFERENT reasons the center canvas showed
nothing or threw when loading a Gaussian splat. They are independent — fix the
one matching your symptom. The `web-viewer-blank-debug.md` checklist covers the
*blank-canvas* family (missing canvas, importmap 404, OrbitControls path); this
file covers failures that happen AFTER the module loads and `addSplatScene` is
called. Order of discovery:

1. SharedArrayBuffer / cross-origin isolation  (hard `DataCloneError`)
2. Scene fog hides the splat after camera auto-framing  (silent invisible)
3. Hardcoded startup auto-load of a deleted `sample`  (`Could not load file`)

---

## CAUSE 1 — `DataCloneError: SharedArrayBuffer transfer requires self.crossOriginIsolated`

**Symptom:** Clicking View (or any `loadSplat`) throws in the console:
```
Uncaught (in promise) Error: Viewer::addSplatScene ->
  at Viewer.updateError (gaussian-splats-3d.module.js:13518:33)
```
and the placeholder cylinder stays visible (splat never renders). The inner
cause is `DataCloneError: SharedArrayBuffer transfer requires
self.crossOriginIsolated` — the gaussian-splats-3d sort worker uses
`SharedArrayBuffer` (since `sharedMemoryForWorkers` defaults to `true`), which
the browser only permits on a **cross-origin-isolated** page.

**Fix A (correct, server-level):** the stdlib dev server MUST send two headers on
every response. In `server.py`, override `end_headers()`:
```python
def end_headers(self):
    self.send_header("Cache-Control", "no-store, no-cache, must-revalidate")
    self.send_header("Cross-Origin-Opener-Policy", "same-origin")
    self.send_header("Cross-Origin-Embedder-Policy", "require-corp")
    super().end_headers()
```
Verify with `curl -sI http://localhost:8753/web/index.html | grep -i cross-origin`.

**Fix B (belt-and-suspenders, client-level):** disable shared-memory in the
Viewer ctor so it works even if a header is ever dropped:
```js
const viewer = new mod.Viewer({ renderer, camera, scene,
  gpuAcceleratedSort: true, sharedMemoryForWorkers: false });
```
Both committed (server `e25b7ff`-era + main.js). After this fix the
`addSplatScene` no longer throws DataCloneError — but see causes 2 & 3, which it
then exposed.

---

## CAUSE 2 — `scene.fog` makes splats invisible once the camera auto-frames

**Symptom:** no error, but splat never appears; only the placeholder/background.
Root cause: `const scene = new THREE.Scene(); scene.fog = new THREE.Fog(0x0b0e13,
6, 22);` — the fog far-plane is 22 world units and its color (`0x0b0e13`) is the
SAME as the background/clear color. Each COLMAP reconstruction has its own
coordinate space + scale, so `frameCameraToSplat()` moves the camera out to
~dist (extent*1.4+0.5 ≈ 18–26u for a ~17u capture) to fit it — pushing the whole
splat past the fog far-plane → 100% fogged to the background color = invisible.

**Fix:** delete `scene.fog` entirely. Gaussian splats do not need distance fog.
```js
const scene = new THREE.Scene();
// no scene.fog — fog far-plane + fog==bg color hid splats after camera framing
```

**Companion technique — `frameCameraToSplat(viewer)`:** because every capture
lives in a different COLMAP coordinate space, a fixed camera (the old
`position.set(2.2,1.8,3.2)` / `target.set(0,0.8,0)` tuned for `sample`) shows
other captures as blank or microscopic. Auto-fit after load:
```js
function frameCameraToSplat(viewer) {
  try {
    const box = viewer.splatMesh && viewer.splatMesh.computeBoundingBox
      ? viewer.splatMesh.computeBoundingBox(true) : null;   // -> THREE.Box3
    if (box) {
      const c = new THREE.Vector3(), s = new THREE.Vector3();
      box.getCenter(c); box.getSize(s);
      const maxDim = Math.max(s.x, s.y, s.z) || 1;
      const dist = maxDim * 1.4 + 0.5;
      controls.target.copy(c);
      camera.position.set(c.x + dist*0.6, c.y + dist*0.4, c.z + dist);
      camera.near = Math.max(0.01, dist/100);
      camera.far  = dist*20 + 100;
      camera.updateProjectionMatrix();
    } else { camera.position.set(2.2,1.8,3.2); controls.target.set(0,0.8,0); }
  } catch { camera.position.set(2.2,1.8,3.2); controls.target.set(0,0.8,0); }
}
```
Call it right after `await viewer.addSplatScene(url, ...)` in `loadSplat`.

---

## CAUSE 3 — startup auto-load hardcodes the deleted `sample`

**Symptom:** on every page load (before touching anything) the console throws
```
Uncaught (in promise) Error: Viewer::addSplatScene ->
  Could not load file assets/sample/model.ply
```
even though `sample` was deleted and only `dji_test` exists. Root cause:
`web/main.js` did `const MODEL_URL = 'assets/sample/model.ply'` (hardcoded
default) and `loadSplat(MODEL_URL)` at module top-level — so it 404s on the
missing file on every load. This is the LAST error the user reported after the
COOP/COEP + fog fixes; it looks like "the splat still won't load" but is really a
stale default path.

**Fix:** never hardcode an asset name in the startup loader. Default to null and
let the user pick, OR auto-load the first asset the server actually has:
```js
const DEPLOY   = new URLSearchParams(location.search).get('deploy');
const URL_MODEL = new URLSearchParams(location.search).get('model');
const MODEL_URL = URL_MODEL || (DEPLOY ? 'assets/' + DEPLOY + '/model.ply' : null);

loadPins();
(async () => {
  if (MODEL_URL) { loadSplat(MODEL_URL); return; }
  try {
    const res = await fetch('/api/assets');
    const j = await res.json();
    if (j.assets && j.assets.length) loadSplat('assets/' + j.assets[0] + '/model.ply');
  } catch {}
})();
```
Also: when removing a broken asset, `rm -rf web/assets/<name>` AND confirm
`/api/assets` no longer lists it (`curl -s localhost:8753/api/assets`).

---

## Verification reality (same as the blanket rule)
Headless Chrome on this Mac cannot init WebGL (null context under every flag), so
you CANNOT prove a splat renders from a headless screenshot. Prove instead by:
- served files return 200 + correct COOP/COEP headers + `Cache-Control: no-store`
- `curl /api/assets` returns the expected list
- an on-screen error overlay (window error + unhandledrejection → painted div)
  so the user reads back the real message
Then ask the user to hard-refresh (Cmd+Shift+R) and report the status pill text
("loaded · model.ply" vs "splat load failed") — that is the real diagnostic.
