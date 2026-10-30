# In-app Active Learning — concrete implementation (Luna-EDGE)

The `edge-ai-vision` SKILL.md describes the "AI Learning" UX. This file is the
reusable implementation detail that actually shipped and was verified. Copy-modify
from here; it is source-agnostic and library-light (pure numpy + cv2, NO albumentations).

## Module split (server-side, Python)
- `learn/__init__.py` holds: `save_capture(img, boxes, class_id)` (writes 1 original
  + N augmented images + `.txt`), `current_model_classes()` (reads `model.names`),
  `build_dataset(class_names, mode, dataset_name)` (writes `data.yaml` + train/val split),
  `train(dataset_name, epochs)` (ultralytics, MPS). `ROOT` is the repo dir; subdirs
  `learn/capture`, `learn/datasets/<ds>`, `learn/runs`, `skills`.
- Class list is OPEN: a `learn/datasets/<ds>.classes.json` file is the source of truth.
  `save_capture` appends the class name if new and returns its index as `class_id`.
  NEVER hardcode class names in the UI — the operator types any string.

## Endpoints (Flask)
- `GET /api/learn/classes` -> `{"classes": model.names list}`.
- `POST /api/learn/capture` body JSON `{"image": <dataURL or base64>, "box":[cx,cy,bw,bh]
  (0..1 normalized), "class_name": <str>, "dataset": <str>}`. Server base64-decodes the
  image, `cv2.imdecode`, calls `save_capture`. Returns `{"saved": <count>}`.
- `POST /api/learn/train` body `{"dataset","mode":"custom"|"coco_ext","epochs":int}`.
  Builds dataset, trains, copies `learn/runs/<ds>/weights/best.pt` -> `skills/<ds>.pt`.

## Browser learning mode
- Header "AI Learning" button toggles a panel + `canvas.classList.add('learning')`
  (crosshair cursor).
- Box draw = mousedown/move/up on the canvas; store `drawBox={x,y,w,h}` in CANVAS px.
  Convert to normalized on save: `normBox = [ (x+w/2)/cw, (y+h/2)/ch, w/cw, h/ch ]`.
  Map client coords to canvas px via `getBoundingClientRect` scale factor
  (`(e.clientX-rect.left)*(canvas.width/rect.width)`).
- Save: `canvas.toDataURL('image/jpeg',0.85)` -> send as the image. Require a live
  frame (`latestBitmap` set) i.e. a source must be Started first.
- Show the drawn box live via a positioned `<div class="lbox">` overlay (pointer-events:none).
- Train: show "training… (minutes)" and disable nothing; poll the response.

## Augmentation (pure numpy + cv2, 15 ops -> 16 files per capture)
`AUG_OPS = [flip_h, flip_v, rot90_cw, rot90_ccw, rot15, rot-15, rot30, rot-30,
scale08, scale12, bright_up, bright_dn, contrast_up, contrast_dn, blur]`.
Pixel ops (bright/contrast/blur) do NOT move boxes. Geometry ops DO — see the
transform math in references/yolo-training.md section "Augmentation bbox transform math".
**Bug caught + fixed:** `scale12` (1.2x) produces an image LARGER than canvas ->
broadcast error. Fix: for s>1, resize up then CROP CENTER back to original size, and
transform the box center by the same `(0.5+(c-0.5)*s)` rule (clamped).

## MPS training note (verified)
`ultralytics 8.4.117`, torch 2.8, Apple M1 Pro: `model.train(data, epochs=50,
imgsz=640, device="mps" if torch.backends.mps.is_available() else "cpu",
project=learn/runs, name=dataset, exist_ok=True)`. For a tiny 2-image synthetic set,
2 epochs completed in ~25s and produced a valid `skills/<ds>.pt` (6.2 MB). Real
datasets (150+ imgs) take minutes per epoch on MPS — fine, just tell the user.
`Overriding model.yaml nc=80 with nc=1` is expected for custom mode.
