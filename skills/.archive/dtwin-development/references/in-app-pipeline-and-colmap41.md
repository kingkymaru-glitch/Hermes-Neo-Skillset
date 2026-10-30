# In-app pipeline + verified COLMAP 4.1 / ffmpeg fixes (DTwin, 2026-08-15)

Session: "process ~/Desktop/DJI/testdji.mp4 with the same pipeline" + founder
steering that the pipeline must be a visible, controllable surface in the
webapp (upload file, follow the process, pick parameters, press Start), not a
hidden script. Local webapp is correct here because COLMAP + MLX splat training
must run natively on the Mac.

## Architecture that resulted
- `tools/pipeline.sh` — parameterized, reusable:
  `tools/pipeline.sh --video <src> --name <deploy> --frames N --iters N`
  → publishes `web/assets/<deploy>/model.ply`. First version proven end-to-end.
- `server.py` — stdlib only (no pip), replaces `python3 -m http.server`:
  `python3 server.py` → http://localhost:8753 (serves repo root so `/web/...`
  and relative `assets/...` both resolve).
- `web/index.html` + `web/main.js` — LunaV-family UI (gold `--lv-turq`,
  glass blur-22 panels, header bar, bottom rail) + left floating control panel.

## server.py API surface
- `POST /api/pipeline` JSON `{video,name,frames,iters}` → starts pipeline.sh as
  a subprocess (single in-flight job guarded by a lock; 409 if already running;
  400 if video path not an existing absolute file). **Double-launch guard:** the
  in-process `RUN["proc"]` lock is NOT enough if a pipeline was launched outside
  the server (e.g. `nohup bash tools/pipeline.sh ...` in a terminal) — that one
  isn't tracked by the server, so a webapp "Run" click would start a SECOND
  pipeline colliding on the same dirs. Also `pgrep -f pipeline.sh` and 409 if
  any is running:
  ```python
  running = subprocess.run(["pgrep","-f","pipeline.sh"],capture_output=True,text=True).stdout.strip()
  if running: self._send(409, json.dumps({"error":"a pipeline is already running (started elsewhere)"}))
  ```
  Note: because the running server predates your edit, you must RESTART `server.py`
  for the new guard to load — testing the guard against a stale process silently
  starts a stray pipeline (side effect to kill + clean).
- `GET /api/pipeline` → Server-Sent Events. Emits `data: <line>` per stdout
  line, then `data: __EXIT__ <rc>`. On idle emits `: idle\n\n` keepalive.
- `POST /api/pipeline/stop` → `p.terminate()`.
- `GET /api/assets` → `{"assets": [<dirs under web/assets that contain
  model.ply>]}`.
- `POST /api/upload?name=<id>&filename=<f>` with the raw file bytes as the
  body (Content-Type: application/octet-stream) → saves to
  `ingest/<id>/<sanitized-f>` and returns `{path,name,filename,size}`. No
  multipart parsing needed — read Content-Length, loop `rfile.read(1<<20)`.
  Sanitize fname with `re.sub(r"[^A-Za-z0-9._-]", "_", fname)`.

## SSE handler shape (server-side)
```python
self.send_response(200)
self.send_header("Content-Type", "text/event-stream")
self.send_header("Cache-Control", "no-cache")
self.send_header("Access-Control-Allow-Origin", "*")
self.end_headers()
while True:
    line = p.stdout.readline()
    if line:
        self.wfile.write(("data: " + line.decode(errors="replace")).encode()); self.wfile.flush()
    elif p.poll() is not None:
        self.wfile.write(("data: __EXIT__ %d\n\n" % p.returncode).encode()); self.wfile.flush()
        RUN["proc"] = None; break
    else:
        time.sleep(0.2)   # and an idle keepalive branch
```
Client: `new EventSource('/api/pipeline')`, on `__EXIT__ <rc>` treat rc==0 as
success and enable "View Hologram". Crude progress: count `>>` stage markers in
the log text / total stages.

## Client "View Hologram" (swap splat at runtime without stacking)
The gaussian-splats-3d Viewer `dispose()` does NOT remove the splatMesh from the
scene graph. To swap models cleanly:
```js
if (splatViewer) {
  try { splatViewer.removeSplatScene(0, false); } catch {}
  try { splatViewer.dispose(); } catch {}
  splatViewer = null;
}
placeholder.visible = true;
const mod = await import('vendor/gaussian-splats-3d.module.js');
const viewer = new mod.Viewer({ renderer, camera, scene, gpuAcceleratedSort: true });
await viewer.addSplatScene(url, { showLoadingUI: false });
splatViewer = viewer; placeholder.visible = false;
```

## PITFALL — COLMAP 4.1.0 CLI renames (strict parser, aborts under set -e)
Homebrew COLMAP 4.1.0 (no CUDA). Unrecognized option → step errors AND, with
`set -euo pipefail`, the whole pipeline script dies silently (no ply). Verify
current names with `colmap feature_extractor --help | grep use_gpu`.

| Old name (older recipes) | COLMAP 4.1.0 valid name |
|--------------------------|--------------------------|
| `--SiftExtraction.use_gpu 0` | `--FeatureExtraction.use_gpu 0` |
| `--SiftMatching.use_gpu 0` (exhaustive_matcher) | `--FeatureMatching.use_gpu 0` |
| `--SiftMatching.use_gpu` in mapper | drop; `--Mapper.num_threads 4`, `--Mapper.ba_use_gpu 0` exists |

Error seen: `Failed to parse options - unrecognised option '--SiftExtraction.use_gpu'`
then (with set -e) no further output.

## PITFALL — COLMAP 4.1 requires the database's PARENT dir to exist
`colmap feature_extractor --database_path frames/<d>/sfm/db.db` fails with
`Check failed: database_parent_path.empty() || ExistsDir(database_parent_path)`.
Fix: `mkdir -p "$(dirname "$DB")"` before feature_extractor. The older `sample`
run never hit this because its commands were typed ad-hoc and the dir already
existed.

## PITFALL — ffmpeg `-vf fps=N` is frames/SECOND, not fraction of source
Wrong: `RATE = N / frame_count` → for 41s/1250-frame clip gave `fps=0.24`
→ only ~10 frames. Correct: `RATE = N / duration_seconds` → `fps=7.19` → 300.
```bash
DUR=$(ffprobe -v error -show_entries format=duration -of csv=p=0 "$VIDEO")
RATE=$(awk "BEGIN{printf \"%.4f\", $FRAMES/$DUR}")
ffmpeg -y -i "$VIDEO" -vf fps=$RATE -q:v 2 "$FRAME_DIR/frame_%05d.jpg"
```

## PITFALL — macOS has no `stdbuf`
`stdbuf -oL -eL bash ...` fails ("stdbuf: No such file or directory") and the
whole background command does nothing. Do not use stdbuf on macOS for line
buffering; use `python3 -u` wrappers or accept block-buffering (check the
frames/ dir + `pgrep -fl colmap` to confirm progress instead of trusting the
log tail, which lags under nohup).

## Verification notes
- The browser_exec tool blocks private/internal addresses (localhost), so it
  cannot load the local app. Verification path = curl (all assets + endpoints
  return 200) + `node --check web/main.js` + `bash -n tools/pipeline.sh` + the
  user's real browser (which rendered the earlier splat). Do NOT claim "done"
  from headless screenshots — real browser only (MARU rule).
- Long CPU jobs (COLMAP + MLX training) must run backgrounded; foreground
  `sleep N` is clamped to 60s and `timeout` caps at 600s. Poll via
  `pgrep -fl colmap|train_mlx` + inspecting `frames/`/`results/`, or a
  background watcher loop that pings on `web/assets/<name>/model.ply` existing.
