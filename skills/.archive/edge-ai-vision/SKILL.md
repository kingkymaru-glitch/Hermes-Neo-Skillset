---
name: edge-ai-vision
description: Build offline-first source-agnostic YOLO detection webapp.
category: computer-vision
---

# Edge AI Vision — offline-first source-agnostic detection

Use when building a local computer-vision inspection system: YOLO object detection
from any camera (webcam, phone IP-cam, drone, ROV, file replay) with a browser
GUI, intended to run with NO internet (field/dam/port ops). The Luna-EDGE project
(github.com/kingkymaru-glitch/luna-edge) is the reference implementation.

## Core architecture — 4 swappable layers
Decouple so the detector never knows what camera or cloud is upstream:
1. **Source** — `read() -> (frame, ts)`. Subclasses: Webcam, IPcam (rtsp/http),
   Mavic (HDMI capture or DJI stream), File (mp4 replay). Live and file are JUST
   two Source classes; the Detector can't tell them apart. Swap via config, no code change.
2. **Detector** — source-blind. YOLO; "skill" = weights file. Emits `Detection(ts,cls,conf,bbox)`.
3. **GeoAdapter** (optional, per source) — maps screen bbox to ground. Kept OUT of
   the detector core. None / Mavic telemetry (lat,lon per frame) / Fixed cam
   (static lat+orientation) / File replay (telemetry log).
4. **Sink** — stdout / local WebSocket / local SQLite / Supabase (post-mission only).

A `Detection` dataclass carries optional lat/lon/elev/heading (default None).

## Offline-first principle (hard constraint for field use)
Everything runs LOCAL on the operator machine: capture + YOLO + control UI
(localhost) + twin viewer (local Cesium) + storage (local SQLite/JSON).
NO Vercel/Supabase/cell at site. LUNAV/cloud = POST-MISSION sync only (export
local store when back in coverage). Process at edge, sync later.

## Localhost webapp (the GUI)
- Engine = local Python process (not a webapp). It pushes frames+detections out.
- Control panel + viewer = a LOCAL web app on the Mac (Flask + flask_sock WebSocket,
  Cesium map). Served from 127.0.0.1, no internet. Same UX as web, localhost only.
- Stream annotated frame as JPEG **bytes** over the WebSocket; detections as **text**
  JSON on the SAME socket. Browser: `ws.binaryType='arraybuffer'`; if `typeof data==='string'`
  → detections, else → Blob image. This dual-type trick is the key to live video in-browser.

## Modular skills (not rewrites)
Base = YOLO COCO (80 classes, runs day 1). New domains = SEPARATE .pt weights:
ppe, crack, sheen, fence-gap. Run one or merge. Train later from any frames.
The detector loads `skills/<name>.pt`; alias `coco` -> `yolov8n.pt` (ultralytics
auto-downloads on first run). Never hardcode a model inside a source.

## Pitfalls (see references/pitfalls.md)
- Circular import: geo/base.py and sinks/base.py must `from ..detector.base import Detection`,
  NOT `from .base import Detection`.
- YOLO weights: pass `yolov8n.pt` (auto-download), not `coco.pt`; skill->alias mapping.
- OpenCV on macOS: default `VideoCapture(0)` may fail; try CAP_AVFOUNDATION backend
  and verify device index. IP-cam MJPEG endpoint is usually `/video` (probe `/video`,
  `/videofeed`; 404 means wrong path).
- flask_sock: `socket.send()` accepts both str and bytes — use that for frame+detections.
- Cesium viewer loads JS from unpkg CDN → vendor locally for true offline field use.
  **NOTE:** in practice the Cesium twin was REMOVED from Luna-EDGE — it was dead
  weight (Geo=none by default, only a stub for the unbuilt Mavic map) and a CDN
  fetch that breaks the page when offline. Don't add a map viewer until the
  geo-adapter lands. Offline-first means NO external script tags at all.

## Streaming stability (Luna-EDGE proven fixes — see references/streaming-stability.md)
These prevent the classic "works 15s then lags / boxes flicker / Stop hangs" failures:
- **Growing lag** = paint backlog: never `createObjectURL`+`img.src` per WS msg.
  Use `<canvas>` + `requestAnimationFrame`; store newest frame, drop stale.
- **Flicker** = boxes baked into each JPEG pop in/out on missed frames. Ship the
  RAW frame from the engine (no `draw()` in the encode path); draw boxes as a
  browser canvas OVERLAY with a 0.5s HOLD (keep each detection's `seen` timestamp;
  redraw while `now - seen <= 500ms`).
- **Aspect ratio (native, NOT stretched).** The canvas viewer must draw the frame
  with `object-fit: contain` math (letterbox: `scale=min(cw/fw, ch/fh)`, center it),
  NEVER `drawImage(bmp,0,0,canvas.w,canvas.h)` — that SQUASHES a 16:9 movie in a tall
  panel. Two consequences if you stretch: (1) the feed looks distorted; (2) in
  learning mode the drawn/training boxes map to the warped canvas → corrupt labels.
  So box overlays AND the learning box-draw must scale/draw against the **contained
  rect** (`containRect={x,y,w,h}` of the letterboxed frame), not the full canvas.
  Learning-mode normalize: `nx=(mouseX-cr.x)/cr.w`, `ny=(mouseY-cr.y)/cr.h`, clamp 0..1.
  Relabeling on a distorted frame POISONS the dataset. (Replaces the older
  `canvas.w/bitmap.w` scaling note, which only held when the frame filled the canvas.)
- **Floating control panel + minimize** = panel `position:absolute` over the video,
  collapsed via a `transform` slide. THE TOGGLE MUST BE JS-DRIVEN, NOT a CSS sibling
  selector: `#sidebar.collapsed ~ #launcher` silently fails if `#launcher` and `#sidebar`
  are not DOM siblings (they weren't — launcher was beside `<header>`, sidebar inside `.row`),
  leaving NO way to reopen the panel. Drive `launcherEl.style.display` in `setCollapsed()`.
  The collapsed state must show its own reopen control (glowing top-left `L · Controls` pill).
  See references/ui-shell-toggle.md.
- **LunaV glass shell** = reskin to LunaV Studio tokens (turq #2f9bff, hairline borders,
  `backdrop-filter: blur(22px)` glass, Inter font, `LunaV EDGE` brand bar, live status pill,
  `LunaV Labs` bottom railing). Makes an offline tool look first-party. See references/ui-shell-toggle.md.
  Keep it offline-first: an Inter webfont via Google Fonts is fine (graceful system fallback),
  but add NO other CDN script tags.
- **Stop hangs / zombie thread** = a stalled IP-cam `read()` blocks the engine
  forever. Pass a `threading.Event` (stop_event); wrap `src.read()` in a 3s
  watchdog thread; Stop sets the event AND `thread.join(timeout=5)`. Verify a
  hung stream's thread actually dies and restart works.
- **Browser decode backlog** = per-message `createImageBitmap` piles up. Gate with
  a single in-flight flag; drop frames while decoding, keep newest only.
- **IP-cam "not connected"** = stale IP after changing WiFi. Phone + Mac must be
  on the SAME subnet; the URI is the phone's CURRENT LAN IP (e.g. 192.168.0.x on
  home WiFi, 172.20.10.x on iPhone hotspot) — not localhost. The app PULLS from the
  phone; bind server to 0.0.0.0 only if you also want phone-side control.

## File-source browser upload (loopback) — see references/file-source-upload.md
For a localhost webapp the detection engine (server-side Python) CANNOT read a
browser-picked `File` object by path. The fix is a loopback UPLOAD, not a path:
- Show `<input type="file" accept=".mp4,.mov,..">` when source=`file`; keep the text URI input for camera sources.
- On change: `fetch('/api/upload', {method:'POST', body: FormData with the file})`.
- Server saves to `media/<sanitized>` and returns the absolute path.
- Start feeds that saved path to `cv2.VideoCapture` (same `FileSource` pipeline).
- Default File `loop=True` so a movie behaves like a continuous live feed.
- Reject non-video extensions server-side (don't trust the client).
This keeps the app fully offline (loopback, no internet).

## Custom training (teach new classes) — see references/yolo-training.md
For a non-ML operator: fine-tune from `yolov8n.pt` (150-500 imgs/class), TWO modes —
(a) **Add to COCO**: retrain from base with extended class list (keeps all 80 + new;
you cannot append a class to a .pt, it's a retrain); (b) **New class only**: fresh model
with just engineering classes (hardhat/vest/crack/valve/fence-gap) for clean inspection.
Introspect `model.names` to show existing classes; if target already in COCO (e.g. bird),
don't train it. Labeling = the real work (~90% effort): LabelImg (local/offline) or
Roboflow (cloud/auto-assist); each image gets a sibling `.txt` with fractional bbox.
Incorporate labeling INTO the app via an "AI Learning" button (live feed + folder, draw
box, save `img.jpg`+`img.txt`). Aggressive AUGMENTATION at save: 1 taught image -> 10-15
variants (flip/brightness/rotate/scale), each with TRANSFORMED `.txt` coords. Train:
`yolo train model=yolov8n.pt data=<ds>/data.yaml epochs=50` -> `.pt` into `skills/`.
Mac MPS trains but slower than Colab for big datasets.
**Concrete impl (endpoints, canvas box-draw, pure-numpy augmentation, MPS call): see
references/active-learning-impl.md. Augmentation bbox-transform math: see references/yolo-training.md.**

## Verification (ad-hoc, no suite) — see references/verification.md
- Synthetic-frame pipeline test (FakeSource yields zeros) proves wiring without a camera.
- Direct `cap.read()` from the real stream URL + `det.infer()` on a saved frame proves
  the live path. Vision tool may be 404 (outage) — fall back to running YOLO on the
  saved frame and reading class/conf text output.
- Confirm `viewer.encode()` returns bytes starting with `\\xff\\xd8` (valid JPEG).

## References
- references/pitfalls.md — detailed fixes for the gotchas above.
- references/streaming-stability.md — concrete code for anti-lag canvas, 0.5s box-hold overlay, hardened streaming-Stop, decode-gate, IP-cam connectivity.
- references/aspect-ratio-ui.md — contain/letterbox canvas draw, box-overlay + learning-label math against the contained rect, floating collapsible sidebar (fixes video distortion that also corrupts training labels).
- references/file-source-upload.md — loopback upload recipe (server endpoint + browser picker + loop default) for using a movie/file as a source.
- references/yolo-training.md — custom YOLO training for a non-ML operator: fine-tune vs from-scratch, Add-to-COCO vs New-class-only, LabelImg/Roboflow, in-app "AI Learning" mode, 1->10-15 augmentation, bbox-transform math, data.yaml + train command.
- references/active-learning-impl.md — CONCRETE in-app learning impl: learn/ module split, /api/learn/* endpoints, canvas box-draw + normalized-box math, 15-op pure-numpy augmentation list, scale>1 crop-center fix, MPS train call.
- references/verification.md — ad-hoc verification pattern (venv python, Flask test_client, terminate-with-stop_event, node --check for inline JS, temp-script hygiene).
- references/ui-shell-toggle.md — floating control panel; minimize-toggle MUST be JS-driven (CSS sibling-selector trap) + collapsed reopen pill; LunaV glass shell tokens.
- templates/detect_skeleton.py — minimal 4-layer scaffold to copy-modify.
