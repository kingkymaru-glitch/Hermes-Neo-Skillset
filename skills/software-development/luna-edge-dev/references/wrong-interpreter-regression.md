# Wrong-Python server: ":8000 is up" is NOT "server works"

## The failure mode
A regression report ("it was working fine before, even for the SAME big files") where the
server responds on HTTP but uploads fail / runs never start. The process holding port 8000
was launched with the **WRONG Python interpreter** — e.g. Xcode's bundled system Python
(`/Applications/Xcode.app/.../Python3.framework/.../Python app.py`) which has **no torch /
ultralytics** — instead of `~/luna-edge/.venv/bin/python` (torch 2.8.0, MPS).

This server binds the port, serves the page (HTTP 200), but every engine route is dead:
- `/api/start` returns `{"ok":false,"msg":"upload a video file first"}` (or errors) because
  the YOLO import inside the engine thread throws `ModuleNotFoundError: No module named 'torch'`.
- `/api/upload` can return HTTP 000 (connection reset / route never completes) for bigger
  files — looks like "fails to upload most of the time."
- The user perceives this as laggy/failed upload + blank feed, even though the FILES and CODE
  are unchanged from when it worked.

## Why the obvious hypotheses were wrong (and cost a round)
Single-threaded dev server, CPU-only inference, and big-file synchronous save were ALL always
true — they do not explain a REGRESSION on identical inputs. The regression came from the
environment: a different interpreter now owns the port. Rule for regressions: suspect
interpreter / process / disk / stray-state BEFORE code logic.

## Diagnostic recipe (run when "worked before, now broken, same files")
```bash
# 1. Who holds the port, and with WHICH interpreter?
lsof -nP -iTCP:8000 -sTCP:LISTEN          # -> PID + COMMAND
ps -o pid,ppid,lstart,args -p <PID>        # -> shows the python binary path
#    GOOD: .../luna-edge/.venv/bin/python app.py
#    BAD : /Applications/Xcode.app/.../Python3.framework/.../Python app.py

# 2. Does that interpreter actually have torch?
<INTERPRETER-PATH> -c "import torch, ultralytics; print('ok')"
#    BAD -> ModuleNotFoundError: No module named 'torch'

# 3. What does the LIVE server actually do on start/upload?
curl -s http://localhost:8000/api/status
curl -s -o /dev/null -w "upload HTTP=%{http_code}\n" -F "file=@media/samples/<clip>.mp4" http://localhost:8000/api/upload
#    dead engine -> status running:false and upload HTTP=000 or non-2xx

# 4. Environment regression checks (independent of code)
df -h /Users/kamarulhk/luna-edge          # disk % — a full disk (92%+) can wedge saves
du -sh ~/luna-edge/media                  # leftover big files from prior runs
pgrep -af "app.py"                         # stray servers
memory_pressure | head                     # RAM pressure
```

## Fix
```bash
pkill -9 -f "app.py"                       # kill the wrong interpreter (NOT -f "luna-edge/app.py")
sleep 1; lsof -nP -iTCP:8000 -sTCP:LISTEN && echo STILL-UP || echo port-free
cd ~/luna-edge && source .venv/bin/activate && python app.py   # restart on the venv
# verify: ps args shows .venv/bin/python; /api/start returns ok:true and streams frames
```

## Prevention — IMPLEMENTED (2026-08-14)
- **Torch guard is LIVE at the top of `app.py`** (after `sys.path.insert`, before any
  other import). Exact form now in the file:
  ```python
  try:
      import torch  # noqa: F401
  except Exception as _te:
      sys.stderr.write(
          "\n[FATAL] Luna-EDGE requires torch (and ultralytics), but it is not "
          "importable in this Python interpreter:\n  %s\n"
          "You are almost certainly running app.py with the wrong 'python'.\n"
          "Fix: use the project venv, e.g.\n"
          "  cd ~/luna-edge && source .venv/bin/activate && python app.py\n" % _te)
      sys.exit(1)
  ```
  VERIFIED: running the real `app.py` under Xcode's Python 3.9 now prints the FATAL
  block and exits (exit 1) WITHOUT binding port 8000 — so the dead-server failure mode
  can never silently recur. The guard also breaks the earlier `timeout`/`exec` test
  tricks (use a real background launch + `sleep`, not `exec(open(...).read())` which
  breaks `__file__`).
- **Pin the launcher to the venv python.** A `launch.command` calling
  `~/luna-edge/.venv/bin/python app.py` (absolute path) prevents a bare `python`/`python3`
  on PATH from hijacking port 8000. Recommended next step if you haven't created it.
- **One-shot "is the live :8000 the right interpreter?" check** (run after any
  "serves but engine dead" report):
  ```bash
  P=$(lsof -nP -iTCP:8000 -sTCP:LISTEN -t); ps -o args= -p "$P"
  # expect: .../luna-edge/.venv/bin/python app.py   (NOT /Applications/Xcode.app/.../Python)
  ```
  If it shows Xcode Python → kill (`pkill -9 -f "app.py"`) and restart on the venv; the
  torch guard now makes the wrong one refuse to bind, so a clean restart is guaranteed venv.

## Cross-ref
Pitfall #7 (stale process serves old routes) and #8 (use venv python) are related but
distinct: #7 is about an OLD copy of YOUR code serving; this is about a DIFFERENT INTERPRETER
serving with no deps at all. Both prove "port 8000 responds" ≠ "server is correct".
