# Cross-engine frame bleed + silent "already-running" stall

The headline bug this session (commit d383548): user reported "runs a video you didn't
load" AND "stop → reset → load new video → stall, unable to load." Both trace to the
engine/WS queue plumbing, NOT media clutter.

## Root cause (two coupled defects)

Frames/dets go into GLOBAL queues (`frame_q`, `det_q`) in `app.py` with NO ownership
token. Any live engine thread pushes into them, and the browser renders the newest
frame, so a stale/wedged engine's feed shows as "a different video."

1. **Silent start refusal.** `/api/start` early-returned `{"ok":False,"msg":"already running"}`
   if a previous engine thread hadn't fully died → new upload never loaded (silent stall).
2. **Split gen filter = total stall.** The WS pump read `current_gen["n"]` while `/api/start`
   bumped `engine_gen["n"]` — TWO separate dicts. After the first run `current_gen` sat at 0
   while engines stamped gen≥1, so EVERY frame failed the filter → blank feed. This alone
   reproduces "unable to load."
3. **No gen stamping.** Queue items were bare `jpg` / det-list; nothing tied a frame to its
   engine, so even a correct pump couldn't drop stale frames.
4. **Frontend hid the error.** `fetch('/api/start')` ignored the response and set status
   "running" blindly, so a rejection looked like a hung load.

## Fix shape (merged in d383548)

- ONE shared `engine_gen = {"n": 0}` dict used by start, stop, the engine thread, AND the pump.
- Stamp every push: `detect/main.py` does
  `frame_q.put_nowait((gen, jpg))` and `det_q.put_nowait((gen, [...]))`,
  where `gen = config.get("gen", 0)` (set in `/api/start` as `config["gen"] = my_gen`).
- Pump (`app.py` `@sock.route("/ws")`) only forwards items whose `item[0] == engine_gen["n"]`;
  stale (other-gen) or malformed items are dropped.
- `/api/start` bumps `engine_gen` BEFORE building config and, if a prev thread is alive,
  calls `_teardown_engine()` FIRST (no early return). New video always loads.
- `/api/stop` advances `engine_gen["n"]` (drops in-flight frames) + joins + clears uploads.
- Frontend start handler reads the JSON response and shows the real `msg`/error; stop handler
  reads `uploads_cleared`.

## Verification — reproduce BOTH symptoms, then prove fix

Run against the LIVE server (kill stale first: `pkill -9 -f "app.py"; sleep 1`). Needs
`websocket-client` (in .venv) and the Flask server up on :8000.

### Test A — cross-engine bleed (the "different video" symptom)
```python
import requests, websocket, json, time, sys
sys.path.insert(0, '/Users/kamarulhk/luna-edge')
from app import frame_q, det_q, _teardown_engine
BASE="http://localhost:8000"
S1="media/samples/WhatsApp_Video_2026-01-15_at_10.48.20.mp4"
S2="media/samples/dji_fly_20260805_165520_704_1785920249496_quickshot.mp4"
def up(p): return requests.post(f"{BASE}/api/upload", files={"file":open(p,"rb")}).json()
def st(u): return requests.post(f"{BASE}/api/start", json={"source":{"kind":"file","uri":u,"loop":False},"skill":"coco","conf":0.3,"geo":{"kind":"none"}}).json()
_teardown_engine(); frame_q.queue.clear(); det_q.queue.clear()
up(S1); up(S2)
a=st(S1); ga=a["gen"]
b=st(S2); gb=b["gen"]            # start B WITHOUT stopping A
assert b["ok"] and gb!=ga        # B must not be refused as "already running"
ws=websocket.create_connection("ws://localhost:8000/ws", timeout=15)
gens=set(); t0=time.time()
while time.time()-t0<8:
    try:
        m=ws.recv()
        if isinstance(m,bytes): continue
        gens.add(json.loads(m).get("gen"))   # det msg is a JSON ARRAY of objects
    except Exception: break
ws.close()
assert ga not in gens, f"STALE ENGINE {ga} BLED THROUGH (original bug!)"
assert gb in gens, "new engine produced no dets"
print("CROSS-ENGINE BLEED TEST: PASS")
```
A pre-fix run shows `ga` (the old engine) appearing in `gens` → bleed. Post-fix: only `gb`.

### Test B — real user flow (run A → stop → load new B → must not stall)
Same imports. Start A, sleep 4s, stop, upload+start B. Assert B streams frames
(`ws.recv()` returns bytes), `ga` never appears, `gb in gens` and `dets>0`. Pre-fix,
`/api/start` for B returns `"already running"` and no frames arrive.

### Gotcha: detection-message shape
The pump sends `ws_conn.send(json.dumps(d[1]))` where `d[1]` is the LIST of detections,
so each det WS message is a JSON **array**, not an object. Parse with `arr=json.loads(m);
if isinstance(arr,list): for o in arr: o.get("cls")`. A test that calls `json.loads(m).get(...)`
on an array silently yields `gens=set()` even when frames are flowing — that is a TEST bug,
not an app bug. Always count binary frames separately as the primary "feed works" signal.

### Gotcha: model-load latency
`/api/start` returns `running:True` instantly but `yolov8n` takes ~6s to load before the
first frame. Wait ≥10s before asserting frame count, or a healthy feed reads as dead.
