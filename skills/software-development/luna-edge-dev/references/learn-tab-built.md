# AI Learning tab — AS-BUILT (2026-08-14)

## Decision recap
- Founder: "different tab, not the same tab, but both on same LunaV EDGE." → `/learn` is a SEPARATE
  Flask route + `templates/learn.html`, same app as Detection. Detection (`index.html`) untouched.
- Founder UX question (Q1 freeze/label, Q2 MPS training speed): freeze/label is a FELT win
  (previously impossible to label moving video); MPS speed is INVISIBLE to the user and small data
  (5–20 imgs, 50 epochs) trains instantly on CPU → DROP MPS work. Invest only in front-end labeling +
  feedback. This is the durable heuristic: rank fixes by whether the USER feels them.

## Shipped (commit 8633271, branch main)
- `templates/learn.html` — 6-step gated UI. Left step-rail (lock-gating), top-bar nav
  `[AI Detection] href="/"` / `[AI Learning] href="/learn"`, LunaV glass tokens reused verbatim.
- `app.py` — ADDED only (Detection routes byte-for-byte unchanged):
  - `GET /learn` → serves `templates/learn.html`
  - `GET /api/media/list` → curated `media/samples/*.mp4` (flag `curated:true`) + uploaded `media/*.mp4`
  - `GET /api/learn/dataset/list?dataset=` → items with `boxes` (YOLO rows) + `url`
  - `GET /api/learn/dataset/classes?dataset=` → saved class list
  - `GET /api/learn/dataset/image?dataset=&file=` → sends the jpg
  - `POST /api/learn/dataset/delete` {file} → removes jpg+txt
  - `POST /api/learn/predict` {image:dataURL, dataset, conf} → runs ultralytics (trained `.pt` if
    exists else `yolov8n.pt`), returns `dets:[{name,conf,box:[x,y,w,h] normalized}]`
  - REUSES existing `POST /api/learn/capture` (augments ~16 frames, indexes class) and
    `POST /api/learn/train` (drops `.pt` into `skills/`).

## The freeze/label fix (key unlock)
Frontend ONLY — no new backend:
```
video.pause(); canvas.drawImage(video,0,0); const dataURL = canvas.toDataURL();
// draw box on canvas (mousedown/move/up), normalize to [cx,cy,w,h] via canvas.width/height
fetch('/api/learn/capture', {method:'POST', headers:{'Content-Type':'application/json'},
  body: JSON.stringify({image:dataURL, box:[nx,ny,nw,nh], class_name, dataset})})
```
Because draw + capture both happen on the paused frame and dataURL is grabbed immediately, box and
photo always agree. This REPLACES the design doc's proposed `/api/learn/frame/freeze` server route,
which was over-engineering.

## Step flow (gating)
1 Name → 2 Pick footage (curated clips thumbs + upload) → 3 Teach (freeze/box/save, "N taught" pill)
→ 4 Review (thumbnails, green "N box"/red "NO BOX", ✕ delete) → 5 Test (conf slider + predict, boxes
drawn on canvas) → 6 Train (button `disabled` until ≥5 boxed frames).

## Verification recipe that WORKED (localhost, headless)
Browser tool BLOCKS localhost → verify otherwise:
1. Served DOM: `curl -s http://localhost:8000/learn > /tmp/learn.html` then `grep` markers
   (`Your teaching path`, `freezeBtn`, `id="conf"`, `disabled=ready<5`, `href="/">`).
2. Exact frontend-path E2E (catches shell base64-quoting failures curl misses) — write to a .py file,
   run with `.venv/bin/python`, NOT `python -c '...'` (quoting breaks):
```python
import base64, requests
img = open('/tmp/frozen.jpg','rb').read()          # a real frame, e.g. cv2 grab from a sample clip
b64 = base64.b64encode(img).decode()
r = requests.post("http://localhost:8000/api/learn/capture",
                  json={"image":"data:image/jpeg;base64,"+b64,"box":[0.5,0.5,0.4,0.4],
                        "class_name":"bottle","dataset":"maru_demo"}, timeout=30)
print(r.status_code, r.text[:200])
l = requests.get("http://localhost:8000/api/learn/dataset/list", params={"dataset":"maru_demo"}).json()
print("count", l["count"])
# cleanup: rm learn/capture/maru_demo_*, learn/datasets/maru_demo*, skills/maru_demo.pt
```
3. Confirm server live: `curl -o /dev/null -w "/learn -> %{http_code}\n" http://localhost:8000/learn`
   and `/ -> %{http_code}` (Detection still 200).

## Restart-after-edit gotcha
After editing app.py: `PID=$(lsof -nP -iTCP:8000 -sTCP:LISTEN -t); [ -n "$PID" ] && kill $PID; sleep 1;
.venv/bin/python app.py > launch.log 2>&1 &` then `tail launch.log` for "Running on". Detection must
stay 200 after restart.
