# MindAR WebAR — deploy & asset-hosting reference (burned 2026-08-22)

Condensed knowledge bank for shipping MindAR image-target WebAR without CDN failures.

## 1. Why the tutorials break
MindAR tutorials load:
`https://cdn.jsdelivr.net/gh/hiukim/mind-ar@1.2.5/dist/mindar-image-aframe.prod.js`
Two failures:
- The pinned `@1.2.5` `cdn.jsdelivr.net/gh/...` path → **404**.
- Even when present, that `/gh/` path serves `Content-Type: text/plain` with
  `X-Content-Type-Options: nosniff`, so the browser refuses to execute it:
  `Refused to execute … because "X-Content-Type-Options: nosniff" was given and its
  Content-Type is not a script MIME type.`

## 2. Host everything locally (zero CDN)
Download the npm tarball and pull the two JS files out:
```
python3 - <<'PY'
import requests, tarfile, io, os
r=requests.get("https://registry.npmjs.org/mind-ar/-/mind-ar-1.2.5.tgz",timeout=60)
tf=tarfile.open(fileobj=io.BytesIO(r.content))
assets="public/ar/assets"
for n in tf.getnames():
    if n.endswith("mindar-image-aframe.prod.js"):
        tf.extract(n, assets); os.replace(os.path.join(assets,n), os.path.join(assets,"mindar-image-aframe.prod.js"))
    if n.endswith("aframe.min.js"):   # aframe is a separate package; fetch its tarball similarly
        ...
PY
```
- `mindar-image-aframe.prod.js` (1.76MB) is self-contained: A-Frame component + the
  `ImageTargets` compiler are both bundled. In Node `eval` it exposes
  `MINDAR.IMAGE.Compiler` (with `compileTrack`) but NOT `MINDAR.IMAGE.ImageTargets`.
- Reference in HTML: `<script src="assets/aframe.min.js"></script>` then
  `<script src="assets/mindar-image-aframe.prod.js"></script>`.
- qrcodejs, favicon, etc. → also copy into `assets/` and reference locally.

## 3. The `.mind` target file
- MindAR needs a COMPILED `.mind` (gzip'd protobuf of image features), NOT a raw image.
- The official sample is still fetchable (only the `@1.2.5` pinned path is dead):
  - `https://raw.githubusercontent.com/hiukim/mind-ar-js/master/examples/image-tracking/assets/card-example/card.mind` (257KB)
  - `https://raw.githubusercontent.com/hiukim/mind-ar-js/master/examples/image-tracking/assets/card-example/card.png` (61KB)
  - the unversioned `https://cdn.jsdelivr.net/gh/hiukim/mind-ar-js/examples/image-tracking/assets/card-example/card.mind` ALSO works.
- Download both → `assets/card.mind` + `assets/card.png`. Point the default
  `imageTargetSrc` / `TARGET_SRC` at `assets/card.mind`. Use `card.png` as the printed marker.
- The npm tarball does NOT contain any `.mind` (confirmed: `mind files in pkg: []`).

## 4. Compiling a CUSTOM `.mind` (per-project marker)
Public API (REAL BROWSER only):
```js
const buffer = await MINDAR.IMAGE.ImageTargets.compile([dataUrl], {printCompilationProgress:()=>{}});
// buffer = ArrayBuffer → base64 → save as <name>.mind
```
- Does NOT work in Node: `ImageTargets` isn't exported to Node's global, and
  `Compiler.compileTrack` needs canvas/WebGL the Node shim lacks.
- The agent's cloud `browser_exec` tool BLOCKS private/localhost URLs, so it cannot
  reach a local `python3 -m http.server` page. Therefore you cannot run the compile
  against a local server.
- In-session status (2026-08-22): the temp-Vercel + `browser_exec` path was ATTEMPTED
  but the cloud browser tool was unstable for the multi-second WASM compile — both
  `Page.navigate` and `Runtime.evaluate` timed out on the public compiler URL, so a
  custom `.mind` was NOT produced this way. The reliable first-test fallback is
  MindAR's stock `card.mind` (Section 3). For a REAL custom marker, do the compile in a
  browser the user actually owns:
  - Option A: deploy the compiler page publicly (temp Vercel as above), then OPEN that
    URL in MARU's own desktop Safari/Chrome, copy the `#result` base64, decode to a file.
    Do NOT rely on the agent's cloud `browser_exec` for a multi-second WASM job.
  - Option B: use MindAR's hosted compile web tool (hiukim.github.io/mind-ar-js-doc/tools/compile)
    if it's up — upload the marker image, download the `.mind`.
  - Then host the downloaded `.mind` in `assets/` and point `TARGET_SRC` at it.
  - Tear down the temp Vercel project after: `npx vercel rm arcompile-temp --yes`.
- `compiler.html` sketch: load `assets/aframe.min.js` + `assets/mindar-image-aframe.prod.js`,
  draw `assets/marker.png` to a canvas, `toDataURL`, call `ImageTargets.compile`, then
  `out.textContent = 'OK:' + btoa(bin)`.

## 5. Field-test sanity
- Serve locally (`python3 -m http.server 8799` in `public/ar`) and curl every asset 200.
- `grep -rE "cdn.jsdelivr.net/gh/hiukim/mind-ar@1.2.5|webarr-screen" .` → must be empty.
- iOS Safari + Android Chrome: HTTPS mandatory, camera needs a user gesture ("Tap to start").
