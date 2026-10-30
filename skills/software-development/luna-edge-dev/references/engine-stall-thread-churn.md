# Engine "works for hours then freezes" — thread churn + concurrent read (fixed 2026-08-14)

Symptom: Luna-EDGE detection ran fine for ~7 hours, then froze — the Flask shell still
served pages (`/api/status` returned `running:false`), but the engine produced no frames
and Start wouldn't recover.

## Root cause (two compounding flaws in the old `detect/main.py`)

```python
def safe_read():
    result = [None]
    def _r():
        try: result[0] = src.read()
        except Exception: result[0] = None
    t = threading.Thread(target=_r, daemon=True)   # NEW THREAD EVERY FRAME
    t.start()
    t.join(3.0)
    if t.is_alive():
        return None  # timed out -> thread STILL blocked inside cap.read()
    return result[0]
```

1. **Per-read thread churn** — a fresh daemon thread was created on every single frame read.
   Over hours that's hundreds of thousands of threads created/abandoned.
2. **Concurrent `read()` on one `cv2.VideoCapture`** — on a stalled camera read, the 3s timeout
   returned `None` but left the orphaned thread *still blocked inside `cap.read()`*, while the
   loop immediately issued another `read()` on the SAME capture object. Two threads racing one
   camera → undefined hang in the FFMPEG/AVFoundation backend. Classic "works for hours, then freezes."

## Fix (shipped commit 831c46c)

- ONE persistent capture thread does blocking reads into `cap_state = {"src": src, "last_ok": t}`.
- ONE watchdog thread force-releases `cap_state["src"]` after `STALL_TIMEOUT = 10s` with no new
  frame. Releasing from another thread makes a wedged `read()` return on FFMPEG/AVFoundation.
- The capture thread, on `None`/drop, calls `_rebuild_source()` — releases + reopens the source
  (recovers dropped IP-cam/network connections) — then sleeps 1s and retries.
- PTZ `set_target` hook must read `cap_state["src"]` (not the stale `src` local), and the
  `finally` block releases `cap_state["src"]`, never `src`.

Verification that it actually works (not just "server up"): restart on the venv, `POST /api/start`
on a `media/samples/*.mp4` with `loop:true`, then run the WS frame-counter from
`references/verify-live-ws.md`. Confirmed 208 binary frames + 469 detection msgs in 12s with real
YOLO hits (`person` 0.881/0.831).

## Interpreter red-herring (cost a wrong diagnosis this session)

The `ps -o args= -p <PID>` output shows `/Applications/Xcode.app/.../Python3.framework/.../Python app.py`
EVEN when the server is running on the correct venv. That's because this project's venv is built ON
Xcode Python 3.9 (`pyvenv.cfg` `home = /Applications/Xcode.app/.../usr/bin`, `version = 3.9.6`), so
`.venv/bin/python` resolves to the SAME framework binary — only `sys.path` differs. Bare Xcode
`python` fails `import torch`; the venv python imports it fine (same binary, different sys.path).

**Do NOT conclude "wrong interpreter" from `ps` args.** The authoritative check is whether torch is
actually mapped into the process:

```bash
P=$(lsof -nP -iTCP:8000 -sTCP:LISTEN -t)
lsof -p "$P" | grep -c 'site-packages/torch'   # >0 = torch loaded = correct venv
```

## Background rogue `.py` diagnostic (launchd KeepAlive respawn)

When a background `.py` "keeps coming back" after being killed, it is almost always a launchd
`RunAtLoad`+`KeepAlive` job. Find it:

```bash
launchctl list | grep -iE 'name'                    # is it launchd-managed?
ls -la ~/Library/LaunchAgents/                       # user agents
cat ~/Library/LaunchAgents/<label>.plist             # RunAtLoad / KeepAlive keys
```

This session the rogue was `com.kamarulhk.cursor-hy3-proxy.plist` (a Cursor-IDE proxy to
`tencent/hy3:free` on 127.0.0.1:8787) — unrelated to Luna-EDGE. Stop it permanently with
`launchctl unload ~/Library/LaunchAgents/com.kamarulhk.cursor-hy3-proxy.plist`. It is a long-lived
proxy, not a one-shot, so "kill after serving" doesn't apply — unloading the plist is the only
way to stop the respawn. `app.py` itself is NOT launchd-managed; it's started by `launch.command`
(`nohup python app.py &`), gets orphaned (PPID 1), and has no auto-respawn.
