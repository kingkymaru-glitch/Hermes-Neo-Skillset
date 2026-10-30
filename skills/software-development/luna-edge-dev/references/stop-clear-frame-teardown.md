# Stop / Reset must clear the frame — frozen-frame & stalled-restart bug

## Repro (founder, 2026-08-13)
1. Open via desktop launcher; Insta360 USB auto-detected.
2. Start → runs normally. Stop → image on screen does NOT clear (stays on last
   Insta360 frame).
3. Switch source to webcam(0), choose source 2, Start → STALLS (no frames; old
   frozen frame remains).
4. Reset source → source resets, but the frozen image on screen persists.

## Root cause (two distinct bugs)
A. Frontend: `paint()` runs forever via `requestAnimationFrame` and only draws
   `latestBitmap`. Neither the Stop handler nor the Reset handler cleared
   `latestBitmap`/`pendingBytes`/`latestDets`, so the last decoded frame stayed
   painted.
B. Backend: the original `/api/stop` only set `stop_event` + `running=False` (a
   half-hearted `join(timeout=5)` that merely logged if still alive) — it did NOT
   block until the engine died and did NOT free the device. `/api/start` spawned a
   NEW engine while the OLD one was still alive holding the camera open, so the new
   engine got no frames and the old frozen frame just sat there.

## Fix
app.py
- Added `_teardown_engine(timeout=6)`: sets `stop_event`, `running=False`, `join()`s
  the engine thread (bounded), nulls `thread`/`model`. NOTE: does NOT release the
  source — `detect/main.py` releases it in its own `finally`.
- `/api/stop` now calls `_teardown_engine()` (real stop, frees device).
- `/api/start` calls `_teardown_engine()` FIRST if a prior thread `is_alive()`, so a
  new source can never overlap the old (kills the stall). Also clears `frame_q`/
  `det_q` so a stale frame can't flash one tick after restart.

templates/index.html
- `clearFeed()`: wipes `latestBitmap`/`pendingBytes`/`latestDets` (also
  `bitmap.close()`).
- Stop handler: `fetch('/api/stop'); clearFeed(); setStatus('stopped')`.
- Reset handler: `fetch('/api/stop'); setStatus('stopped'); clearFeed();` (then
  restores default source/URI, unticks tracking, `detectCameras()`).
- `paint()`: when `!frame && !folderMode`, fill idle bg `#0f1216` + centered
  "feed stopped — press Start" so stopped state is visibly empty, not frozen.

## Verification (headless — no GUI here)
- `source .venv/bin/activate && python app.py` (background), then:
  - `curl -s -X POST localhost:8000/api/stop` → `{"ok":true,"msg":"stopped"}`
    (idempotent, no 500 even with no engine).
  - `curl -s -X POST localhost:8000/api/start -H 'Content-Type: application/json' \
     -d '{"source":{"kind":"webcam","uri":"0"}}'` → `{"ok":true}`;
    `curl localhost:8000/api/status` → `{"running":true}`.
  - `curl -s -X POST localhost:8000/api/stop` → status back to `{"running":false}`.
  - Server log: no tracebacks; engine prints "stopped.".
  - Served page: `curl -s localhost:8000/ | grep -c clearFeed` ≥ 1; idle text
    present; extract `<script>` body (lines ~283–706) and `node --check` → OK.
- Could NOT verify the actual pixel repaint in-browser (no display). Founder must do
  the real repro: Stop clears frame; source-switch Start doesn't stall.

## Gotcha that bit during the fix
Invented `from detect.lib.thread import kill_thread` — that module does NOT exist in
the repo → `app.py` import crashed, `/api/stop` returned 500. Fix: removed the import
and the kill call; the engine self-cleans. Before referencing any "kill/stop helper",
grep the repo (`grep -rn "def kill_thread" detect`) to confirm it exists.
