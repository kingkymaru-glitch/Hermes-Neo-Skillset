# Luna-EDGE — live WebSocket frame verification

Headless end-to-end check that the engine actually produces frames + detections
over the browser WS path (the real "feed is working" bar, not just `running:True`).

## Hard gotcha — model-load latency (cost a false bug-read this session)
`/api/start` returns `ok:true` and `/api/status` shows `running:True, error:None`
**instantly**, but the engine does NOT push frames until `ultralytics` finishes
loading `yolov8n` on first run. On this Mac that warm-up is ~6 seconds. A
verification window shorter than that reports **0 frames** and looks like a dead
feed — it is NOT. Fix: wait 6–10s after `/api/start` before asserting frame count.

## Script (run inside ~/luna-edge/.venv)
Requires `websocket-client` (`pip install websocket-client`); already in the venv.
Connect, drain WS for N seconds, count binary frames + parse JSON detections.

```python
import requests, json, time, os
import websocket
base = "http://localhost:8000"
vid = os.path.abspath("media/<some>.mp4")   # or use ipcam/webcam uri
requests.post(base + "/api/start", json={
    "source": {"kind": "file", "uri": vid, "loop": True},
    "skill": "coco", "conf": 0.3})
frames, dets = [], []
ws = websocket.WebSocket(); ws.connect("ws://localhost:8000/ws"); ws.settimeout(0.4)
t0 = time.time()
while time.time() - t0 < 10:               # <-- 10s, not 4s (model warm-up)
    try:
        m = ws.recv()
        if isinstance(m, (bytes, bytearray)):
            frames.append(len(m))
        else:
            try: dets.append(json.loads(m))
            except Exception: pass
    except websocket.WebSocketTimeoutException:
        pass
    except Exception as e:
        print("recv err:", e); break
ws.close()
requests.post(base + "/api/stop")
print("frames:", len(frames), "bytes:", sum(frames),
      "det_msgs:", len(dets), "sample:", dets[:2])
```

Expected healthy output: `frames: 150+`, `bytes: several MB`, `det_msgs: 200+`
with real COCO classes in the sample. If `frames: 0` after a 10s window, THEN it's
a real fault (check `/api/status` error + `launch.log`).

## Detection message shape (WS text frame)
The text (non-binary) WS frame is a **JSON ARRAY of box objects**, NOT a dict —
`json.loads(m)` returns a list; calling `.get()` on it raises
`'list' object has no attribute 'get'`. Each box:
`{"cls": "person", "conf": 0.25, "bbox": [x, y, w, h], "lat": null, "lon": null}`
(`lat`/`lon` are null unless a GeoAdapter is active). To total detections across
the drain, iterate the list (`for b in (d if isinstance(d, list) else [])`), key on
`b["cls"]`, count `b["conf"]`/`b["bbox"]` as needed.

## Re-run hygiene
The `/api/upload` endpoint dedupes only on exact basename collision, so re-uploading
the same clip with a different suffix piles up byte-identical copies in `media/`.
They waste GBs but are harmless to the pipeline. Prune duplicates with:
`md5 -q media/*.mp4 | sort | uniq -c` (counts >1 = safe-to-dedup identical files).
Do NOT delete while a looped file-source run is live on one of them.
