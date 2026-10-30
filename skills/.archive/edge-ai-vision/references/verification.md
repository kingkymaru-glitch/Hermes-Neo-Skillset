# Ad-hoc verification (luna-edge has no committed test suite)

Use scratch scripts — there is no pytest/jest here. Pattern proven this session:

1. **Run server-side (cv2/flask) code with the project venv**, not system python.
   System python lacks `cv2`. `cd ~/luna-edge && source .venv/bin/activate && python script.py`.
   Node is available at /usr/local/bin/node for inline-JS syntax checks (`node --check`).

2. **Drive HTTP endpoints with Flask `app.test_client()`** (no port needed):
   `c = app.app.test_client(); c.post('/api/start', json={...})`. Reuses the real handlers.

3. **Terminate the engine in tests**: `run(cfg, stop_event=ev)` then `ev.set(); th.join(timeout=6)`.
   Do NOT let it block on a hung read — the 3s watchdog handles that, but the test must
   set the event or the script hangs and verification times out (and the harness may
   report the run as "failed").

4. **Stub heavy deps** to test wiring without weights/camera:
   `M.YoloDetector = lambda *a,**k: FakeDet()`; `M.build_source = lambda *a,**k: OneFrame()`;
   `M.StdoutSink = FS`. This exercises the encode/draw/stop paths on synthetic frames.

5. **Browser/canvas logic**: extract the inline `<script>` from the served page and
   `node --check` it for syntax. Logic predicates (e.g. the 0.5s box-hold `now-seen<=500`)
   can be replicated in Node/python and asserted — you cannot run a real browser here.

6. **Temp-script hygiene**:
   - Don't use `&` (the terminal tool rejects backgrounding — use background=true instead).
   - No `timeout` command on this Mac (`command not found`) — rely on the script's own
     `ev.set()+join` teardown or the tool timeout.
   - Keep the temp file ALIVE until AFTER the run, then `rm`. Deleting it first makes the
     run fail and the harness reports verification "failed".
   - The runtime sandbox may block `write_file` to /private/var/.../T — write via
     `cat > /tmp/hermes-verify-*.py` in terminal, or write_file to /tmp.
