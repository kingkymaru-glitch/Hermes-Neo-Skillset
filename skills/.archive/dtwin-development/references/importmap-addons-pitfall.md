# importmap `three/addons/` path mismatch — local 404 that aborts the whole module

This is blank-canvas cause #5 in the DTwin web viewer. It is subtle because the
HTML overlays render fine and three.js loads — only the *addon* import 404s, and
a single failed `import` in an ES module aborts the ENTIRE module (no partial
execution), so the render loop never starts → fully blank canvas.

## The trap
index.html importmap:
```html
<script type="importmap">
{ "imports": {
  "three": "./vendor/three/three.module.js",
  "three/addons/": "./vendor/three-addons/"
} }
</script>
```
main.js:
```js
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
```
The importmap prefix `three/addons/` maps to `./vendor/three-addons/`, so the
import RESOLVES to `./vendor/three-addons/controls/OrbitControls.js`. If you
downloaded OrbitControls.js into `vendor/three-addons/` (no `controls/` subdir),
that path 404s. One failed import = whole module dead = blank. No exception is
thrown you can catch in app code, because the module never finishes evaluating.

## Symptom on a REAL browser (not headless)
A blank canvas, but the HTML overlays (top bar, "Placeholder hologram", status
pill) still show (they are plain HTML). If you add the on-screen error overlay
(see web-viewer-blank-debug.md) you'll see:
`✗ OrbitControls import FAILED: Failed to fetch dynamically imported module:
http://localhost:8753/web/vendor/three-addons/controls/OrbitControls.js`

## Fix
```bash
cd ~/DTwin/web
mkdir -p vendor/three-addons/controls
mv vendor/three-addons/OrbitControls.js vendor/three-addons/controls/OrbitControls.js
# verify the resolved path now serves 200:
curl -s -o /dev/null -w "%{http_code}\n" \
  http://localhost:8753/web/vendor/three-addons/controls/OrbitControls.js
```
RULE: always nest vendored addons under the *exact* subpath the importmap
prefix + the import statement expect. `three/addons/<rest>` →
`vendor/three-addons/<rest>`. Don't flatten the structure.

## How to catch it fast — `web/diag.html` self-diagnostic
Headless screenshots are useless here (no WebGL) and the browser tool can't hit
localhost. So put the diagnostic ON the page: a standalone `diag.html` that runs
each load step and PRINTS the result as colored text. The user opens it in their
real browser and reads back the first red line — no DevTools needed.

Structure (served from the same origin as the app so relative importmap + fetch work):
- importmap identical to index.html (so the SAME module resolution is tested)
- `import * as THREE from 'three'` then print `r<REVISION>`
- `await import('three/addons/controls/OrbitControls.js')` → ✓/✗ (THIS is the one
  that catches the path mismatch)
- `await import('./vendor/gaussian-splats-3d.module.js')` → ✓/✗ (splat viewer)
- real `new THREE.WebGLRenderer({canvas})` + draw a cube + `renderer.render()` →
  proves three.js can actually paint (separates "module broke" from "GL broke")
- `fetch('assets/sample/model.ply', {method:'HEAD'})` → ply reachable?

Wire each step with try/catch that appends a `<div class="ok|bad|warn">` line to
a `#out` container. First red line = the failure. This page is now committed in
the repo (`web/diag.html`) and is the canonical "why is it blank" triage tool.
