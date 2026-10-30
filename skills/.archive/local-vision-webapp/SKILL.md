---
name: local-vision-webapp
description: Local offline YOLO vision localhost browser via WebSocket.
---

# Local Vision Webapp (offline-first, source-agnostic YOLO + localhost viewer)

Use when: building a local computer-vision app that must run WITHOUT internet (field demo,
remote site, offline inspection); streaming YOLO detections + annotated video to a browser on
localhost; "use my webcam / phone IP-cam / drone cam as a source"; "run YOLO locally and show it
in a web UI". The detector must work for ANY camera source, live or recorded.

## Core architecture — 4 swappable layers
- **Source** (frame producer, pluggable): webcam (`/dev/videoN`), IP cam (`rtsp://` / http MJPEG
  from a phone app), Mavic/HDMI capture device, or File (mp4 replay). Live and recorded are just
  two Source subclasses — the Detector CANNOT tell them apart. Pass `--source <uri>`; never
  hardcode the camera.
- **Detector** (source-blind): YOLO via ultralytics. "Skill" = a weights file (coco / ppe / crack).
  Swap the weights, not the code. coco → `yolov8n.pt` (auto-downloads first run).
- **GeoAdapter** (optional, per source): maps screen bbox → ground (Mavic telemetry, fixed-cam
  pose). Kept OUT of the detector core so the detector stays pure vision.
- **Sink** (pluggable): stdout / local SQLite / local WebSocket / Supabase (post-mission ONLY).

## Key patterns
- **Decouple capture from inference.** Capture thread grabs frames at full rate into a
  `latest_frame` slot. Infer thread runs YOLO at a CAPPED rate (`det_fps`, e.g. 8 Hz). Draw the
  latest boxes on every captured frame → smooth video, boxes refresh a few times/sec.
  Video FPS ≠ detection FPS, and that is correct: you do NOT need YOLO at 27fps.
- **Browser streaming via shared queues.** Engine pushes annotated JPEG frames + detection JSON
  into global `frame_q` / `det_q` queues; a WebSocket handler streams them to the browser. This
  decouples engine-start from browser-connect order (engine can run before the page opens).
- **Offline-first.** No cloud at the site. LUNAV/Supabase are POST-MISSION export/sync targets
  only. Run the webapp on `127.0.0.1` — no internet needed.

## PITFALLS (learned the hard way — embed these)
1. **flask_sock WebSocket: NEVER call `ws_conn.receive()` in the streaming loop** to "detect
   disconnect". It BLOCKS until the client sends something; the browser never sends, so the loop
   dies after the first frame. Symptom: single frame that only updates on page refresh. Fix:
   detect disconnect via a `send()` exception; never call `receive()` in a stream loop.
2. **Apple-Silicon MPS is SLOWER than CPU for small yolov8n frames (640px).** GPU transfer
   overhead dominates. Use CPU for yolov8n@640. MPS only helps large/batch inference.
3. **OpenCV holds an internal frame buffer → latency.** Set `cv2.CAP_PROP_BUFFERSIZE = 1` on
   EVERY `VideoCapture` (webcam / ipcam / mavic). Without it you get ~1–1.5s lag.
4. **WebSocket drain-to-newest.** If the handler does one `get_nowait()` per loop with a
   `maxsize=4` queue, the viewer lags 4 frames behind. Drain the queue to the newest frame before
   sending (`while True: jpg = q.get_nowait()` in try, send the last one caught).
5. **Refactor drop:** when splitting capture/infer/display into threads, make sure the annotated
   frame is actually pushed to the browser queue (`frame_q.put_nowait(jpg)`) in the infer loop.
   Easy to lose during a rewrite → you get detections (text) but NO video (binary). Verify both
   binary frames AND text arrive on the socket.
6. **Source-agnostic discipline:** the detector must never know the source. A "drone" is just a
   Source URI. This is what lets one engine serve webcam / phone / ROV / fixed cam unchanged.
7. **Canvas aspect ratio (native, NOT stretched).** Drawing the frame as
   `ctx.drawImage(bmp, 0,0, canvas.w, canvas.h)` SQUASHES a 16:9 movie in a tall panel.
   Use `object-fit: contain` math: `scale=min(cw/fw, ch/fh)`, center it (letterbox). Box overlays
   and any learning-mode box-draw MUST scale against the contained rect (`containRect={x,y,w,h}`),
   not the full canvas — otherwise the feed distorts AND training labels land on the warped
   canvas (poisoned dataset). Learning normalize: `nx=(mouseX-cr.x)/cr.w`, clamp 0..1.
8. **Floating/collapsible sidebar** for full-aspect viewing: make the control panel
   `position:absolute` over the video and add a collapse toggle. The toggle MUST be
   JS-driven, NOT a CSS sibling selector (`#sidebar.collapsed ~ #launcher` silently
   fails if the two elements are not DOM siblings — leaving NO way to reopen the panel;
   that exact bug shipped once). In `setCollapsed(v)` set `launcherEl.style.display =
   v ? 'inline-flex' : 'none'` so the collapsed state shows its own reopen control (a
   top-left `L · Controls` pill). `–` in the panel header collapses; the pill expands.
   See edge-ai-vision/references/ui-shell-toggle.md.

## Verification (ad-hoc, NOT a full lint suite — faster and sufficient for UI work)
- **Wiring:** feed a synthetic frame (`np.zeros((h,w,3))`) through the full pipeline (no camera
  needed) to confirm Source→Detector→Sink imports and runs.
- **Live stream:** connect a `websockets` client to `ws://127.0.0.1:8000/ws` and count BINARY
  frames received in 3s. Expect continuous delivery (~tens of frames). If 0–1 frame → the WS
  handler died (pitfall 1). Re-run `scripts/verify_stream.py`.
- Confirm BOTH binary (video) and text (detections) messages arrive — catches pitfall 5.

## References & scripts
- `references/patterns.md` — condensed code sketches (4-layer skeleton, decoupled threads,
  flask_sock WS handler with drain-to-newest, buffersize=1).
- `scripts/verify_stream.py` — re-runnable WebSocket frame-rate probe (binary vs text count).
