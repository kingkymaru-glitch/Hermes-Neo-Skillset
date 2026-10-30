# Module specifier + window export + browser cache failure chain

Session 2026-08-15. Symptom reported by MARU: clicking "sample" in the DTwin
Assets panel produced TWO console errors and the splat never loaded:

```
installHook.js:1 Splat load failed: TypeError: Failed to resolve module specifier 'vendor/gaussian-splats-3d.module.js'
    at loadSplat (main.js:63:30)
    at main.js:105:1
index.html:113 Uncaught TypeError: window.loadSplat is not a function
    at viewBtn.onclick (index.html:113:18)
```

## The chain (all three links must be fixed)

### Link 1 — bare specifier in a dynamic import aborts the whole module
`web/main.js`:
```js
const SPLAT_PACKAGE = 'vendor/gaussian-splats-3d.module.js';  // BARE — wrong
...
const mod = await import(SPLAT_PACKAGE);   // line ~63
```
A bare specifier (no leading `./`) is resolved against the importmap. The
importmap only declared `three` and `three/addons/`:
```html
<script type="importmap">
{ "imports": {
    "three": "./vendor/three/three.module.js",
    "three/addons/": "./vendor/three-addons/"
} }
</script>
```
No key matches `vendor/gaussian-splats-3d.module.js`, so the browser throws
"Failed to resolve module specifier". Because it's a top-level `await import()`
inside a `<script type="module">`, the throw **aborts the entire main.js module**
before the `window.*` exports at the bottom ever run.

Fix: relative URL.
```js
const SPLAT_PACKAGE = './vendor/gaussian-splats-3d.module.js';
```
No importmap entry needed — the relative path resolves against the page at
`/web/`. Verified `curl -o /dev/null -w "%{http_code}" http://localhost:8753/web/vendor/gaussian-splats-3d.module.js` → 200.

### Link 2 — module-scoped functions invisible to inline onclick
Even after the module loads, the Asset panel's inline handlers in `index.html`
run in GLOBAL scope, so a bare `loadSplat(...)` / `setStatus(...)` throws
`loadSplat is not a function` / `setStatus is not a function`. The functions
live inside main.js's IIFE (`(function(){ ... })()`).

Fix (bottom of main.js, before the closing `})();`):
```js
window.loadSplat = loadSplat;
window.setStatus = setStatus;
window.placeholder = placeholder;
window.splatViewer = () => splatViewer;
```
And in `index.html` every inline handler must call `window.loadSplat(...)` /
`window.setStatus(...)`, NOT the bare names. Grep for every bare `loadSplat(` /
`setStatus(` in `index.html` and prefix `window.`.

### Link 3 — browser cache masks the fix ("error persisted" after the code was correct)
The stdlib `SimpleHTTPRequestHandler` sends `Last-Modified` but NO
`Cache-Control`, so the browser serves a stale cached `main.js`/`index.html`.
After fixing links 1+2 on disk, the user still saw the OLD bare specifier and
OLD line numbers in the console.

Diagnostic first — always confirm what the server is ACTUALLY serving before
concluding a fix "didn't work":
```
curl -s http://localhost:8753/web/main.js | grep SPLAT_PACKAGE
curl -s http://localhost:8753/web/index.html | sed -n '113p'
```

Fix in `server.py` Handler — override `end_headers`:
```python
def end_headers(self):
    # Local dev server: never let the browser cache stale JS/CSS/HTML.
    self.send_header("Cache-Control", "no-store, no-cache, must-revalidate")
    super().end_headers()
```
Then restart. Two restart gotchas hit in this session:
- `pkill -f "python3 server.py"` MISSED the old server (its command line was
  `/opt/homebrew/.../Python server.py` with a different argv). Confirm the port
  is free with `lsof -iTCP:8753 -sTCP:LISTEN`; `kill -9 <pid>` the stale PID,
  then relaunch `python3 server.py` (background).
- After relaunch, verify the header actually landed:
  `curl -sI http://localhost:8753/web/main.js | grep -i cache-control`
  → expect `Cache-Control: no-store, no-cache, must-revalidate`.
Finally the user must hard-refresh (Cmd+Shift+R) to drop the browser's in-memory
cache of the old module.

## Why the three fixes looked like "same error" three times
- Fix attempt 1: exposed `window.loadSplat` in main.js → still errored because
  link 1 (bare specifier) aborted main.js before the export ran.
- Fix attempt 2: changed inline handlers to `window.loadSplat` → still errored
  because the served main.js was the cached pre-fix copy (link 3).
- Fix attempt 3 (the real one): relative specifier + window exports + no-store
  header + verified the header landed + kill the stale server + hard refresh.
Lesson: when a JS fix "persists", check SERVED bytes and CACHE headers before
writing more code — the file on disk being correct does not mean the browser
got it.
