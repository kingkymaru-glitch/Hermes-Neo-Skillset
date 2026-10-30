# Camera wedge + silent-zero-detection diagnostic (2026-08-26, commit d5f5ed0)

Three SEPARATE causes all look like "Detect button does nothing / no boxes":

| Symptom | Root cause | How to confirm | Fix |
|---|---|---|---|
| Stream flows, but NO boxes ever draw | ultralytics got a `FileNotFoundError` from a double `.pt` (e.g. `yolov8n.pt.pt`) → no model → silent 0 dets | Headless: `YoloDetector("yolov8n")` should print `MODEL LOADED OK`; if it raises, path is wrong | Pass BARE alias `"yolov8n"` (no `.pt`). Custom skills use `skills/<name>.pt` |
| `read()` returns `None` / HANGS; `isOpened()==True` | macOS Camera PERMISSION denied for the Terminal app (pitfall #19) | `system_profiler SPCameraDataType` shows camera; granting/regranting Camera for Terminal fixes it | User grants Camera in System Settings → relaunch Terminal |
| `read()` returns `None` FOREVER, but it WORKED earlier this session | `VDCAssistant` (root camera broker) WEDGED after repeated `kill -9` of app.py (pitfall #21) | `pgrep -fl app.py` CLEAR + `system_profiler` shows camera, yet no frame; only `sudo pkill VDCAssistant` frees it | User: quit & reopen Terminal, or `sudo pkill VDCAssistant`. Don't `kill -9` repeatedly |

## Exact headless probes (run from ~/luna-edge with the venv python)
# 1. Model-load check (no camera needed) — proves pitfall #20 fixed
```bash
cd ~/luna-edge
.venv/bin/python - <<'PY'
import sys; sys.path.insert(0,"detect")
from detector.base import YoloDetector
d = YoloDetector("yolov8n")          # bare name triggers auto-download
assert d.model is not None, "MODEL FAILED TO LOAD"
print("MODEL LOADED OK; class0 =", d.model.names[0])
PY
```
# 2. Camera-frame check (proves wedge vs permission) — run BEFORE trusting any start
```bash
cd ~/luna-edge
.venv/bin/python - <<'PY'
import cv2
cap = cv2.VideoCapture(0, cv2.CAP_AVFOUNDATION)
print("isOpened:", cap.isOpened())
ok, frame = cap.read()
print("got_frame:", ok)
cap.release()
print("RESULT:", "frames flowing" if ok else "NO FRAMES — wedge(permission ok earlier)/permission/device-locked")
PY
```
# 3. Live frames counter (after a clean start) — proves "delivering" not "stuck"
```bash
curl -s localhost:8000/api/status | python -m json.tool   # watch "frames" climb >0
```

## Engine code shape shipped (d5f5ed0)
- `_guarded_camera_read(cap, timeout=4.0)`: spawns a thread that does the `read()`
  and joins with a wall-clock timeout, so a denied/wedged camera returns
  `got_frame=False` instead of hanging the start call forever.
- `app.py /api/start` for a webcam source REJECTS with an actionable message when
  the guarded read yields no frame within the timeout (no silent dead engine).
- `detect/main.py` capture loop increments `_engine_stats["frames"]` at the real
  capture point; `app.py /api/status` surfaces it. Truthful even with no WS client.
- `detect/detector/base.py`: `coco` alias → `YOLO("yolov8n")` (bare). Custom skills
  still resolve `skills/<name>.pt`.

## Do NOT
- Append `.pt` to a known ultralytics built-in name (double extension → silent 0 dets).
- `kill -9` the engine repeatedly — it wedges VDCAssistant (pitfall #21). Use clean
  `kill -TERM` / launcher stop.
- Trust "video plays" as proof detection works — verify the model object loaded.
