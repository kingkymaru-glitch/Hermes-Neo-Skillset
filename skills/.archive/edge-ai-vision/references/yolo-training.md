# Custom YOLO training for a non-ML operator (Luna-EDGE "AI Learning" mode)

How to teach the detector a NEW class (monkey, bird, hardhat, crack, ...) — explained
for a founder who runs the app but doesn't write ML code. Mechanics, not hype.

## How YOLO "learns" a class
YOLO is trained on a DATASET: images + a bounding-box label per object. It adjusts
internal weights to map visual patterns -> class name. NOT "show one picture".
- **Fine-tune (use this):** start from pretrained `yolov8n.pt`, add new class(es) on top.
  Needs ~150-500 images/class (variety > count). Far cheaper than from-scratch.
- **From scratch:** needs thousands/class. Overkill. Don't.

## Two train modes (offer both in the UI)
- **(a) Add to COCO:** retrain from `yolov8n.pt` with an EXTENDED class list
  (all 80 COCO classes + your new class). Keeps person/car/bird AND gains monkey.
  NOTE: you cannot "append" a class to a .pt — the output layer is fixed-size.
  "Add to existing" == RETRAIN from base with the longer list. That's fine, just know it's a retrain.
- **(b) New class only:** train a FRESH model with JUST your engineering classes
  (e.g. hardhat, vest, crack, valve, fence-gap). No person/car. For inspection where
  you only want asset items detected — faster + cleaner. Use when the 80 COCO classes
  are noise for the job.

## Introspect existing classes first
Loaded model exposes `model.names` (dict {id: 'class'}). Show this list in the UI so
the operator sees what already exists. If the target is ALREADY in COCO (e.g. `bird`,
id 14), DON'T train it — just keep using the coco skill. Only train what's genuinely new.

## Labeling (the real work, ~90% of effort)
Each image `monkey001.jpg` needs sibling `monkey001.txt` with one line per object:
`class_id center_x center_y width height` — ALL as fractions (0-1) of image size,
NOT pixels. A labeling tool computes these from your drawn box; you never type numbers.
- **Local (private, offline): LabelImg** — opens each image, preset class list, drag a
  box, auto-saves `.jpg`+`.txt`, Next/Prev. Matches "offline-first". Best default.
- **Roboflow (cloud, auto-assist):** same UI + AI box suggestions + auto-augment, but
  images leave the machine. Use only if privacy allows.
- **Semi-auto (2nd pass):** after a first rough model (even 50 hand-labeled imgs), run it
  over remaining images; it draws boxes, you ACCEPT/FIX. You verify instead of drawing.

## Incorporate labeling INTO the app (best UX — Luna-EDGE "AI Learning" button)
Reuse the live canvas + frame stream. Learning mode:
- shows current model class list (from `model.names`),
- source = LIVE feed (draw box on a paused frame) OR folder of images (reuse upload),
- you draw a box + pick/type a class, click save -> writes `img.jpg`+`img.txt`,
- a Train button runs `yolo train` (MPS, offline) and drops `.pt` into `skills/`.
Auto-label is a LATER phase (needs a first model); v1 = you draw, app saves+augments.
Class names are OPEN (free text, a `<ds>.classes.json` is the source of truth) — never
hardcode them. See references/active-learning-impl.md for the endpoint + canvas-box-draw detail.

## Aggressive augmentation (1 taught image -> 10-15 dataset rows)
At save time, generate variants of each labeled image. Each variant gets its OWN `.txt`
with box coords TRANSFORMED to match (flip -> mirror x; rotate -> rotate corners; etc).
Cheap set, all offline:
- horizontal flip + vertical flip
- brightness +/- , contrast +/-
- rotate +/- 15-25 deg
- scale / resize (random crop)
- (optional) slight blur / noise
Use albumentations, imgaug, or ultralytics' built-in `augment` param. Verify each
augmented `.txt` still encloses the object — a flipped box with un-mirrored coords is a
SILENT bad label.

### Augmentation bbox transform math (THE trap — get this right)
Box is normalized `[cx, cy, bw, bh]` (0..1). Apply the SAME transform to the box that
you apply to the image; here are the exact mappings (verified in Luna-EDGE):
- `flip_h`:  `[1-cx, cy, bw, bh]`
- `flip_v`:  `[cx, 1-cy, bw, bh]`
- `rot90_cw`:   `[cy, 1-cx, bh, bw]`   (center rotates; w/h SWAP)
- `rot90_ccw`:  `[1-cy, cx, bh, bw]`
- `rot±θ` (θ in deg): rotate center about image center (0.5,0.5):
  `dx,dy = cx-0.5, cy-0.5`; `nx = 0.5 + dx·cos - dy·sin`; `ny = 0.5 + dx·sin + dy·cos`;
  shrink box by `f = |cosθ| + 0.6·|sinθ|` (conservative, stays inside): `bw·f, bh·f`.
- `scale s` (0.8 or 1.2): `ncx = 0.5+(cx-0.5)·s`, `ncy = 0.5+(cy-0.5)·s`, `bw·s, bh·s`,
  all clamped to [0.01, 1.0]. For s>1 the image is cropped back to original size, so the
  box center shifts by the same rule and is clamped.
- brightness/contrast/blur: box UNCHANGED.
ALWAYS clamp every coord to 0..1 and drop a variant if its box shrinks below ~0.01.
In Luna-EDGE the pure-numpy implementation lives in `learn/__init__.py`
(`_bbox_after_transform`); copy it rather than re-deriving — sign errors here produce
labels that look fine but train garbage.

### No augmentation library? Pure numpy + cv2 works
If `albumentations`/`imgaug` aren't installed (they weren't in luna-edge's venv), implement
the 15 ops above with `cv2.flip`, `cv2.rotate`, `cv2.warpAffine` (rotations), `cv2.resize`+
center-crop (scale), `cv2.convertScaleAbs` (brightness/contrast), `cv2.GaussianBlur`. No
extra dependency, fully offline. See references/active-learning-impl.md for the exact op list
and the scale>1 crop-center fix.

## Dataset layout
```
learn/
  capture/        # raw labeled images + .txt
  datasets/
    coco_ext/     # images/ + labels/ + data.yaml   (mode a)
    custom/       # images/ + labels/ + data.yaml   (mode b)
  runs/           # trained weights
skills/           # final .pt dropped here (monkey.pt, sitesafe.pt)
```
`data.yaml`: `path: ..`, `train: images/train`, `val: images/val`,
`names: [person, ..., monkey]` (mode a) or `names: [hardhat, vest, crack]` (mode b).
Split ~80% train / 20% val (val held out to MEASURE accuracy — never train on it).

## Train command
`yolo train model=yolov8n.pt data=learn/datasets/coco_ext/data.yaml epochs=50`
(mode a) or `model=yolov8n.pt data=learn/datasets/custom/data.yaml` (mode b).
Output `.pt` -> copy to `skills/`. The Skill dropdown then lists it (detector is
source-agnostic, so it runs on S22/movie/webcam identically).

## Mac MPS caveat
Training runs on Apple Silicon but slower than Colab for big datasets. Small datasets
(few hundred imgs, few classes) train fine locally. For the engineering-inspection model
(few classes) it's quick.
