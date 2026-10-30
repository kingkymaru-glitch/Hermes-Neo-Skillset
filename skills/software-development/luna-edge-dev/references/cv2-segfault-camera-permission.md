# cv2 segfault (Apple Silicon) + macOS camera-permission diagnostic

Two distinct "Luna EDGE shows no video / crashes on Detect" root causes that this
session proved against the live Mac. Keep them separate in your head:

- Whole Flask server dies with exit 139 the instant detection starts  → cross-thread
  `cap.release()` SIGSEGV (SKILL.md pitfall #17). Code bug, fixed in 61aa1d8.
- Server runs fine but webcam never delivers a frame → macOS Camera permission
  denied to the terminal app (SKILL.md pitfall #19). OS grant, NOT a code bug.

## A. How the segfault was found — `faulthandler` recipe

Native C-level crashes (SIGSEGV) print NOTHING in Python tracebacks — the process
just dies with 139. To get a C backtrace at the exact crashing line, enable
`faulthandler` BEFORE importing cv2 / starting threads, and (optionally) schedule a
timed dump so even a hang prints a stack:

```python
import faulthandler, signal
faulthandler.enable()
# if the process wedges instead of crashing, dump a traceback after N seconds:
faulthandler.dump_traceback_later(20, exit=True)   # forces a trace + exit on hang
# also catch SIGSEGV explicitly (faulthandler already installs a handler, but be explicit):
# faulthandler.enable() covers SIGSEGV/SIGFPE/SIGABRT automatically
```

Run the engine directly (bypass Flask) to isolate:
```bash
cd ~/luna-edge
"$HOME/luna-edge/.venv/bin/python" -X faulthandler -u - <<'PY'
import faulthandler; faulthandler.enable()
from detect.main import run
run()   # drive with a real /api/start-equivalent config
PY
```
This session, the dump landed in `detect/sources/base.py:30` (`self.cap.read()`)
with the caller in `detect/main.py` `watchdog_loop` at the `s.release()` line —
proving a **different thread releasing the cap while `read()` was in flight**.

## B. Root cause + the shipped fix (commit 61aa1d8)

Cause: `watchdog_loop` called `src.release()` / `cap.release()` from a thread
while the capture thread was blocked inside `cv2.VideoCapture.read()`. Apple
Silicon AVFoundation is NOT thread-safe for that → native SIGSEGV kills the
process. (Pitfall #14's 2026 claim that cross-thread release "unblocks a wedged
read()" is wrong on this hardware.)

Fix shape (what shipped):
- `detect/main.py` `watchdog_loop()` → PASSIVE: only logs/flags a stall, never
  calls `release()`.
- `detect/sources/base.py` `read()` → guard: `if self.cap is None or not
  self.cap.isOpened(): return None`. `release()` also None-safe.
- Capture thread owns the cap, detects `None`/stall, rebuilds+reconnects the
  source on `None`. No other thread touches the cap.
- `det_fps` parsing: `"max"`/non-numeric/empty → `0` (unlimited); only real
  numbers go through `float()` (fixes the `float("max")` ValueError).

Verification after the fix: run `run()` with faulthandler and confirm the process
stays alive (`still alive: True`) and no segfault — that proves the crash is gone.
(End-to-end frames still require pitfall #19's camera grant.)

## C. macOS Camera permission diagnostic (pitfall #19)

Symptom: `cv2.VideoCapture(0).isOpened()` is `True`, but `.read()` returns
`ok=False` indefinitely — OR `.read()` *hangs* (blocks) instead of returning.
`system_profiler SPCameraDataType` shows the camera present; `lsof -i:8000` / `ps`
show no other process holding it.

This = the terminal app (Terminal.app or iTerm) that launched the venv Python is
NOT granted Camera access. macOS grants camera to the PARENT APP, not the python
binary, and AVFoundation silently withholds frames (rather than erroring) when
unauthorized.

Definitive probe (hard-timed so it can't hang your turn — run in background or
with `signal`-based timeout):
```python
import cv2, time
c = cv2.VideoCapture(0, cv2.CAP_AVFOUNDATION)
print("isOpened:", c.isOpened())          # True even when denied
ok, frame = c.read()
print("read ok:", ok, "frame is None:", frame is None)   # False / None => denied
c.release()
```
If `isOpened=True` but `read()` never yields a frame, it is permission, NOT code.

Fix (USER action, not code):
- System Settings → Privacy & Security → Camera → ensure the terminal app
  (Terminal / iTerm) is ON.
- If already on, toggle OFF then ON, quit & relaunch the terminal, then launch
  Luna EDGE once so the permission prompt appears and allow it.
- After granting, restart Luna EDGE (kill stale `app.py` first — see pitfall #7),
  hard-refresh R-Tessera, toggle CCTV + Detect.

Note: earlier this session video worked, then stopped — permission state changed
out from under a working engine. Always rule this in/out before touching engine
code when "no video" is reported.
