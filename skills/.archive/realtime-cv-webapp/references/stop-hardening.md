# Stop-Hardening for Real-Time CV Engines (blocking-read safe)

Problem: a Stop endpoint that only flips `running=False` does NOT terminate the
engine thread when the capture source stalls. `cv2.VideoCapture.read()` on a flaky
IP cam / S22-over-WiFi can block forever; the loop never re-checks the flag, so
the thread lives on, holds the camera, and a second Start double-spawns.

## Engine side (`detect/main.py`)
- Accept `stop_event: threading.Event` in `run()` (default `threading.Event()`).
- Both loops: `while stop["go"] and not stop_event.is_set():`
- Wrap the source read in a watchdog so a hung read can't defeat the Event:
  ```python
  READ_TIMEOUT = 3.0
  def safe_read():
      result = [None]
      def _r():
          try: result[0] = src.read()
          except Exception: result[0] = None
      t = threading.Thread(target=_r, daemon=True); t.start()
      t.join(READ_TIMEOUT)
      return result[0] if not t.is_alive() else None
  ```
- `finally:` set `stop_event`, `cap_t.join(timeout=2)`, `inf_t.join(timeout=2)`, `src.release()`.

## Server side (`app.py`)
- Store `stop_event` per-run in shared `_state`.
- `/api/stop`: `stop_event.set()` then `thread.join(timeout=5)`; WARN if still alive.
- `/api/start` while running: return `ok:false, "already running"` (guard double-spawn).

## Verification (proves it, not HTTP 200)
Run with the project's VENV python (has flask + cv2). Monkeypatch a hung source:
```python
import sys, time, threading
sys.path.insert(0, "/Users/kamarulhk/luna-edge")
import detect.main as M, app as A

class Hung:
    def read(self): time.sleep(3600)   # simulates stalled IP cam
    def release(self): pass
M.build_source = lambda *a, **k: Hung()
class FD:
    def infer(self, f): return []
M.YoloDetector = lambda *a, **k: FD()
M.build_geo = lambda *a, **k: None
class FS:
    def emit(self, d): pass
M.StdoutSink = FS; M.build_sink = lambda *a, **k: FS

A.app.testing = True
c = A.app.test_client()
c.post("/api/start", json={"source":{"kind":"ipcam","uri":"http://x/video"},"skill":"coco","geo":{"kind":"none"}})
time.sleep(1.0)
c.post("/api/stop"); time.sleep(6)
st = c.get("/api/status").get_json()
th = A._state.get("thread"); alive = th.is_alive() if th else False
ok = (not st["running"]) and (not alive)
c.post("/api/start", json={...}); time.sleep(1.0)   # restart must succeed
print("PASS" if ok and c.get("/api/status").get_json()["running"] else "FAIL")
```
If it prints PASS: Stop kills a stalled engine AND restart is clean. HTTP 200
alone is insufficient — the thread can be state-flagged stopped yet still alive.
