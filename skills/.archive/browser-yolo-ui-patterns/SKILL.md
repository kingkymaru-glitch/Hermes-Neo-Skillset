---
name: browser-yolo-ui-patterns
description: Canvas YOLO UIs — contain-rect, box mapping, teach loop.
---

# Browser YOLO UI patterns

Covers two reusable problems in browser-based detection webapps (localhost/edge,
offline-first):

1. **Drawing a video stream to a `<canvas>` without distortion**, and overlaying
   detection boxes (or capturing user-drawn boxes) at the *correct* coordinates.
2. **An in-app "teach the model" loop** — capture a labeled frame in the browser,
   augment it, and train a new YOLO weights file, all without leaving the app.

Both were battle-tested on the Luna-EDGE project (Flask + WebSocket + cv2 +
ultralytics). The mechanics are engine-agnostic.

## When to use
- A `<canvas>` shows a live camera/IP-cam/movie feed and you draw detection boxes
  on it (server-side or browser-side).
- Boxes look "off" / squashed / drift when the canvas shape ≠ video shape.
- You want users to label objects inside the app and produce a trained `.pt`.
- Lag grows over time on a streaming feed.

## Pattern 1 — contain-rect rendering (NO distortion)
The classic bug: `ctx.drawImage(bmp, 0, 0, canvas.width, canvas.height)` stretches
the frame to the canvas, squashing non-matching aspect ratios. Worse, if the user
*draws* a label box on that squashed canvas, the normalized coords are wrong →
**corrupted training data**.

Fix: compute a `contain` rect (letterbox) every paint, draw into it, and scale
boxes against it. Full math + a unit-test in `references/canvas_contain_rect.md`.
Sketch:

```js
function paint(){
  fitCanvas();
  if(latestBitmap){
    const fw = latestBitmap.width, fh = latestBitmap.height;
    const cw = canvas.width, ch = canvas.height;
    const scale = Math.min(cw / fw, ch / fh);      // contain, not stretch
    const dw = fw * scale, dh = fh * scale;
    const dx = (cw - dw) / 2, dy = (ch - dh) / 2;  // letterbox offset
    containRect = {x:dx, y:dy, w:dw, h:dh};
    ctx.fillStyle = '#000'; ctx.fillRect(0,0,cw,ch);
    ctx.drawImage(latestBitmap, dx, dy, dw, dh);
    const sx = dw / fw, sy = dh / fh;              // box scale vs contained rect
    for(const d of latestDets){ /* bx = dx + d.bbox[0]*sx ... */ }
  }
  requestAnimationFrame(paint);
}
```

**User-drawn box → normalized frame coords** must invert through `containRect`:
```
nx = (canvasX - containRect.x) / containRect.w   // then clamp 0..1
ny = (canvasY - containRect.y) / containRect.h
```
If you skip this, labels train on the warped canvas, not the real video.

## Pattern 2 — single in-flight decode gate (lag control)
A WebSocket/MJPEG feed can deliver frames faster than you can `createImageBitmap`.
Decode every frame and the queue grows → lag climbs forever. Gate it:

```js
let decoding = false;
function decodeNext(){
  if(!pendingBytes){ decoding = false; return; }
  decoding = true;
  const bytes = pendingBytes; pendingBytes = null;
  createImageBitmap(new Blob([bytes], {type:'image/jpeg'}))
    .then(b => { if(latestBitmap) latestBitmap.close(); latestBitmap = b;
                 if(pendingBytes) decodeNext(); else decoding = false; })
    .catch(() => { decoding = false; });
}
// onmessage: pendingBytes = ev.data; if(!decoding) decodeNext();
```
Only one decode runs at a time; we keep only the *newest* frame. Decode cost is
bounded to the paint rate → lag stays flat.

## Pattern 3 — in-app "teach the model" loop
The engine is server-side; the browser can't hand it a `File`. So labeling must
**upload** the captured frame (base64) to the server, which saves + augments.
Loopback upload (localhost) is instant, no internet.

Flow:
1. Browser: `canvas.toDataURL('image/jpeg', 0.85)` → POST `{image, box, class_name, dataset}`.
2. Server: save `img.jpg` + `img.txt` (YOLO format: `class_id cx cy w h`, all 0..1),
   then generate ~10–16 augmented copies (`flipH`, `flipV`, `rot90`, `bright`,
   `rot15`, `rot-15`, `scale08`, `scale12`, `blur`, `noise`) — each with its
   label transformed to match. Pure `numpy`+`cv2`, **no albumentations needed**
   (avoids an extra dependency). See `references/in_app_teach_loop.md`.
3. Train: `model.train(data=yaml, epochs=N, device=mps)` (Apple Silicon) → produces
   `runs/<ds>/weights/best.pt`; copy to `skills/<ds>.pt`.
4. UI lists current classes via `model.names` so the user sees what exists before
   adding (monkey = new; bird = already in COCO → don't retrain bird).

Two train modes:
- **custom** (new-class-only inspection): `data` has just the new classes.
- **coco_ext**: retrain from `yolov8n.pt` with `nc = 80 + new` (YOLO output layer
  is fixed-width, so "add a class" = retrain with extended list, not patch).

## Pattern 4 — freeze-frame label overlay (step-gated "teach" tab)
A common variant of Pattern 1: the user pauses a *playing* `<video>`, snapshots the
current frame to a frozen `<img>` (via an offscreen canvas `drawImage`), and draws a
label box on a `<canvas>` over it. Two bugs bite here that the live-stream pattern
doesn't:

**Bug A — the split-screen layout.** If `<img id=freezeImg>` and `<canvas
id=drawCanvas>` are *siblings in normal flow* (`display:block`), freezing stacks them
as two equal blocks: the frozen frame on top, the canvas (drawn black/empty) dropping
*below* it. The user ends up drawing on the detached lower block, not the image.
Fix: make the stage `position:relative` and **absolutely overlay** both the frozen
image and the canvas on the same box:
```css
.media-wrap { position: relative; }
#freezeImg, #drawCanvas { position: absolute; inset: 0; width: 100%; height: 100%; }
#freezeImg { object-fit: contain; }   /* keep aspect; letterbox, don't stretch */
```
Keep the `<video>` itself in flow (paused) so the `.media-wrap` keeps its height as
the anchor; only hide/overlay the frozen snapshot + canvas on top. (Hiding the video
with `display:none` collapses the wrapper to 0 height and the absolute canvas
vanishes.)

**Bug B — box drift (mouse CSS px ≠ canvas internal px).** The draw canvas internal
resolution = the video resolution (`cv.width = v.videoWidth`), but the mouse is read in
*displayed* CSS pixels. Drawing the box in raw mouse coords puts it in the wrong spot
on any non-native size (retina, smaller window, letterboxed clip). Fix: scale every
pointer coordinate through the rendered rect:
```js
function toCanvas(e){
  const r = cv.getBoundingClientRect();
  const sx = cv.width  / r.width, sy = cv.height / r.height;  // display→internal
  return { x: (e.clientX - r.left) * sx, y: (e.clientY - r.top) * sy };
}
```
Normalize for the API as before: `nx = (x + w/2)/cv.width`, etc. (Works for mouse
and touch — call `toCanvas` on both.)

**Affordance:** show an amber "⏸ Frozen — drag a box" badge on the frame while frozen
(`display:inline-flex`), hide it on play. It removes the "can I even draw here?" doubt.

Full worked snippet + the freeze/save flow in
`references/freeze_frame_label_overlay.md`.

## Pitfalls
- **Stretch = corrupt labels.** Never `drawImage` to full canvas w/h. Use contain.
- **Don't stack the canvas below the image.** Frozen-frame labeling needs the canvas
  *absolutely overlaid* on the frozen `<img>` (inset:0), not a sibling block — else
  you draw on a detached black area. Keep the video in flow as the height anchor.
- **Scale pointer coords to canvas-internal px.** Mouse is in CSS px; canvas is in
  video px. Multiply by `cv.width/getBoundingClientRect().width` or boxes drift.
- **Box scale must use the contained rect**, not canvas w/h, or overlays drift.
- **YOLO can't append a class.** Adding "monkey" means retrain with nc+1.
- **Augment flips must flip the label too** (`cx -> 1-cx` for horizontal). Forgetting
  this silently trains wrong boxes.
- **Don't require albumentations** — numpy/cv2 cover flip/bright/rotate/scale/blur.
- **Bind the server to 0.0.0.0** if you ever want phone-side control; localhost-only
  detection is fine on 127.0.0.1.

## Verification (no test framework in most of these repos)
Use a throwaway `hermes-verify-*.py` script run in the project venv, assert the
claims, then delete it. See `scripts/verify_contain_rect.py` for a reusable
deterministic probe of the label-mapping math.

## Support files
- `references/canvas_contain_rect.md` — full contain-rect math + box mapping + a
  worked example with letterbox offsets.
- `references/in_app_teach_loop.md` — augmentation recipe (1→16) with label
  transforms, Flask endpoint shape, and the yolo train command.
- `references/freeze_frame_label_overlay.md` — freeze-frame teach-tab overlay:
  absolute-inset layering fix, `toCanvas` coord-scaling, freeze badge, save flow.
- `scripts/verify_contain_rect.py` — deterministic unit check of canvas-px →
  normalized-frame-coord mapping (run in venv, then delete).

## Overlap note
Bundled skills `realtime-cv-webapp`, `local-vision-webapp`, and `edge-ai-vision`
cover the *streaming* side of this. This skill fills the gap they miss: undistorted
canvas rendering + correct box<->frame mapping, and the in-app label→train loop.
Curator may consolidate.
