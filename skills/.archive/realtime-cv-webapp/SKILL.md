---
name: realtime-cv-webapp
description: Stream YOLO detections to browser via WebSocket for CV apps.
---

# Realtime CV Webapp (local / offline)

Build a real-time computer-vision viewer that runs entirely on a local machine (no cloud), streams a camera/feed through a model (YOLO), and shows annotated video + detections in a browser at localhost.

## When to use
- "Show live detections in a browser from a webcam / IP cam / drone / file."
- Offline-first field tools (NO internet at the deployment site).
- Source-agnostic detectors (any camera = just a URI swap).

## Architecture (4 swappable layers)
1. **Source** — frame producer. Subclasses: webcam (`/dev/videoN`), IP cam (`rtsp://` or `http` MJPEG, e.g. Android "IP Webcam" serves MJPEG at `http://<ip>:8080/video`), drone (HDMI capture device or DJI stream), file (mp4 replay). Live and recorded are just two implementations; the detector can't tell them apart. Contract: `read() -> (frame, ts)`.
2. **Detector** — source-blind. YOLO (ultralytics) with skill = weights file (`coco` / `ppe` / `crack` as drop-in modules). Swap skill, not code. `coco` aliases to `yolov8n.pt` (auto-downloads on first run).
3. **GeoAdapter** (optional) — maps screen bbox to ground (telemetry / fixed cam / file replay). Kept OUT of the detector core.
4. **Sink** — stdout / local WebSocket / local SQLite / Supabase (post-mission only).

## Critical pitfalls (these bite silently — verify, don't assume)
- **WS handler must NOT call `receive()` in the send loop.** `ws_conn.receive()` BLOCKS until the client sends something. The browser never sends → after the first frame the handler blocks/errors and the stream DIES. Symptom: ONE frame shows, only updates on page refresh. Fix: stream in `while True` sending from queues; detect disconnect via a `send()` exception; `time.sleep(0.02)` pump. Verified: 145–201 frames/3s after fix vs single-frame-death before.
- **Decouple capture from inference.** A single tight loop (capture+infer+encode) caps FPS at the infer rate (~15fps). Fix: capture thread grabs frames at full rate into a latest-frame slot; infer thread runs YOLO at `det_fps` (e.g. 8 Hz) and updates latest-detections; viewer draws latest frame + latest boxes every capture frame → smooth video, boxes refresh a few times/sec. User explicitly wanted "near live" without YOLO at full rate. Capture rate (e.g. 27fps from an IP cam) is independent of det_fps.
- **Down-scale for infer, scale boxes back.** 1080x1920 frames are slow. Resize to `proc_w=640` for YOLO, multiply returned boxes by `w/proc_w` to map back to full-res for drawing.
- **MPS on tiny frames can be SLOWER than CPU** (GPU transfer overhead dominates for small batches). For yolov8n at 640px, CPU was faster than `.to('mps')`. Benchmark before assuming GPU helps.
- **JPEG re-encode quality 60** is fine for a viewer; lower latency than 70+.
- **Frame queue with maxsize + drop-oldest** prevents backlog when the WS client is slow.
- **Browser MUST use `<canvas>` + `requestAnimationFrame`, NOT `<img>.src` per message.** Setting `feed.src = URL.createObjectURL(...)` on every WS message (~50/s) repaints slower than messages arrive → onmessage callbacks pile up in the event loop → the DISPLAYED frame falls further behind over time. Symptom maru hit: constant ~1.5s lag that GREW worse past ~15s. Fix: store newest bytes + `createImageBitmap` off the critical path; a `requestAnimationFrame` paint loop draws the newest frame once per display refresh and drops uns hown ones. This decouples network receipt from paint — the lag stays flat. (The constant 1.5s base is the phone IP-cam's own encode latency, not the pipeline; swap to a USB/Mac webcam to remove it.)
- **The canvas+rAF fix ALONE is NOT enough — TWO more time-proportional accumulators remain and WILL regrow lag.** Found when maru reported lag "persist[ed] over time" even after the rAF fix was already in place:
  1. **Unbounded decode fan-out.** Per-message `createImageBitmap(...).then(...)` fires one async decode PER frame with NO gate. When frames beat decode, promises pile up and run on the main thread even after the frame is stale → main-thread CPU saturates → rAF paint starves → lag grows the longer it runs. FIX: a single in-flight decode gate. Store newest bytes; only ONE `createImageBitmap` runs at a time; on resolve, if a newer frame arrived, decode again, else stop. Dropped frames cost nothing (you only ever show the newest). Exact gated-decoder snippet in `references/lag-debugging.md`.
  2. **Unbounded log DOM.** `el.innerHTML += ...` on every detection, forever, with `scrollTop=scrollHeight` on a node that only grows → each append/scroll gets progressively more expensive in a busy scene. FIX: cap the log (keep last ~50 children via `while(el.childElementCount>50) el.removeChild(el.firstChild)`). Cheap, keeps DOM cost flat over time.
  - **Server-side encode throttle (secondary):** if `infer_loop` re-encodes EVERY captured frame to JPEG (50+ Hz) but the WS pump only ships ~30 Hz and drains-to-newest, most encodes are wasted CPU. Throttle the encode with a `1/30s` timestamp gate so sustained CPU stays flat. Smaller win than 1 & 2 once those are fixed, but removes a constant load floor.
  - **Verifying a lag fix needs a LONG RUN + user report, NOT HTTP 200.** A 200 proves the page serves; it proves nothing about growing lag. After any viewer change: (a) confirm the gated decoder + bounded log are present in the SERVED html, (b) `node --check` the inline script, (c) ask the user to run it several minutes and report whether lag stays flat. There is NO headless way to assert "lag doesn't grow."
- **Set `CAP_PROP_BUFFERSIZE=1` on every capture source** (webcam/ipcam/mavic). OpenCV internally buffers decoded frames; without it the source hands you stale frames = hidden latency on top of the model.
- **Stop must be BULLETPROOF, not a flag flip — a hung source read() leaves a ZOMBIE engine thread.** A weak Stop that only sets `running=False` (or a dict `stop["go"]=False`) can be OBSERVED ONLY if the capture loop reaches its loop check. But `cv2.VideoCapture.read()` (especially on a flaky IP cam / S22 over WiFi) can BLOCK FOREVER when the stream stalls — the loop never re-checks the flag, so the engine thread never exits, the webcam is never released, and a SECOND Start spawns a second engine on top (or the old one holds the port/camera). maru hit this as "blank page" + mysterious respawned processes. FIX (verified end-to-end):
  1. Pass a `threading.Event` `stop_event` into `run()`; both `capture_loop` and `infer_loop` check `not stop_event.is_set()` in their `while` conditions (not just a dict flag).
  2. **Wrap the source read in a wall-clock watchdog.** `safe_read()` runs `src.read()` in a daemon sub-thread and `join(READ_TIMEOUT=3.0)`; if it's still alive after the timeout, return `None` (treat as no frame) so the capture loop IMMEDIATELY re-checks `stop_event`. Without this, a single blocked read defeats the Event entirely.
  3. Server `/api/stop` sets `stop_event.set()` AND `thread.join(timeout=5)`; if still alive after 5s, log a WARN (it's a daemon thread so it can't outlive the process, but the log surfaces the stall). A `start` while `running` returns `ok:false, already running` (guards double-spawn).
  4. `run()`'s `finally:` sets `stop_event`, joins both threads (timeout=2), then `src.release()`.
  - **Verifying the Stop fix needs a STALLED-source test, not HTTP 200.** HTTP 200 only proves the page serves. To prove Stop kills a hung engine: monkeypatch `build_source` to return a source whose `read()` does `time.sleep(3600)`, start via the app's test_client, then POST `/api/stop`, then assert the engine thread is `not alive` within ~5s AND a second `/api/start` succeeds. (Exact recipe in `references/stop-hardening.md`.) There is NO way to assert this with a normal curl status check alone — the thread can be "running:false" in state but still alive in reality.
- **Multiple-instance port fight = blank/confused page.** If an OLD server instance is still bound to the port (e.g. from a previous `launch.command` run with a different bind, or a backgrounded process that never died), a new launch binds a SECOND process; the browser may hit either, and stale/old-code servers serve pre-fix pages → "blank" or inconsistent behavior. Before a launcher change or after any kill/relaunch churn, KILL ALL instances (`pkill -9 -f "luna-edge/app.py"`) and confirm EXACTLY ONE `pgrep` match (parent+child = one server) before declaring victory. The crypto_bot 1m app on :5055 is independent and must NOT be killed.
- **"Detections arrive but NO video" = forgot `frame_q.put(jpg)` in the infer thread.** After decoupling capture/infer, the frame-to-browser queue push lives in `infer_loop`; if it's dropped, only `det_q` (text) flows and the browser shows boxes in the log but a blank feed. Always push the annotated JPEG to `frame_q` inside `infer_loop`.

## Detection-box anti-flicker (flickering boxes when detection is intermittent)
- Symptom maru hit: "the box detecting object is flickering and making it hard to read what is detected." Root cause: boxes were re-baked into the JPEG EVERY frame (`encode(draw(frame, dets))`); when one frame momentarily MISSES the object (or the bbox jitters a few px) the box pops in/out each refresh → unreadable.
- **Fix:** (1) Engine ships the RAW frame — do NOT call `draw()` in the frame path (`jpg = encode(frame, quality=60)`). (2) Browser draws boxes as a `<canvas>` overlay holding each detection for `HOLD_MS=500` via a `seen=performance.now()` timestamp; a 1-frame miss doesn't erase the box. Scale `bbox` (full-frame px, engine already scaled back up by `w/proc_w`) by `canvas.width / latestBitmap.width` (NOT CSS size). A fresh det batch refreshes every box's `seen`, so a live object's box stays put and only fades 500ms after it's truly gone.
- **Verifying the fix is easy to FALSE-PASS.** HTTP 200 + `node --check` prove nothing about baking. To prove: run `detect.main.run()` with a REAL `queues={"frame":fq,"det":dq}` (passing `queues:None` skips the encode branch entirely → silent false PASS), monkeypatch `detect.viewer.encode` to capture the frame and `detect.viewer.draw` with a spy; assert `captured['frame'] is not None` AND `draw() NOT called`. Full pattern + hold-predicate test in `references/box-overlay-anti-flicker.md`.

## Adding a PTZ-capable webcam (Insta360 Link) as a source + digital tracking mode
A UVC PTZ webcam (Insta360 Link) needs NO proprietary SDK for a local viewer: macOS exposes it
as a normal AVFoundation capture device, so it's just a `cv2.VideoCapture(index)` source like any
webcam — enumerate via `system_profiler SPCameraDataType` / `ffmpeg -f avfoundation -list_devices`.
"PTZ" here = DIGITAL: keep the full 4K frame as the wide view and crop a window around the target,
resize the crop to output size. (Not motor PTZ — that needs the vendor SDK; don't claim it.)

- Add `insta360` to the source `<select>` + a "Tracking mode" checkbox; the JS shows the toggle only
  when `insta360` is picked, sets the device index in the URI field, and includes
  `track: <checkbox>.checked` in the `/api/start` payload.
- Backend: a `PtzSource(Source)` that opens the device index and, in `read()`, crops its current
  window (stored as fractions of the full frame) and `cv2.resize`s to output. `set_target(cx,cy,fw)`
  records a desired window; `read()` lerps current→target (`k≈0.15`) for smooth motion.
- Detector hook: in `infer_loop`, after a detection batch, feed the TOP-CONFIDENCE box to the source
  if it has `set_target`: `if dets and hasattr(src,"set_target"): src.set_target(centroid..., width...)`.
- **CRITICAL coordinate-mapping pitfall:** when tracking is ON, the detector runs on the CROPPED
  frame, so the detection centroid fractions are in CROP-space. Feeding them straight to `set_target`
  (which places them in FULL-frame space) makes tracking drift/off-center. The source must map
  crop-space → full-frame space using its CURRENT window before storing the target:
  `fx = (win_cx - win_hw) + cx * (2*win_hw)` (same for fy, and scale the width fraction by the window).
- Config-driven: `source.kind` may be `insta360`; `build_source` returns `PtzSource(uri, track=...)`.
- **macOS "command not found: python":** when starting the Flask server from a non-activated shell,
  `python` isn't on PATH (Homebrew/venv). Always launch with the explicit venv interpreter
  `.venv/bin/python app.py`, and kill stale instances (`pkill -f "luna-edge/app.py"`) before
  relaunch so the browser doesn't hit an old pre-fix server. Full pattern in
  `references/ptz-tracking-source.md`.

## Offline-first pattern (field deployment)
- Everything local: capture + model + localhost webapp (Flask) + local map viewer + local SQLite. No Vercel/Supabase/cell at site.
- LUNAV/Supabase = POST-MISSION sync only (export local store when back in coverage).
- **Cesium (or ANY CDN dep) in an offline-first tool is DEAD WEIGHT and a blank-page risk — strip it unless the map is actually wired.** maru asked "why do we need Cesium here?" twice; the answer: it's only for the (unbuilt) Geo→map viewer, and with `Geo=none` it does NOTHING but still loads `unpkg.com/cesium...js` on every page load — an external fetch that (a) defeats "offline-first", and (b) can block/slow page init. A render-blocking `<script src=cdn>` that fails/slow makes the WHOLE inline script (canvas, WS, Start button) never run → BLANK PAGE. FIX: remove the CDN `<link>`/`<script>`, the `#map` div, and all `viewer`/`ensureViewer`/`addDet`/`clearMarkers` code; keep Geo as a no-op selector. If geo is later built, VENDOR Cesium locally — do not reintroduce the CDN tag.

## Verification (run, don't assume)
- WS frame-rate probe: connect a `websockets` client, count frames over 3s. Expect ~capture-rate (e.g. 145 frames/3s ≈ 48fps pump). A single frame = handler died.
- Import check: all changed modules import cleanly.
- Note: you cannot see the browser render — verify the data path (frames delivered) and trust the visual; ask the user to confirm on-screen.

## Founder context (MARU / Neo)
- Discovery-before-code: when the user says "explore first / no code yet / just discovery", STAY in discovery; do not scaffold or write files.
- Reply straight, short, fact-based; do not over-think or over-explain. Confirm facts, then answer concisely.
- Offline-first is a HARD constraint for field demos (deep-jungle dam: NO internet). Design the whole system to run with zero external calls; cloud is post-mission only.

## Local desktop launcher (macOS)
For field use, give the operator a one-click start: a `launch.command` on the Desktop that activates the venv, starts the server, waits for the port, and opens the browser (kills any prior instance first). Optionally wrap as a `.app` for a no-Terminal-window double-click, but the `.command` file is the most reliable launcher (Gatekeeper may block a hand-built `.app` on first run). Reproduce from `templates/launch.command`.
- **GUI-launch environment trap (HIGH-frequency failure):** when a `.command` is double-clicked, macOS opens it via the GUI (`open`), which runs with a BARE environment — `PYTHONPATH` / user `site-packages` are often NOT on `sys.path`. So `python3` resolves to `/usr/bin/python3` and `import flask` → `ModuleNotFoundError`, but the failure is silent (logged to the file, nothing on screen) → "double-click did nothing." FIX: in the launcher, explicitly `export PYTHONPATH="$HOME/Library/Python/3.9/lib/python/site-packages:$PYTHONPATH"` and `export PATH="$HOME/Library/Python/3.9/bin:$PATH"` BEFORE launching, and use an explicit `PYBIN` (e.g. `/usr/bin/python3`) that has the deps. VERIFY by actually launching via `open <file>.command` (not `bash <file>` from a shell, which has the working env) and checking the port + log.

## references/
- `references/flask-ws-yolo-pattern.md` — condensed code patterns (correct WS handler, decoupled threads, config keys, browser img-from-binary).
- `references/lag-debugging.md` — the FULL lag root-cause map: canvas+rAF (necessary), gated decode fan-out (1), bounded log DOM (2), server encode throttle, gated-decoder snippet, and the long-run verification approach.
- `references/mindar-image-ar-bugs.md` — MindAR image-tracking WebAR (marker-anchored AR): `start()` vs `startScanning()` "is not functioning" camera-error bug, `.mind` being gated by auth, local-target hosting.
- `references/stop-hardening.md` — Stop must kill a STALLED engine thread (not just flip a flag): stop_event + read watchdog + join(timeout), plus the verified stalled-source test_client recipe.
- `references/box-overlay-anti-flicker.md` — detection-box anti-flicker: raw-frame + 0.5s browser overlay hold; the `queues:None` false-pass verification recipe.
- `references/ptz-tracking-source.md` — adding a PTZ UVC webcam (Insta360 Link) as a source: PtzSource crop+lerp, the crop→full-frame coordinate-mapping pitfall, detector tracking hook, UI wiring, verify recipe.
- `templates/launch.command` — known-good macOS one-click launcher (venv + start + wait + open browser + PYTHONPATH pin).
