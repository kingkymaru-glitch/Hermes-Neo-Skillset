# File-source URI leak — "local file processing not working"

## Symptom
User selects Source = File, picks a video, hits Start → feed frozen/blank, no
detections. Looks like "file processing is broken" but detection pipeline is fine.

## Real root cause (from launch.log)
Repeated traceback: `RuntimeError: File not opened: 0` raised in
`detect/sources/base.py` `FileSource.__init__` (cv2.VideoCapture("0") fails).
The frontend sent `{source:{kind:"file", uri:"0"}}` — the webcam index, NOT a
path. Switching the `#source` dropdown to "file" only *hid* the `uri` text input;
it never cleared its value, so the camera index `"0"` stayed in the hidden field.
The Start guard only blocked an *empty* string, so `"0"` passed through to the
engine, crashed the engine thread, and the WS loop never started → blank feed.

## Why it reproduced intermittently
When the upload `fetch` resolved, onchange set `uri` to the server path and it
worked. But if the user switched source back/forth, or clicked Start before the
async upload settled, `uri` reverted/held `"0"` → crash. 6+ crashes in launch.log.

## Fix (committed ef518ad)
Frontend (`templates/index.html`):
- `syncSourceUI()` clears `document.getElementById('uri').value=''` (and
  `fileReady=false`) when leaving File, so a camera index can't leak forward.
- `fileReady` flag set `true` only inside the upload `.then()` after a real
  upload; Start guard requires `isFile && uri && fileReady` (was only `!uri`).

Backend (`app.py`):
- `/api/start` rejects `kind:"file"` with missing/non-existent path up front:
  `if not uri or not os.path.isfile(uri): return jsonify(ok:False,"upload a video file first")`
  — clear error instead of a silent dead engine.
- `pump()` wraps `run()` in `try/except Exception as e: _state["error"]=str(e)`
  (print it too). `/api/status` now returns `{running, error}`. `_state["error"]`
  cleared to None at the top of every successful start so stale errors don't linger.

## Verification recipe (headless — no display)
```bash
cd ~/luna-edge && source .venv/bin/activate
pkill -f "luna-edge/app.py"; python app.py &   # or exec via background
sleep 4
# (1) the OLD broken call must now be REJECTED, not crash:
curl -s -X POST localhost:8000/api/start -H 'Content-Type: application/json' \
  -d '{"source":{"kind":"file","uri":"0"},"skill":"coco","geo":{"kind":"none"}}'
# -> {"ok":false,"msg":"upload a video file first"}
# (2) real file via upload, then start:
RPATH=$(curl -s -X POST localhost:8000/api/upload -F "file=@media/<name>.mp4" \
  | python3 -c "import sys,json;print(json.load(sys.stdin)['path'])")
curl -s -X POST localhost:8000/api/start -H 'Content-Type: application/json' \
  -d "{\"source\":{\"kind\":\"file\",\"uri\":\"$RPATH\",\"loop\":true},\"skill\":\"coco\",\"geo\":{\"kind\":\"none\"}}"
sleep 4; curl -s localhost:8000/api/status   # -> {"error":null,"running":true}
# (3) prove frames actually flow over the WS (the "processing works" proof):
python - <<'PY'
import time
from websocket import create_connection   # pip install websocket-client if missing
ws=create_connection('ws://127.0.0.1:8000/ws'); ws.settimeout(0.5)
f=d=t0=0,time.time()
while time.time()-t0<6:
    try:
        m=ws.recv()
        if isinstance(m,(bytes,bytearray)): f+=1
        else: d+=1
    except Exception: pass
ws.close(); print('WS_FRAMES',f,'WS_DETS',d)
PY
# expect ~100 frames / ~250 dets in 6s for a real video.
```
Also: `curl -s localhost:8000/ | grep -c fileReady` (expect 4) and `node --check`
on the extracted `<script>` body to confirm no JS syntax regression.

## General lesson (reuse for any source-type)
When a dropdown has a shared hidden `uri` field across source kinds, clearing the
field on `syncSourceUI` is mandatory — a stale value from another kind will leak
into the engine. And any engine started in a thread MUST surface startup failures
via status, or the UI silently shows nothing.
