# Headless Render Verification (when browser_exec can't reach localhost)

The Browser-Use tool blocks private addresses, but you can still do a real
visual check on localhost apps by rendering them headlessly with Chrome and
reading the screenshot with `vision_analyze`.

## Recipe (macOS, Chrome at /Applications/Google Chrome.app)
```bash
"/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" \
  --headless=new --no-sandbox --use-gl=angle --use-angle=swiftshader \
  --disable-dev-shm-usage --window-size=900,700 \
  --screenshot=/tmp/app.png --virtual-time-budget=7000 \
  "http://localhost:PORT/path?query=..." 2>/dev/null
ls -la /tmp/app.png   # confirm a non-trivial PNG was written
```
- `--use-angle=swiftshader` = software WebGL → three.js / canvas / WebGL sites
  render without a GPU. Required for any WebGL app (not just a nicety).
- `--virtual-time-budget=7000` lets CDN ES-module imports (`importmap` three.js)
  and `fetch()` calls settle before the screenshot fires. 5–10s is the sweet spot.
- For Linux, substitute `google-chrome` or `chromium`. Windows: `chrome.exe`.

## Then read the pixels
```
vision_analyze(image_url="/tmp/app.png",
  question="Describe the scene: is there a 3D viewport, any pins/labels,
            top-bar text, and are there visible error messages?")
```
This is the actual visual sign-off. Report exactly what it shows; never claim a
drag/click interaction you did not perform.

## Pitfall: three.js sprite pins invisible under swiftshader
A pin built as `THREE.Sprite` with a `CanvasTexture` (drawn via 2D canvas)
often does NOT paint under swiftshader headless — the canvas texture never
uploads, so the sprite is invisible. The placeholder/solid geometry still
renders, making the bug easy to miss in a quick glance.
FIX: use a solid 3D mesh pin instead of a sprite:
```js
function makePin() {
  const g = new THREE.Group();
  const m = new THREE.MeshBasicMaterial({ color: 0xffd23f });
  const head = new THREE.Mesh(new THREE.SphereGeometry(0.07, 16, 12), m);
  head.position.y = 0.18;
  const body = new THREE.Mesh(new THREE.ConeGeometry(0.07, 0.18, 16), m);
  body.position.y = 0.05; body.rotation.x = Math.PI;
  g.add(head, body);
  return g;
}
```
Also: raycaster against a pin group must use `intersectObjects(pinGroup.children, true)`
(recursive) and then walk up to `hit.object.parent` for the userData, because
the group's mesh children are what actually get hit.

## Pre-commit static checks (always, cheap)
- `node --check web/main.js` — catch JS syntax errors curl/grep can't.
- `curl -s -o /dev/null -w "%{http_code}" http://localhost:PORT/file` — all
  assets (html/js/json) must return 200.
- JSON data files: `node -e "JSON.parse(fs.readFileSync(p))"`.
