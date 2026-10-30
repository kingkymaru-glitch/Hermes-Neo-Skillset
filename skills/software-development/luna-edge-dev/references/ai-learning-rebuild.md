# AI Learning Rebuild — plan & decisions (2026-08-14)

Design-only. Not yet built. Drives the replacement of the current `#learnPanel` training bench.

## Root problem (from user-session analysis)
Current Learning = draw box on a LIVE moving feed with NO pause. On a DJI clip the target moves every
frame; the box lands on empty road. Worse, a silent capture bug: box is measured at mouse-up but the
saved image is `canvas.toDataURL()` at click time (a later frame) → box saved against wrong pixels.
The only working path is Folder Learning (still images), but the user has no way to extract frames
from a video → dead end for non-technical field users.

## Architecture decision
- NEW separate tab/page, NOT a panel in the shared Detection canvas. Route `/learn`,
  `templates/learn.html`, own `static/learn.js`. Detection (`/`, `index.html`) left byte-for-byte
  unchanged. Each tab owns its own ws://, so no shared paint state. This is the safest way to avoid
  regressing the working detector.
- Backend reuse: `/api/upload`, `/api/learn/classes`, `/api/learn/capture`, `/api/learn/folder/*`,
  `/api/learn/train`. Extend `/api/start` to accept `{conf, single_frame:true}` for the compare step.
- New routes:
  - GET `/learn` → serve learn.html
  - POST `/api/learn/frame/freeze` → returns the exact last decoded frame as JPEG (so box+photo match)
  - GET `/api/learn/dataset/list` → all samples: thumb, class, bbox, status, per-class counts
  - POST `/api/learn/sample/edit` → redraw/relabel one sample
  - POST `/api/learn/sample/delete` → remove one sample
  - GET `/api/learn/review/check` → safe-train gate (warn if any class < N samples)
- Curated clips in `media/samples/` NEVER touched by labeling/auto-clear.

## Curriculum steps (1–8)
1 raw pixels/no AI · 2 draw box + label (frozen frame) · 3 model guess (boxes+conf, vs your box) ·
4 confidence slider (add conf param + UI) · 5 what it knows / can't see · 6 mistakes (force FP/miss) ·
7 teach (existing capture/augment/folder/train bench, step-gated) · 8 why edge (offline/private).

## UX principles (what makes it usable)
- Step banner "Step N of 8" + thin progress bar — ADHD-friendly "where am I".
- One action per screen; Train hidden until final step behind "Advanced" caret.
- Freeze + scrubber + zoom + Undo + pointer events (mouse AND touch for field/tablet).
- Right rail collapsible dataset browser: thumbnail strip, class counts, click-to-edit, delete.
- Plain-language copy; no "epochs/coco_ext/dataset" dumped up front.
- Class autocomplete + near-duplicate warn ("monky"≈"monkey").

## Dataset manager (prevents "wait until train to fail")
- Per-item feedback: after Save, thumbnail drops into rail with green ✓ (saved + N augmented) or red ✗
  with reason. No silent batching.
- Edit + delete per sample; no clear-all.
- Live class counts; review gate (accept/relabel/delete pre-train).
- Safe-train check: block Train if any class < 5 samples.
- Thumbnail = the ACTUAL captured frame (closes the freeze-frame mismatch bug).

## Don't over-invest
MPS training speed is invisible to user and labeling/training 5–20 imgs @ 50 epochs is already
near-instant on CPU. Felt UX is entirely front-end (freeze/scrub, step controller, dataset rail).
Apply MPS only if training *feels* slow later.

## Build phases (verify Detection still 200 + live boxes at every phase)
- P0 tab nav + /learn shell + shared LunaV CSS
- P1 clip upload + video + scrubber + FREEZE + draw + frame/freeze capture
- P2 dataset rail: list / edit / delete / counts / status badges
- P3 step controller + curriculum copy
- P4 compare (detection-on-frozen) + confidence slider
- P5 review gate + safe-train + Train wiring + post-train "run your model"
- P6 live e2e verify (upload → freeze → draw → capture → dataset/list shows sample with correct
  frame → edit → delete → train → safe-train blocks <5, passes on enough)

## Status
Approved in principle by founder (MARU) 2026-08-14. Not started in code.
