---
name: luna-edge-dev
description: Build/fix Luna-EDGE offline YOLO webapp (~/luna-edge).
---

# Luna-EDGE — offline YOLO detection webapp

Local-first detection engine. Python Flask-SocketIO server on the Mac streams MJPEG
frames over a WebSocket to a `<canvas>` browser page; YOLO (ultralytics yolov8n) runs
server-side and ships raw frames (boxes drawn in-browser as an overlay, NOT baked into
the JPEG). Offline-first: no CDN, no external API. Repo `github.com/kingkymaru-glitch/luna-edge`,
local `~/luna-edge`. Author commits as `git -c user.name=maru -c user.email=kingkymaru@gmail.com`;
fetch+rebase before push, never force-push; exclude `launch.log`.

## Architecture (read before editing)
- `app.py` — Flask server. Bind `0.0.0.0:8000`. Endpoints: `/api/start` (builds config,
  spawns detect engine thread with a `threading.Event` stop signal + 3s read watchdog),
  `/api/stop` (sets event, `join(timeout=3)` — prevents zombie thread on stalled IP-cam),
  `/api/upload` (saves movie to `media/`, returns server path), `/api/cameras`
  (enumerate attached capture devices for auto-fill — see "Cameras & PTZ"),
  `/api/learn/classes`
  (lists `model.names`), `/api/learn/capture` (save img+txt+augment), `/api/learn/train`
  (ultralytics `model.train`, MPS, drops `.pt` into `skills/`).
- `detect/main.py` — engine loop: `safe_read` watchdog, single in-flight `createImageBitmap`
  decode gate (bound lag), paints raw frame only. Boxes drawn client-side.
- `learn/__init__.py` — augmentation (pure numpy+cv2, NO extra dep): 1 captured frame to
  about 16 variants (flipH/flipV/rot90/rot180/rot270/scale08/scale12/bright/contrast/blur/
  noise). Box labels transformed per op. `train()` builds `data.yaml` + runs ultralytics.
- `templates/index.html` — single-file UI. LunaV glass tokens (see below). Sidebar floats
  over the video; canvas draws frames with `object-fit:contain` maths (letterbox) so the
  native aspect ratio is preserved.

## Stop / Start lifecycle — engine teardown & canvas clear (CRITICAL)
The canvas paints the last decoded frame FOREVER via requestAnimationFrame; it only
stops showing a frame when `latestBitmap`/`pendingBytes`/`latestDets` are cleared.
`/api/stop` MUST fully tear down the engine (join the thread) so a subsequent
`/api/start` with a different source cannot overlap a still-alive thread that holds
the camera device open (that overlap = "Start stalls, no frames, old frame frozen").
- `app.py` defines `_teardown_engine(timeout=6)`: sets `_state["stop_event"]`, sets
  `running=False`, `join()`s the engine thread (bounded), then nulls `thread`/`model`.
  `/api/stop` calls it; `/api/start` calls it FIRST if a prior thread is still alive
  (`prev.is_alive()`), BEFORE building a new config — guarantees one engine at a time
  and frees the device for the new source.
- The engine (`detect/main.py`) releases the source itself in its `finally` block
  (joins cap/infer threads + `src.release()`). `app.py` teardown must NOT try to
  release the source again — and there is NO `kill_thread`/`ThreadPoison` helper in
  this repo (an invented import of `detect.lib.thread` crashes the app → 500 on every
  route). A blocked camera `read()` is already bounded by the `safe_read` 3s-timeout
  worker thread, so a bounded `join` is sufficient to reclaim the device; never assume
  a stuck read needs thread-murdering.
- Frontend `clearFeed()` wipes the three frame buffers; it MUST be called from BOTH the
  Stop handler AND the Reset handler, and `paint()` must draw an idle "feed stopped"
  background when no frame is present — otherwise the last frame stays frozen on screen
  after Stop/Reset.

## Launch (canonical one-shot: launch-roverkit.sh)
`bash ~/luna-edge/launch-roverkit.sh` is the ONE command that brings the whole
demo up: starts Luna EDGE (arm64 venv, `:8000`), starts a cloudflared quick
tunnel, auto-patches the Supabase `cctv_cameras.stream_url` (SECURITY DEFINER
RPC via the public anon key — **no manual SQL ever needed**), then opens
R-Tessera. The desktop `ROVER-KIT Demo.app` runs this same script. Prefer it
over the raw `python app.py` start for any demo/launch request.

- **Collision-safe**: if `:8000` is already served by a HEALTHY Luna EDGE, the
  launcher does NOT kill it — it just re-asserts the tunnel URL + DB row and
  exits. Re-running it against an already-up server is harmless; safe to invoke
  blindly.
- Run it backgrounded (`terminal(..., background=true)`); it takes ~40s (server
  ~3s, tunnel ~6s, DB update, then browser opens). Do NOT wrap it in nohup/
  disown — the Hermes runtime rejects those wrappers; use background=true.
- **Readiness** (don't trust the launcher's log alone): `lsof -nP -iTCP:8000
  -sTCP:LISTEN` shows the holder and `curl -s localhost:8000/api/status` returns
  `{"error":null,"running":false}` = server up, engine idle.
- **Tunnel URL rotates every launch** (quick tunnel). That's expected — the
  launcher re-patches Supabase automatically, so the feed URL in R-Tessera stays
  correct. Do not manually paste SQL to fix a rotated URL.
- The engine stays **idle** (`running:false`, `frames:0`) until the Detect
  toggle is hit on R-Tessera or Start is pressed in the UI; `yolov8n` adds ~6s
  before the first frame. `running:false` with `error:null` is HEALTHY, not a
  failure — only `frames` climbing proves delivery once started.
- On this Mac the app is also reachable on the LAN at `http://<LAN-IP>:8000`
  (the log prints `Running on http://172.x.x.x:8000`).

## LunaV glass theme tokens (reuse everywhere)
```
--lv-void:#14171c; --lv-panel:#1b1f26; --lv-panel-raised:#232831; --lv-inset:#0f1216;
--lv-hairline:rgba(150,175,205,0.14); --lv-turq:#2f9bff; --lv-ice:#7db4ff;
--lv-amber:#ffb340; --lv-red:#ff4d4d; --lv-green:#00c878;
--lv-txt1:#e8eef4; --lv-txt2:#8fa1b3; --lv-txt3:#55677a; --lv-glow:0 0 18px rgba(47,155,255,.35)
```
Glass panels: `background:rgba(27,31,38,0.82); backdrop-filter:blur(22px); border:1px solid var(--lv-hairline); border-radius:14px`.
Primary button: `linear-gradient(135deg,var(--lv-turq),#1b6fd0)` + `var(--lv-glow)`.
Bottom railing (fixed, glass) carries the **LunaV-family** bar — NOT the old
"LunaV Labs" wordmark (that wording was replaced on founder mandate). Mirror LunaV
Studio / R-Tessera exactly:
- `position: fixed; left:0; right:0; bottom:0; height:38px; z-index:20;` glass
  `blur(22px)`, `border-top`.
- Left: teal status dot (`var(--lv-turq)` glow) + "LunaV EDGE — 3D Engine Online".
- Right: "LUNAV EDGE — ROVER-R".
- `display:flex; justify-content:space-between; padding:0 24px;` font `0.62rem`,
  `letter-spacing:0.15em; text-transform:uppercase;`.
Keep the SAME wording pattern (teal dot + "3D Engine Online" left / brand "ROVER-R"
right) when editing — it is the family signature.

## CRITICAL UI pattern — AI Learning & AI Detection are TWO SEPARATE windows
Founder explicitly wanted two independent banner buttons, each opening its OWN panel
— NOT one panel with a mode toggle. The original code used `setLearning(on)` that
hid one button and showed the other (and hid AI Detection by default); that is WRONG
now. Correct structure in `templates/index.html`:
- Banner: both `AI Learning` and `AI Detection` buttons always visible, both
  `class="hdr-btn"` (LunaV `.mb-btn` style: `padding:10px 18px; font-size:0.78rem;
  letter-spacing:0.06em`). Brand block = `.brand .name` with `<b>LunaV</b>
  <span>EDGE</span>`, `span` = `var(--lv-turq)`, `font-weight:700`,
  `letter-spacing:0.06em`, `font-size:0.85rem` (mirrors LunaV Studio `.lv-brand-name`).
- Two independent panels inside `#sidebar`: `#aiDetPanel` (Source/Model/Start/Stop/
  Detection log = the "AI Detection" window) and `#learnPanel` (the "AI Learning"
  window). Each toggled by its OWN button via independent functions:
```js
function toggleLearning(force){            // AI Learning window
  learning = (typeof force==='boolean') ? force : !learning
  learnPanel.style.display = learning ? 'block' : 'none'
  canvas.classList.toggle('learning', learning)
  learnBtn.classList.toggle('active', learning)
  if(learning) refreshCls()
}
function toggleDetection(force){           // AI Detection window (independent)
  const open = (typeof force==='boolean') ? force : (aiDetPanel.style.display==='none')
  aiDetPanel.style.display = open ? 'block' : 'none'
  aiDetBtn.classList.toggle('active', open)
}
learnBtn.onclick = () => toggleLearning()
aiDetBtn.onclick = () => toggleDetection()
```
Do NOT reintroduce the `setLearning` mutual-swap or hide either button inline.
Both windows can be open at once; `learning` (draw-box mode) is driven only by
`toggleLearning`.

## Cameras & PTZ (Insta360 Link + auto-detect)
USB webcams (Insta360 Link) present as normal UVC devices on macOS — OpenCV/AVFoundation
index, NOT a motor/IP PTZ. Treat them as a capture-device source and implement a **digital
PTZ** (pan/zoom by cropping the wide 4K feed) rather than fighting proprietary SDKs.

Source plumbing in `detect/sources/base.py`:
- `build_source(kind, uri, **kw)` maps `kind`→class. Register `"insta360"` → `PtzSource`
  (a `WebcamSource` subclass). `build_source("insta360", "1", track=True)` — uri is the
  AVFoundation device index as a string.
- `PtzSource.__init__(uri, track=False, out_w=1280, out_h=720)` opens `cv2.VideoCapture(int(uri) if str(uri).isdigit() else uri)`.
- Crop window stored as fractions of the FULL frame `win=[cx,cy,hw,hh]` (hw/hh are HALF-widths).
- `set_target(cx, cy, frac_w)` receives a centroid in the CURRENT (crop) frame's space and maps
  it to full-frame space via the live window: `fx=(wcx-hw)+cx*(2*hw)`, `fy=(wcy-hh)+cy*(2*hh)`,
  `fw=max(0.2,min(0.5,frac_w*2*max(hw,hh)))`; clamp to `[fw, 1-fw]`. Skipping this crop→full
  mapping makes tracking drift.
- `read()` lerps `win` toward the stored target (`k≈0.15` for glide) then crops+resizes to out_w/out_h.
- Tracking hook in `detect/main.py` infer loop: after inference, if `hasattr(src, "set_target")`,
  pick the max-conf detection, convert its pixel bbox to crop-frame fractions (`cx=((x1+x2)/2)/w`,
  `cy=((y1+y2)/2)/h`, width `max(dx/w, dy/h)`), call `src.set_target(...)`.

UI (`templates/index.html`): add `<option value="insta360">Insta360 Link (PTZ)</option>` to
`#source`; a `#trackWrap` checkbox (Tracking mode) shown only when that option is selected via
`syncSourceUI`; include `track: <checked>` in the `/api/start` payload.

### Auto-detect cameras → fill Source URI
`/api/cameras` probes OpenCV indices 0..7, returns `[{index,name,builtin,ptz,works,w,h}]`.
Frontend `detectCameras()` fetches it, fills a `<datalist>` on the URI input, and auto-fills the
URI with the PTZ camera (see below), switching `#source` to `insta360`/`webcam` accordingly.
Fill ONLY when the URI is empty or still the default S22 placeholder — detect `'192.168'`
anywhere in the value, NOT `indexOf(...)===0` (the placeholder is `http://192.168...` so the
`===0` check silently fails — this exact bug cost a round this session).

#### CRITICAL — OpenCV index order ≠ system_profiler/ffmpeg NAME order (do NOT trust names)
This session the user corrected me directly: the device named "FaceTime HD Camera" in
`system_profiler` / `ffmpeg -list_devices` was at a DIFFERENT OpenCV index than its name
suggested. On this Mac: ffmpeg reported `[0]FaceTime, [1]Insta360`, but OpenCV opened the
Insta360 at **index 0** and FaceTime at index 1. There is NO shared key between the
system_profiler/ffmpeg name lists and OpenCV's indices, so name-by-index mapping produces
wrong labels AND wrong auto-selection.
IDENTIFY THE INSTA360 BY A PHYSICAL CAPABILITY, NOT ITS NAME: it is a 4K UVC camera
(3840×2160), while FaceTime caps at 1080p / non-4K modes. Probe each index by trying to SET
`CAP_PROP_FRAME_WIDTH=3840 / CAP_PROP_FRAME_HEIGHT=2160` and reading it back; if
`w>=3000 and h>=2000` it is the PTZ camera (`ptz=True`). Auto-select `ptz` first, else any
working camera. Label non-PTZ devices generically (`Camera {idx}`) rather than by mismatched
name — trust `ptz`, never the name. Add a "Reset source" button (stop engine + clearFeed() so the frozen frame clears + restore
Source=ipcam/default-URI + untick tracking + re-run `detectCameras()`) so the user can switch
source after auto-fill.
Also: do NOT hardcode `uri='1'` in `syncSourceUI` when `insta360` is selected — it clobbers
the detected index (this session auto-detect picked the right index 0, then `syncSourceUI`
overwrote it to '1' = the Mac cam). Let `detectCameras()` own the URI value.
Suppress OpenCV's noisy "camera failed to initialize" stderr during the probe (redirect
`sys.stderr`/`sys.stdout` to `os.devnull` around each `cv2.VideoCapture`) — non-existent
indices (3..7) print spam per probe.

## AI LEARNING REBUILD — BUILT 2026-08-14 as separate `/learn` tab
The old `#learnPanel` was a TRAINING BENCH bolted onto the shared Detection canvas — effectively
unusable (no pause on video → can't label). Per founder's "separate tab, not the same tab" call, it
was rebuilt as a SEPARATE route+page (`/learn`, `templates/learn.html`) under the SAME LunaV EDGE
app; **Detection (`templates/index.html`) is byte-for-byte untouched.** Full agreed plan:
`references/ai-learning-rebuild.md`. What actually SHIPPED: `references/learn-tab-built.md`.
(The legacy `#learnPanel` still exists in `index.html` as-is; `/learn` is the new recommended path.)

### Shipped architecture (differs from the original design doc)
- **No `/api/learn/frame/freeze` server route was added.** The doc recommended the server hold the
  last decoded frame; that was over-engineering. The frontend freezes purely client-side:
  `canvas.drawImage(video,0,0)` → `canvas.toDataURL()` → POST to the EXISTING `/api/learn/capture`
  (already augments ~16 frames + indexes the class). Simpler, no new backend, and inherently saves
  the SAME frame the box was drawn on — eliminating the old silent frame-mismatch bug.
- **6-step gated flow** (not 8): 1 Name → 2 Pick footage (4 curated clips + upload) → 3 Teach
  (freeze/box/save) → 4 Review (thumbs, green "N box"/red "NO BOX", ✕ delete) → 5 Test (conf
  slider + predict) → 6 Train (disabled until ≥5 boxed frames).
- Top-bar nav: `<a href="/">AI Detection</a>` + `<a href="/learn">AI Learning</a>`; left step-rail
  with lock-gating. LunaV glass tokens reused verbatim.
- **New backend routes (Detection untouched):** `/learn`, `/api/media/list`, `/api/learn/dataset/
  list|classes|image|delete`, `/api/learn/predict` (ultralytics on a dataURL at conf). Reuses
  `/api/learn/capture` + `/api/learn/train` (unchanged).
- UX-felt-vs-invisible call (founder Q1/Q2): **KEEP** freeze/label + dataset review/delete (felt
  wins); **DROP** MPS training-speed work (invisible; small data trains instantly on CPU).

### Why separate page, not shared canvas
- Detection is proven/working; the shared `paint()` loop + `folderMode` flag + `latestBitmap` are
  tightly coupled to the live feed. Any Learning change risks regressing Detection. **Isolation = safety.**
- Learning needs OPPOSITE mechanics from Detection: freeze, scrub, draw-on-a-still, frame-accurate
  capture, edit labels, manage datasets, watch training. Cramming into the same canvas is what
  created the "draw on a moving movie with no pause" wall.
- A separate page (`/learn` route, `templates/learn.html`, own `static/learn.js`) calls the SAME
  backend routes (`/api/upload`, `/api/learn/*`, and `/api/start` with an optional conf + single-frame
  compare mode). One-route backend change + fresh frontend. Lowest risk.
- The "compare my box vs model box" lesson does NOT require same window: the Learning page calls
  `/api/start` on a FROZEN frame and overlays both boxes. Keep them apart.

### Critical UX bug discovered in current Learning capture (SILENT, was mislabeling data)
The draw handler measures the box at MOUSE-UP, but `doSaveLearn()` saves `canvas.toDataURL()` AT CLICK
TIME — a later frame on the live feed. Box and photo are two different pictures → silent mislabeled
training data. **FIX SHAPE:** capture the exact frozen frame (server holds last decoded frame; expose
`POST /api/learn/frame/freeze` returning the JPEG bytes) so the box is saved against the SAME frame it
was drawn on. This is the single highest-value unlock and the make-or-break for labeling video at all.

### Agreed UX shape (intuitive, one-action-per-screen)
- Separate tab [AI Detection] [AI Learning] under same LunaV EDGE app; Detection byte-for-byte unchanged.
- Step banner "Step N of 8 · <plain copy>" + thin progress bar. Steps 1–8 = pixels → draw box →
  model guess → conf slider → what it knows → mistakes → teach (bench) → why edge.
- Center stage: `<video>` + scrubber + big FREEZE + draw canvas (draw only after freeze). Zoom + Undo + pointer events (mouse+touch).
- Right rail (collapsible, hidden while drawing): dataset browser — thumbnail strip, class counts, click-to-edit, delete.
- Bottom: ONE next-action button. Train hidden until final step behind "Advanced" caret (epochs pre-filled).
- Plain-language copy; class autocomplete + near-duplicate warn ("monky"≈"monkey").
- Dataset manager: per-item ✓/✗ feedback, edit+delete per sample, live counts, review gate, safe-train
  check (block if any class <5 samples), thumbnail = ACTUAL captured frame.

### What does NOT solve the user's problem (don't over-invest)
MPS training speed (backend/device flag) is invisible to the user and labeling/training 5–20 images at
50 epochs is already near-instant on CPU. Felt UX lives entirely in front-end labeling + feedback.
Apply MPS only if training *feels* slow later.

## CRITICAL pitfalls (each cost a debugging round this session)
1. **Aspect-ratio distortion is a display bug, not a model bug.** Never `drawImage(bmp,0,0,canvas.w,canvas.h)`
   (stretches). Use contain maths: `scale=min(cw/fw,ch/fh); dx=(cw-dw)/2; dy=(ch-dh)/2;`
   store `containRect={x:dx,y:dy,w:dw,h:dh}`; draw boxes against it. If you label in Learning
   mode on a squashed frame, training boxes are wrong.
2. **Floating launcher/minimize must not sit under the header.** The app bar is `position:relative;
   z-index:30; height:56px` and full-width. A collapsed launcher pill placed at `top:16px`
   renders BEHIND it (invisible + unclickable). Fix: launcher = `position:fixed; top:72px;
   z-index:40`. Drive its visibility in JS (`el.style.display = v?'inline-flex':'none'`), do NOT
   rely on a CSS sibling selector `#a.collapsed ~ #b` — it silently fails if the two elements
   are not DOM siblings (they weren't: launcher was outside `.row`, sidebar inside it).
3. **WebSocket frame = newest only.** Server pushes JPEG bytes + a JSON det array. Client keeps
   `pendingBytes` (overwrite, not queue) and gates decode with one in-flight `createImageBitmap`
   — drops backlog so lag can't grow. Boxes held 500ms (`HOLD_MS`) client-side to stop flicker.
4. **File source = upload, not path.** Browser file picker only yields a `File` object; the
   server reads a real path via `cv2.VideoCapture`. So Source=file shows a `<input type=file>`
   that POSTs to `/api/upload`; the returned server path fills the URI the engine opens. Loopback.
5. **Cesium removed.** It was a render-blocking CDN stub for a future Mavic map; contradicts
   offline-first. Don't re-add CDN deps.
6. **Don't edit `edge-ai-vision` / `local-vision-webapp` / `realtime-cv-webapp`** — those are
   bundled skills, not this project's code. Luna-EDGE conventions live here.
7. **Flask caches templates when `debug=False`, AND a stale SERVER PROCESS serves stale
   `/api/*` routes — the latter bit harder than the former.** Two distinct stale states:
   (a) template cache: a still-running `python app.py` serves the first-rendered HTML after an
   `index.html` edit. (b) **stale process**: after editing `app.py` (routes/handlers), a
   pre-edit `python app.py` is STILL alive holding port 8000 and serves the OLD routes — so even
   though the files on disk are correct, your `/api/stop` returns the old response shape and
   your new `clear_uploads()` never runs. This cost a full debugging round this session.
   ALWAYS after any `app.py`/`index.html` edit: `pkill -9 -f "app.py"` (NOT `-f "luna-edge/app.py"`
   — the launch cmdline is `python app.py`, which the repo-path pattern never matches, so it
   reports "not running" while the old process lives), then confirm the port is free
   (`lsof -i:8000 | grep LISTEN` → expect empty) before restarting. `pgrep -fa "luna-edge/app.py"`
   returning nothing is NOT proof the server is dead. If a launcher/launchd respawns it on kill,
   stop that too. Re-verify against the LIVE served page/route after restart, never the file on disk.
   **Kill-by-PID variant that worked this session (2026-08-14) when only `lsof` output was handy:**
   `PID=$(lsof -nP -iTCP:8000 -sTCP:LISTEN -t); [ -n "$PID" ] && kill $PID; sleep 1;` then confirm
   empty. Restart with `.venv/bin/python app.py > launch.log 2>&1 &` and watch `tail launch.log`
   for "Running on http://".
8. **Run with the venv python — a torch-guard now enforces it.** Bare `python` may not exist on
   PATH (`zsh: command not found: python`). Use `.venv/bin/python app.py` or
   `source .venv/bin/activate && python app.py`; system `python3` (esp. Xcode's bundled
   `/Applications/Xcode.app/.../Python3.framework/.../Python`) has NO torch/ultralytics. As of
   2026-08-14 `app.py` starts with a `try: import torch except: sys.exit(1)` guard — so a wrong
   interpreter now FATAL-exits WITHOUT binding port 8000 (verified). If `:8000` serves but
   `/api/start` is dead, the port-holder is the wrong interpreter: `P=$(lsof -nP -iTCP:8000
   -sTCP:LISTEN -t); lsof -p "$P" | grep -c 'site-packages/torch'` → `>0` = torch loaded = correct.
   Kill + restart on venv.
   CAVEAT (2026-08-14): do NOT judge by `ps -o args=`. It shows the Xcode framework Python path
   even for a CORRECT venv, because this project's venv is built ON Xcode Python 3.9
   (`pyvenv.cfg` `home = /Applications/Xcode.app/.../usr/bin`), so `.venv/bin/python` resolves to
   the SAME framework binary — only `sys.path` differs. Bare Xcode `python` fails `import torch`;
   the venv python imports it fine (same binary, different sys.path). The torch-guard only catches
   a torch-less interpreter, NOT the venv-vs-bare distinction.
9. **Stop/Reset must clear the canvas AND fully tear down the engine.** A frozen last frame
   after Stop, and a "Start stalls, no frames" after switching source, share one root cause:
   the rAF paint loop shows `latestBitmap` forever, and a Stop that only sets a flag (without
   `join()`) lets a new `/api/start` overlap a still-alive thread holding the camera open. Fix
   shape: `_teardown_engine()` `join()`s the engine thread (bounded) and is called by BOTH
   `/api/stop` and the pre-start path in `/api/start`; frontend `clearFeed()` (wipes
   `latestBitmap`/`pendingBytes`/`latestDets`) is called by the Stop AND Reset handlers;
   `paint()` draws an idle "feed stopped" bg when no frame is present. See
   `references/stop-clear-frame-teardown.md`.
10. **Shared hidden `uri` field leaks across source kinds.** Source dropdown uses ONE hidden
   `uri` input for camera/index AND file path. Switching to `file` only *hides* the field — it
   does NOT clear it — so the webcam index `"0"` stays and slips into `FileSource("0")` →
   `RuntimeError('File not opened: 0')`, the engine thread dies, WS never starts, blank feed.
   This session's "local file processing not working" was exactly this. Fix shape: `syncSourceUI()`
   clears `uri` (and a `fileReady=false` flag) when leaving File; Start requires `isFile && uri &&
   fileReady`; `/api/start` rejects a `file` source with missing/non-existent path up front
   (`os.path.isfile`) returning `{"ok":false,"msg":"upload a video file first"}`; `pump()` wraps
   `run()` in `try/except` storing `_state["error"]`, and `/api/status` returns `{running, error}`
   so engine deaths are never silent. See `references/file-source-uri-leak.md`.
11. **`atexit` does NOT fire on signal-kill — bind SIGTERM/SIGINT handlers for any
   cleanup-on-exit.** This session added `clear_uploads()` (app.py) to wipe session uploads in
   `media/` on exit, registered it via `atexit`, and it SURVIVED a SIGTERM kill (uploads stayed
   in `media/`). Fix: `signal.signal(signal.SIGTERM, handler)` + `signal.signal(signal.SIGINT, handler)`
   where `handler(signum, frame)` runs the cleanup then `sys.exit(0)`. `/api/stop` and `atexit`
   are still correct for the normal paths; the signal handlers cover the kill path. Also note the
   **upload lifecycle**: `media/` root = session uploads only; `media/samples/` = curated test
   footage (DJI/WhatsApp) and must NEVER be auto-deleted — `clear_uploads()` skips the `samples/`
   subdir. Verified: `/api/stop` returns `uploads_cleared:N` and `media/` empties while
   `samples/` stays (4 clips); SIGTERM also clears `media/`. See
   `references/upload-clear-and-stale-server.md`.
12. **Learning capture uses a DIFFERENT frame than the drawn box (silent mislabel).** In the legacy
   `#learnPanel`, the box was normalized at mouse-up against the live `latestBitmap`, but `doSaveLearn()`
   POSTed `canvas.toDataURL()` at CLICK time — a later live frame. The saved photo and the box disagreed,
   so training data was silently wrong. **The fix that actually shipped in `/learn` (2026-08-14):**
   freeze is purely client-side — `canvas.drawImage(video,0,0)` on the PAUSED frame, then
   `canvas.toDataURL()` immediately and POST to the existing `/api/learn/capture`. Because draw + freeze
   happen on the same paused frame and the dataURL is captured right then, photo and box always agree.
   (The design doc's `/api/learn/frame/freeze` server route was NOT built — over-engineering.) Always
   verify the saved thumbnail matches the drawn box — never trust a label step that can't show the
   actual captured frame back to the user.

13. **Browser tool (`browser_exec`) is BLOCKED against localhost / private IPs.** Navigating
   `http://localhost:8000` or `127.0.0.1` returns "Blocked: URL targets a private or internal
   address". So you CANNOT click-through the Luna-EDGE UI headlessly here. Verify instead:
   (a) **served-DOM check** — `curl -s http://localhost:8000/learn` and `grep` for marker strings
   (step labels, freeze button id, conf slider id, train-gating fn); (b) **exact frontend-path E2E**
   — replicate the browser's `fetch()` with Python `requests` (same JSON body, base64 dataURL) and
   assert the response; this caught an earlier shell `-c` base64-quoting failure that curl missed.
   Never rely on the browser tool for localhost; tell the user to eyeball the live page themselves.

14. **Engine "works for hours then freezes" = per-read thread churn + concurrent `cap.read()`, not
   the model.** The old `detect/main.py safe_read()` spawned a NEW daemon thread on EVERY frame read;
   on a stalled camera read it returned None after a 3s timeout but left the orphaned thread still
   blocked inside `cap.read()` while the loop immediately issued another `read()` on the SAME
   `cv2.VideoCapture` — two threads racing one camera → undefined hang (the classic 7h-OK-then-stuck).
   Fix (shipped 2026-08-14, commit 831c46c): ONE capture thread does blocking reads into `cap_state`,
   ONE watchdog thread force-releases the source after `STALL_TIMEOUT=10s` of no frames (releasing
   from another thread unblocks a wedged `read()` on FFMPEG/AVFoundation), and the capture thread
   rebuilds+reconnects the source on `None`/drop. PTZ `set_target` hook must read `cap_state["src"]`,
   and the `finally` block releases `cap_state["src"]` (never the stale `src` local). Never reintroduce
   per-read thread spawning. Full before/after + the interpreter red-herring + the launchd-rogue
   diagnostic: `references/engine-stall-thread-churn.md`.

15. **The "instability / lagging / crash" the founder reported was a STALE ZOMBIE SERVER, not tuning or a model bug.** Symptom set: after full restart + double-clicking the desktop launcher, the app "suddenly runs AI on old .mp4s" and then fails to load new files; Stop/Reset/refresh don't help. Root cause: an EARLIER `python app.py` process (e.g. from that morning) was still alive holding :8000, and the old `launch.command` had a port-busy GUARD that REFUSED to start instead of restarting — so double-click just exited and the user kept talking to the stale process with its old in-memory state + old code. Fix shipped (commit 948ea15): `launch.command` now KILLS whatever holds :8000 (`lsof -nP -iTCP:8000 -sTCP:LISTEN -t` → `kill -9`) then starts fresh. This is the hard "dump stuck memory" reset. Hard rule: when Luna-EDGE "feels unstable after working fine," suspect a zombie server FIRST — verify the port-holder is the current code (`curl -s http://localhost:8000/api/status`) and restart via the launcher before touching engine/source code.

16. **Make the app genuinely offline-with-no-trace: kill CDN fonts + disable library telemetry.** Verified external egress had TWO sources (app logic itself was already local-only):
   - (A) Google Fonts CDN: both `templates/index.html` and `templates/learn.html` `<link>`ed `fonts.googleapis.com`/`fonts.gstatic.com`. Fix: download the woff2 via `curl -A "Mozilla/5.0 ..."` from the css2 endpoint, self-host under `static/fonts/` (`fonts.css` + 5 woff2: Geist, Geist Mono, Cormorant Garamond, JetBrains Mono), replace the `<link>` with `<link rel="stylesheet" href="/static/fonts/fonts.css">`. Served HTML then has 0 external refs. Flask serves `static/` by default (existing `/static/R3.png` already worked), so no route change needed.
   - (B) Ultralytics (YOLO) telemetry: `sync` is ON by default in `~/Library/Application Support/Ultralytics/settings.json` and can phone home on first model load. Fix: `from ultralytics import settings; settings.update({"sync": False})` (persists to the file) AND add env guards to `launch.command`: `export ULTRALYTICS_SYNCHRONOUS=False; export YOLO_OFFLINE=1`.
   - **How to PROVE zero egress** (don't trust `grep` alone): start the server, then `lsof -nP -p <PID> -iTCP -sTCP:ESTABLISHED` and inspect the OWNER PID of each external IP. This session's first capture showed Google/GitHub/Spotify IPs — but cross-checking `lsof -nP -iTCP@<ip>` proved they belonged to OTHER apps (Mail PID 693, Google 2640, Spotify 2445), NOT Luna-EDGE's python (PID 48816, which owned ZERO sockets). Luna-EDGE python must own no network socket during a model load. Commits: 2b4551d (privacy).

17. **Cross-thread `cv2.VideoCapture.release()` during an in-flight `read()` SIGSEGVs on Apple Silicon — NOT harmless.** Pitfall #14 (2026-08-14) claimed a watchdog force-releasing the source "unblocks a wedged read() on FFMPEG/AVFoundation." This session PROVED the opposite on this Mac: when the watchdog thread called `src.release()` (or `cap.release()`) while the capture thread was blocked inside `cap.read()`, `cv2`'s AVFoundation backend raised a native **SIGSEGV (exit 139)** that killed the entire Flask-SocketIO process — surfacing as "server dies when I click Detect / video never starts / whole app crashed." Root cause confirmed via `faulthandler` (recipe in `references/cv2-segfault-camera-permission.md`): the C-backtrace landed in `detect/sources/base.py` `read()` (the `self.cap.read()` line) and `detect/main.py` `watchdog_loop` (the `s.release()` line). FIX that shipped (commit 61aa1d8): make the watchdog **passive** (it only logs/flags, never calls `release()`); the capture thread owns the cap, detects `None`/stall itself, guards `read()` against a `None`/`!isOpened()` cap, and rebuilds the source on `None`. **Never let a non-capture thread call `cap.release()` while the capture thread may be inside `read()`.** This supersedes pitfall #14's "releasing from another thread unblocks a wedged read()" — that is unsafe on this hardware; #14's OTHER point (one capture thread, no per-read thread spawn) still stands.

18. **`det_fps="max"` → `float("max")` ValueError crashes `/api/start`.** `app.py` sends `"det_fps":"max"` to mean "no cap" (unlimited FPS), but `detect/main.py` did `det_fps = float(config.get("det_fps", 0))`, which raises `ValueError: could not convert string to float: 'max'` the instant detection starts → engine thread dies, WS never emits, the R-Tessera Detect button appears dead (and earlier the same start also triggered pitfall #17's segfault on top). FIX (61aa1d8): parse `det_fps` defensively — treat `"max"`/non-numeric/empty as `0` (unlimited) and only `float()` genuine numbers. Any "magic string" config knob must be parsed with `try/except` + sentinel, never `float()`-ed raw.

19. **`isOpened()==True` but `read()` returns `False` forever (or HANGS) = macOS Camera PERMISSION denied, not a code bug.** This session the engine ran fine but the webcam delivered zero frames: `cv2.VideoCapture(0, cv2.CAP_AVFOUNDATION).read()` returned `ok=False` on 24 consecutive tries (and in a separate probe *hung* instead of returning — AVFoundation can block on the first read when permission is absent). `system_profiler SPCameraDataType` showed the camera physically present, `lsof`/ps showed no other holder, yet no frames. That symptom = the Terminal/iTerm app launching the venv Python is NOT granted Camera in **System Settings → Privacy & Security → Camera**. It is NOT fixable from code — the user must grant/regrant the terminal app Camera access (toggle OFF then ON, relaunch terminal, allow the prompt). This is the single most common "Luna EDGE video suddenly stopped working" cause *after it worked before*, and it masks as an engine bug. Diagnostic + `faulthandler` recipe in `references/cv2-segfault-camera-permission.md`. If the whole Flask server *crashes* on Detect → pitfall #17; if it runs but shows no frames → this. (Confirmed this session: a long-running early instance streamed fine; later `read()` returned nothing after permission state changed — the engine code was correct, only the OS grant was missing.)

20. **`coco` skill streamed but drew ZERO boxes (silent) = ultralytics got a `FileNotFoundError` from a DOUBLE `.pt` extension.** The R-Tessera Detect toggle showed live video but no detection overlay. Root cause (commit d5f5ed0): `detect/detector/base.py` built the model path as `alias["coco"] + ".pt"` → `"yolov8n.pt"`, then passed that to `YOLO("yolov8n.pt")`. Ultralytics treats a string with a dot+extension as a LOCAL FILE path, so it looked for `yolov8n.pt.pt` (your `.pt` plus the extension it assumed), raised `FileNotFoundError`, loaded **nothing**, and silently returned zero detections — the stream still flowed, so it looked healthy. FIX: pass the BARE ultralytics alias `"yolov8n"` (no `.pt`) so ultralytics auto-downloads/loads the built-in model. Custom/trained skills still load by explicit path `skills/<name>.pt`. **Rule: never concatenate `.pt` onto a known ultralytics built-in name** (`yolov8n`, `yolov8s`, `yolov8x`, `yolov5s`, …). Verify with a 1-shot headless probe: `YoloDetector("yolov8n")` should print `MODEL LOADED OK` and `names[0]=='person'`; if it raises, the model path is wrong. This failure is SILENT — always confirm the model object is non-empty, don't trust "the video plays."

21. **`isOpened()==True` but `read()` returns `None` FOREVER (after you `kill -9`'d the server) = the macOS camera broker `VDCAssistant` is WEDGED, NOT a permission problem.** Distinct from pitfall #19. Symptom: earlier in the same session the camera delivered frames fine (permission WAS granted — verified 520 frames), then after several `kill -9 -f "app.py"` the device stopped yielding frames even though `system_profiler SPCameraDataType` shows the camera present and no process you own holds `cv2.VideoCapture`. Cause: AVFoundation's `VDCAssistant` daemon (the root-owned system camera broker) was left holding the device when its client was SIGKILL'd without a clean `release()`; it won't hand the device back until restarted. NOT code-fixable (needs `sudo`, which the agent lacks). RECOVERY (user action): quit & re-open Terminal, OR `sudo pkill VDCAssistant` (frees the device instantly). `system_profiler` showing the camera + `pgrep -fl app.py` being CLEAR does NOT mean the device is free — the real test is whether `cv2.VideoCapture(0).read()` returns a frame. **To avoid causing this:** never `kill -9` the engine repeatedly; use clean `kill -TERM` / the launcher's stop. Pair the bounded `_guarded_camera_read()` (wall-clock-threaded read timeout → fails loudly instead of hanging) with a live `frames` counter in `/api/status` counted at the capture point in `detect/main.py` (true even with no WS client), so R-Tessera can tell "delivering" (`frames` climbing) from "running but stuck" (`frames:0`). The guard detects a wedged camera but does NOT un-wedge it.

## Reference files
- `references/bugs-and-verification.md` — condensed transcripts of the 3 bugs fixed this
  session (squash, sibling-selector, header-occlusion) + the ad-hoc verification recipe.
- `references/insta360-cameras-ptz.md` — full recipe for the Insta360 Link / USB-webcam PTZ
  source (digital crop PTZ, tracking hook), `/api/cameras` auto-detect, and verification steps.
- `references/stop-clear-frame-teardown.md` — the frozen-frame / stalled-restart bug: why
  Stop/Reset must clear `latestBitmap` and `_teardown_engine()` must join the engine thread
  before a new source can Start; full fix + headless verification recipe.
- `references/file-source-uri-leak.md` — the "local file processing not working" bug: a stale
  webcam index `"0"` in the shared hidden `uri` field leaks into `FileSource` and crashes the
  engine thread; fix shape + headless WS-frame verification recipe.
- `references/verify-live-ws.md` — working headless WebSocket verification script (count binary
  frames + parse JSON dets) + the ~6s `yolov8n` model-load latency gotcha. Use after every
  engine/source edit to prove the feed truly works, not just that the server is up.
- `references/upload-clear-and-stale-server.md` — the session where uploads accumulated (14 dupes
  from repeat uploads) + the `clear_uploads()` fix, the stale-server-process that masked it, and
  why `atexit` alone missed SIGTERM. Includes the correct restart/kill recipe.
- `references/ai-learning-rebuild.md` — the 2026-08-14 agreed redesign of the AI Learning tab:
  separate `/learn` page (not a shared canvas), the silent frame-mismatch capture bug, the 8-step
  curriculum, dataset-manager UX, and the phased build plan. Read before touching Learning UI.
- `references/learn-tab-built.md` — AS-BUILT record of the shipped `/learn` tab (2026-08-14):
  the 6-step flow, routes added, the client-side freeze that reuses `/api/learn/capture` (no
  `/api/learn/frame/freeze`), the felt-vs-invisible UX call (freeze/label kept, MPS dropped), the
  exact `requests`-mirrors-`fetch` verification recipe, and the localhost browser-tool block.
- `references/cv2-segfault-camera-permission.md` — Apple-Silicon `cv2` SIGSEGV
  (cross-thread `cap.release()` during `read()`) + the macOS Camera-permission
  "opened-but-no-frames" trap (pitfall #19); `faulthandler` recipe. Governs #17/#19.
- `references/camera-wedge-detector-fix.md` — the 2026-08-26 session: the
  `yolov8n.pt` double-extension SILENT zero-detection bug (pitfall #20) + the
  `VDCAssistant` camera wedge after `kill -9` (pitfall #21). Exact headless probes
  to distinguish "no model" vs "permission denied" vs "device wedged", and the
  `_guarded_camera_read` / `frames` counter code shape.

## Live frame verification — WS end-to-end (the real "feed works" bar)
`curl`'ing the served HTML only proves the page loads; it does NOT prove the engine
streams frames/dets. For a true working check, connect to `ws://localhost:8000/ws`
and count binary frames + parse JSON detections. Working recipe + the model-warmup
gotcha are in `references/verify-live-ws.md` — use it after every engine/source edit
to satisfy MARU's "done = visibly working" bar. Key gotcha: `/api/start` returns
`running:True, error:None` instantly, but `yolov8n` takes ~6s to load before the
first frame; **wait 10s before asserting frame count** or you'll misread a healthy
feed as dead.

## Phone camera scan + source-switch UX (2026-09-22)
### `/api/scan-cameras` — phone camera discovery
Add a parallel subnet scan for IP Webcam Pro (and similar phone camera apps):
- Probe local subnet (`get local IP via UDP to 8.8.8.8`, take first 3 octets) `.1`–`.9`
- Fallback IPs for common phone tether/hotspot ranges: `172.20.10.3`, `192.168.0.12`, `192.168.1.12`, `192.168.43.12`, `192.168.43.1`, `10.0.0.12`
- Endpoints to probe (in order): `http://<ip>:8080/video`, `http://<ip>:8080/videofeed`, `http://<ip>:8080/shot.jpg`, `rtsp://<ip>:554/live`
- **Use GET request, NOT HEAD** — IP Webcam Pro returns 405 on HEAD
- Run probes in parallel (`ThreadPoolExecutor`, max_workers=10) with `as_completed` + 8s overall timeout
- Server-side 60s cache (`_camera_cache = {"camera": None, "expires": 0}`) to avoid re-scanning on every page load
- Return `{"ok": True, "cameras": [{"uri": "...", "name": "IP Webcam (...)"}]}`

### Frontend scan UI + source-switch UX
- Add 📱 **Scan** button next to Source URI input — populates datalist with discovered cameras
- **Auto-stop on source switch:** `srcSel.onchange` calls `stopAndClear()` (sets start_requested=false, hides model load, fetches `/api/stop`, connects WS, clears feed, sets status to stopped). Prevents zombie engines from holding camera devices open.
- **Auto-set URI per source kind** in `syncSourceUI()`:
  - `webcam` → `"0"` (local AVFoundation index)
  - `ipcam` → restore from `localStorage.getItem('luna-edge.last-camera')` if valid
  - `file` → empty (upload required)
- **localStorage memory:** on Start, save URI if not the default placeholder (`http://192.168.0.12:8080/video`). On load, restore it.
- **DO NOT auto-start** — founder explicitly wants to pick source manually after scan

### Model path resolution fix (2026-09-22)
`yolov8n.pt` resolved relative to `/` (process cwd) when launched via `.app`/launcher → GitHub rate-limited download failure.
- In `detect/detector/base.py` `YoloDetector.__init__`: check repo root (`REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))`) for `{alias_name}.pt` before falling back to bare alias name
- In `app.py` `resolve_skill_path`: same repo-root check before returning `f"{alias_name}.pt"`
- This means base models MUST live at repo root (next to `app.py`) for offline launching

### ROVER-KIT Status menu bar app (Swift)
- `~/Desktop/ROVER-KIT Status.app` — Swift Cocoa `NSStatusItem` app
- Polls every 5s: `port_open(8000)` + `pgrep -f "cloudflared tunnel"` + tunnel URL from log
- Icon states: 🟢 (EDGE + tunnel up), 🟡 (EDGE only), 🔴 (down)
- Menu: status lines + Open R-Tessera / Open EDGE / Start / Stop / Quit
- Auto-starts on login via `~/Library/LaunchAgents/com.luna-edge.roverkit-status.plist`
- Bundle: `~/luna-edge/RoverKitStatus/main.swift` compiled with `xcrun swiftc -O -wmo`

### Demo button flow (2026-09-22)
One-click flow: Demo.app → Luna EDGE on :8000 → cloudflare tunnel → scan → auto-start YOLO detection
- `launch-roverkit.sh` handles server + tunnel + Supabase patch + browser open
- Frontend auto-scans on page load, populates dropdown, waits for user to pick source + click Start
- Source-switch auto-stops previous engine cleanly

## Verification (no test suite in repo — use ad-hoc scripts)
Write a throwaway script to a temp path (e.g. `/tmp/hermes-verify-edge-ui.js`), run with
`node`, then `rm` it. Patterns that WORKED this session:
- Static parse of `templates/index.html`: assert both `AI Learning`/`AI Detection` buttons
  present and NOT `display:none` inline; no `function setLearning` leftover; both `#aiDetPanel`
  and `#learnPanel` exist; `toggleLearning`/`toggleDetection` wired; brand `.85rem` + turquoise
  `0.06em`; railing contains "LunaV EDGE — 3D Engine Online" + "LUNAV EDGE — ROVER-R"; `<script>`
  braces/parens balanced (split on the char, compare counts).
- Live server (KILL FIRST, then start — see pitfall #7): `pkill -9 -f "app.py"; sleep 2;
  (lsof -i:8000 | grep LISTEN) || echo "port free"` to confirm the old process is gone;
  then `(cd ~/luna-edge && source .venv/bin/activate && python app.py &)`; `sleep 4`;
  `curl -s http://localhost:8000/` → assert HTTP 200 and the marker strings appear in served HTML.
- NEVER use `pkill -f "luna-edge/app.py"` — the launch cmdline is `python app.py`, which that
  pattern never matches, so it silently leaves the stale server running. Use `pkill -9 -f "app.py"`.
- Always re-verify against the LIVE served page/route after any `index.html`/`app.py` edit —
  stale evidence from a pre-edit server is invalid.
- Note: do NOT write throwaway scripts to `/private/var/folders/.../T/` — that path is a
  protected system temp and the write will be refused; use `/tmp/` instead.

## Commit flow
`git add <files>` then `git -c user.name=maru -c user.email=kingkymaru@gmail.com commit` then
`git fetch origin main && git rebase origin/main` then push. Update
`~/Documents/obsidian_maru_1/Projects/Luna-Edge-Checkpoint.md` (vault note is source of truth, not git).
