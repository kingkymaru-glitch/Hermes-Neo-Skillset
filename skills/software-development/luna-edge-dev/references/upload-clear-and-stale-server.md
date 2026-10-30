# Upload auto-clear + stale-server-process (2026-08-13 session)

## Symptom that triggered the work
- `media/` had 18 files = only 4 unique (md5-verified). 14 were dupes from repeated
  `/api/upload` calls (each suffix-increment created a new file; engine only reads one).
- After adding a `clear_uploads()` hook to `/api/stop`, the FIRST live test still left the
  uploaded clip in `media/` after stop — and `/api/stop` returned the OLD shape
  `{'ok':True,'msg':'stopped'}` with NO `uploads_cleared` field.

## Root cause 1 — stale server process (the big one)
- My restart ran `pkill -f "luna-edge/app.py"`. The launch cmdline is `python app.py`
  (relative path, no `luna-edge/` prefix), so that pattern matched NOTHING. `pgrep -fa
  "luna-edge/app.py"` returned empty → I wrongly concluded port 8000 was free. But a
  PRE-EDIT `python app.py` was still alive, holding port 8000, serving the OLD `/api/stop`.
  New code never ran. This is a sharper form of pitfall #7 (template cache): the server
  process itself was stale.
- Fix/proof recipe:
  ```
  pkill -9 -f "app.py"            # matches `python app.py` cmdline
  sleep 2
  lsof -i:8000 | grep LISTEN      # MUST be empty before trusting restart
  (cd ~/luna-edge && source .venv/bin/activate && python app.py > launch.log 2>&1 &)
  sleep 4
  curl -s -o /dev/null -w "HTTP %{http_code}\n" http://localhost:8000/
  ```

## Root cause 2 — atexit does not fire on signal kill
- `clear_uploads()` registered via `atexit`. On SIGTERM (`kill -TERM <pid>`) the uploads
  were NOT cleared — `atexit` handlers don't run when a process is terminated by a signal.
- Fix: bind signal handlers explicitly:
  ```python
  import signal, sys
  def _on_exit_signal(signum, frame):
      try: clear_uploads()
      finally: sys.exit(0)
  signal.signal(signal.SIGTERM, _on_exit_signal)
  signal.signal(signal.SIGINT,  _on_exit_signal)
  ```
- Now cleanup runs on all three exit paths: `/api/stop`, normal exit (`atexit`), and kill
  (signal handlers).

## The feature (what landed in app.py, commit f69fd13)
- `clear_uploads()` deletes every `*.mp4/.mov/.avi/.mkv/.webm` DIRECTLY in `media/`.
  It skips subdirectories, so `media/samples/` (curated DJI/WhatsApp test clips) is never
  touched. Returns count removed.
- `media/samples/` = permanent curated footage. `media/` root = session uploads only.
  Decision made with founder: protect curated clips from auto-clear.

## Verification (real, not assumed)
- Upload a clip to media/ → `/api/start` (file+loop) → streamed 68 frames + 86 dets over WS
  → `/api/stop` returned `uploads_cleared:1`, `media/` root empty, `samples/` intact (4).
- SIGTERM kill: `media/` cleared to 0, `samples/` intact (4).
- Model-load gotcha re-confirmed: `/api/start` returns `running:True` instantly but `yolov8n`
  needs ~6s before the first frame — wait ≥10s before asserting frame count (see
  `references/verify-live-ws.md`).

## Pitfalls to carry forward
- `pkill -f "luna-edge/app.py"` is a NO-OP for this project. Always `pkill -9 -f "app.py"`
  and verify port-free with `lsof`.
- A "process not found" from a path-pattern grep is NOT evidence the server is down — the
  cmdline won't contain the repo path.
- `atexit` ≠ cleanup-on-kill. For any long-running server cleanup, use SIGTERM/SIGINT handlers.
