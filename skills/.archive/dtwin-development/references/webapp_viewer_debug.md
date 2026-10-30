# DTwin Webapp / Viewer Debugging Playbook

Recurring failure modes for the `web/` twin viewer at `~/DTwin` and the fix that worked. Verify with real checks (curl, headless where safe) — do NOT assume.

## 1. "Run Pipeline does nothing" / module never executes
**Symptom:** click Run, no handler; or `#p-log` stays at static HTML default; `runBtn.onclick` is null.
**Root causes seen:**
- **Missing vendored three.js addon.** The viewer imports `three/addons/...` (e.g. `GLTFLoader.js` imports `three-addons/utils/BufferGeometryUtils.js`). If that file is absent, the ENTIRE `main.js` module graph fails to load → the IIFE that binds Run never runs. Fix: download the matching three.js version's file from `https://unpkg.com/three@<REV>/examples/jsm/...` into `web/vendor/three-addons/...`. Check the installed revision in `web/vendor/three/three.module.js` (`REVISION`) and match it.
- **WebGL init at top level throwing.** `new THREE.WebGLRenderer(...)` at module top-level aborts the whole script before the pipeline IIFE binds. Make viewer init non-fatal (try/catch, set `VIEWER_OK=false`, guard `renderer` everywhere) so the pipeline panel ALWAYS binds regardless of viewer state.
- **Stale JS cache.** Server sends `Cache-Control: no-store`; if the browser still shows old behavior, hard-refresh (Cmd+Shift+R).
**Verify:** `curl -s -o /dev/null -w "%{http_code}" http://localhost:8753/web/vendor/three-addons/utils/BufferGeometryUtils.js` → must be 200 (was 404).

## 2. `GLB load failed: SyntaxError: Unexpected non-whitespace character after JSON`
**Symptom:** `GLTFLoader.parse` → `JSON.parse` fails at position ~1011.
**Root cause:** the `.glb` JSON chunk is space-padded per spec (0x20) but was generated with a NULL byte (0x00) padding, OR its declared JSON length is wrong. GLTFLoader does strict `JSON.parse`. This is a GENERATOR bug (in `tools/ply_to_glb.py` or the splat_to_mesh tool), not a viewer bug — it affects every produced GLB.
**Check:** `python3 -c "import struct;d=open(p,'rb').read();import json;off=12;ln=struct.unpack('<I',d[off+8:off+12])[0];j=d[off+12:off+12+ln];print(repr(j[-4:]))"` — last bytes must be space-padded, not `\x00`.
**Fix:** regenerate from the `.ply` using the current (correct, space-padded) `tools/ply_to_glb.py` via the splat venv: `tools/splat-apple/.venv/bin/python tools/ply_to_glb.py <asset>/model.ply <asset>/model.glb`. The script is correct (pads with spaces) — only old on-disk GLBs are bad.

## 3. `ffmpeg: command not found` inside the running pipeline
**Symptom:** Run starts (handler fires, "extracting frames") but dies at ffmpeg.
**Root cause:** the launchd daemon (`~/Library/LaunchAgents/com.dtwin.server.plist`) does NOT inherit the interactive shell PATH, so it can't find Homebrew's `ffmpeg` at `/opt/homebrew/bin`.
**Fix (two layers):**
- In `tools/pipeline.sh`: `export PATH="/opt/homebrew/bin:/opt/homebrew/sbin:/usr/local/bin:/usr/bin:/bin:$PATH"` near the top.
- In the plist: add `<key>EnvironmentVariables</key><dict><key>PATH</key><string>/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/opt/homebrew/sbin</string></dict>`.
- Reload daemon: `launchctl unload ~/Library/LaunchAgents/com.dtwin.server.plist; launchctl load ~/Library/LaunchAgents/com.dtwin.server.plist`.

## 4. Stale demo auto-loads on every page / can't be removed
**Symptom:** starting a new project, an old `.glb` force-previews; no delete control.
**Root cause:** startup IIFE fetched `/api/assets`, took `assets[0]`, force-previewed it. The DELETE endpoint only removed `model.ply`, leaving the asset list stuck.
**Fix:** remove the startup auto-load (page starts neutral); make `DELETE /api/assets/<name>` `shutil.rmtree` the whole folder; add a Delete button per asset row (with confirm). After this, a fresh project starts clean and any asset is removable via the UI.

## Verification harness notes
- Server-side: `curl -X POST http://localhost:8753/api/pipeline -H 'Content-Type: application/json' -d '{"video":"<path>","name":"x","frames":300,"iters":2000}'` → `{"started":true}`.
- `/api/assets` lists `web/assets/*` dirs. DELETE removes one.
- **Do NOT spawn headless Chrome on MARU's Mac for testing** — orphaned `--remote-debugging-port` procs block his real Chrome launch (stale `SingletonLock`). Prefer curl + server log inspection. If a real browser probe is unavoidable, kill all Chrome procs + remove `~/Library/Application Support/Google/Chrome/SingletonLock` afterward.

## 5. Trim box-select does nothing / "Delete selected" says "Nothing selected"
**Symptom:** in Trim & Mesh, drag a box over the 3D cloud — no marquee appears, nothing highlights, Delete reports `Nothing selected. Drag a box over the cloud first.`
**Root cause (verified 2026-08-16):** the marquee `mousedown` handler was bound to the **sidebar panel** element:
```js
panel.addEventListener('mousedown', (e) => { if (e.target === canvas) startMarquee(e); });
```
but `#view` (the 3D canvas) is a separate `position:fixed; inset:0; z-index:1` element that is NOT a child of the panel. A drag on the cloud therefore never has `e.target === canvas` bubble to the panel, so `startMarquee` never fires. The backend (`/api/trim`) is fine — only the UI listener is wired to the wrong element.
**Secondary conflict:** even if the listener fired, OrbitControls also listens on the canvas, so the drag would orbit the camera and scramble the screen→world mapping used to pick points.
**Fix:**
- Bind selection to the canvas itself: `canvas.addEventListener('mousedown', startMarquee);` (canvas is `position:fixed`, so `e.clientX/Y` map directly — keep the marquee `position:fixed`).
- In `startMarquee`, bail unless `e.target === canvas`, and `controls.enabled = false` while dragging; restore `controls.enabled = true` in `endMarquee`.
- In `endMarquee`, only call `pointsInBox` if the drag exceeded a few px (debounce clicks). `pointsInBox` projects each point through `ptsObj.matrixWorld` and tests screen bounds — runs on the sampled cloud from `/api/points` (`serverIdx` maps sampled index → real gaussian index for `/api/trim`).

## 6. Mesh export always uses the wrong cloud (no original/trimmed choice)
**Symptom:** after trimming, the exported `.glb` reflects the ORIGINAL capture (or vice-versa) with no way to choose.
**Fix (verified 2026-08-16):** add a source toggle in the Export group and honor it server-side.
- `index.html` Export group: `Original | Trimmed` radios (`#meshSrc`); the `Trimmed` radio is `disabled` until a trimmed cloud exists.
- `deleteSelected` (after a successful `/api/trim`) enables + checks the `Trimmed` radio and updates `#meshSrcHint`.
- `main.js` Mesh button reads `srcWrap.querySelector('input:checked').value` and POSTs `{name, source, ...}` to `/api/mesh`.
- **Backend contract** (`server.py` `/api/mesh`):
  - `data.get("source") == "trimmed"` → `model_trimmed.ply` (400 if missing: `no trimmed cloud for <name> — use Delete selected first`).
  - `== "original"` → `model.ply`.
  - omitted/empty → legacy: `model_trimmed.ply` if present else `model.ply`.
  - `/api/assets` now returns `[{name, has_trimmed: bool}]` (was a flat string list) — the UI gates the `Trimmed` radio on `has_trimmed`.
**Verify:** `curl -s http://localhost:8753/api/assets` → each entry has `has_trimmed`; `curl -X POST /api/mesh -d '{"name":"X","source":"trimmed"}'` returns 200 when `model_trimmed.ply` exists, 400 otherwise.

## 7. Changing `/api/assets` shape breaks asset select → `assets/[object Object]/model.ply`
**Symptom:** clicking an asset row throws `Viewer::addSplatScene -> Could not load file assets/[object Object]/model.ply`.
**Triage clue:** the `.ply` path + `[object Object]` means it's the splat path in `web/index.html` (`loadSplat('assets/'+name+'/model.ply')`), NOT `loadGlb` (which uses `.glb`). Don't go hunting Three.js — it's a front↔back contract mismatch.
**Root cause (regression 2026-08-16):** a backend change made `/api/assets` return `[{name, has_trimmed}]` objects instead of a flat `["CMPK1",...]` string list. The asset-row renderers still iterated each entry as a bare string, so `name` became the whole object → `String(item)` → `[object Object]`. The URL is built by string concatenation, so the object leaks straight into it.
**DTwin DUAL-RENDERER pitfall (the real trap):** asset rows are built in TWO places that MUST stay in sync, or one path keeps serving `[object Object]`:
  - `web/index.html` inline `window.ASSET_ROW = function(item){...}` — the ACTIVE renderer on the deployed page.
  - `web/main.js` `refreshAssets()` forEach loop AND `defaultAssetRow()` — the fallback renderer.
  Fixing only one of them (e.g. only `refreshAssets`) leaves the other broken. This exact regression happened because the §6 mesh-source toggle changed the contract but initially only `main.js` was updated.
**Fix pattern — normalize at EVERY consumer (not just one):**
```js
const name = typeof item === 'string' ? item : (item && item.name) || String(item);
```
Apply it in: `window.ASSET_ROW` (index.html), the `refreshAssets` forEach, and `defaultAssetRow`. Then the click handler's `loadSplat('assets/' + name + '/model.ply')` gets a real string.
**Verify without a browser** (reproduce the normalize against the live endpoint):
```sh
curl -s http://localhost:8753/api/assets | node -e 'let s="";process.stdin.on("data",d=>s+=d).on("end",()=>{for(const it of JSON.parse(s).assets){const n=typeof it==="string"?it:(it&&it.name)||String(it);console.log("assets/"+n+"/model.ply")}})'
```
Must print `assets/CMPK1/model.ply` etc. — never `[object Object]`.
**Regression discipline (cross-cutting):** whenever you change a backend API's JSON shape, grep ALL front-end consumers of that endpoint (every `fetch('/api/...')` call + every inline renderer) and update them in the SAME change. One-place fixes here caused this exact break twice.

## 8. "I can SELECT points but Delete removes nothing / deletes the WRONG ones"
**Symptom (distinct from §5):** in Trim & Mesh you load the cloud, drag a box — the marquee appears and points highlight red (selection WORKS) — you click Delete selected, but the boxed points stay put, OR seemingly-random points vanish, and repeated attempts never clean the cloud. Report from MARU 2026-08-16: "able to select the points, but unable to delete it even repeated attempt select and delete".

**Root cause — TWO coupled bugs (both verified, both fixed):**
- **Bug A — wrong indices (silently deletes the wrong Gaussians).** `/api/points` returns a 50k-point SAMPLE of the real 100k+ splat. Each sampled point carries a hidden `src_idx` mapping it to its true position in the full `.ply`. `tools/trim_splat.py extract` computed `src_idx` but did NOT emit it in the JSON. So `loadPoints` fell back to `serverIdx = [0..n-1]` (sample-local index). `deleteSelected` then sent `serverIdx[i]` → sample-local indices pointing at DIFFERENT Gaussians in the real cloud. Something got deleted, just never what you picked. The backend "succeeded" so there was no error to surface — the classic silent-data bug.
- **Bug B — viewer reloads the unchanged original.** `/api/points` always read `model.ply` (original) while `/api/trim` wrote `model_trimmed.ply`. After every Delete, `loadPoints` re-served the untouched original → the cloud looked identical ("nothing happened"). On top of that, `/api/trim` itself read `model.ply` as its keep-set source, so backend deletions didn't accumulate across multiple trims either (each trim restarted from the original).

**Fix (verified working end-to-end 2026-08-16):**
- `tools/trim_splat.py extract`: add `"src_idx": [int(i) for i in src]` to the emitted JSON payload.
- `server.py /api/points`: resolve working cloud = `model_trimmed.ply` if present ELSE `model.ply`.
- `server.py /api/trim`: same resolution for the source it reads; always writes `model_trimmed.ply`. Now successive box-deletes accumulate on the trimmed cloud and the viewer reflects each delete after the post-trim `loadPoints` refresh.
- `web/main.js loadPoints`: already correct once `src_idx` exists — `serverIdx = j.src_idx || Array.from({length:n},(_,i)=>i);`.

**Verify end-to-end WITHOUT a browser (proves deletes land on the right Gaussians AND accumulate):**
```sh
# 1. src_idx present + correct mapping
curl -s "http://localhost:8753/api/points?name=CMPK1" | python3 -c "import sys,json;d=json.load(sys.stdin);print('count',d['count'],'total',d['total'],'has src_idx','src_idx' in d, 'first', d['src_idx'][:3] if 'src_idx' in d else None)"
# 2. delete 5 sampled points by their REAL src_idx
curl -s -X POST http://localhost:8753/api/trim -H 'Content-Type: application/json' \
  -d '{"name":"CMPK1","indices":[<5 src_idx from step1>]}'
#    -> {"trimmed":"/.../model_trimmed.ply","kept":N-5,"removed":5}
# 3. reload reflects the trim (total dropped by 5; server now reads model_trimmed.ply)
curl -s "http://localhost:8753/api/points?name=CMPK1" | python3 -c "import sys,json;print('total now',json.load(sys.stdin)['total'])"
```
Reset after testing: `rm -f web/assets/<NAME>/model_trimmed.ply` (restores the original 100k+ Gaussians).

**Note:** `extract_points` samples with `np.random.RandomState(0)` (deterministic) → the SAME 50k points appear each reload; `src_idx` is recomputed against whichever cloud is the current working one (original first load, trimmed thereafter). So after a delete, the reloaded sample maps to the trimmed cloud, and the next box builds on the cleaned version.

**Cross-session lesson for trim-style tools:** any "pick a few of many, delete by index" UX MUST carry the sampled→source index map end-to-end (backend emits it, frontend sends it back, backend applies it to the SOURCE cloud), and the preview must re-read the post-edit artifact — not the pristine original — or deletions look like no-ops.
