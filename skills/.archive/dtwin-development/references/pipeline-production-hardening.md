# Pipeline + server production hardening (2026-08-15)

When the founder (MARU) asks to "optimize the code, the pipeline, the memory
usage ... test its robustness for production ready" on the DTwin video→splat
pipeline, these are the concrete fixes that were made and verified. All live on
branch `neo` in `~/DTwin`. Summaries of each fix are in the SKILL.md; this file
is the fuller "why / how it bit / exact command" detail.

## 1. GNU `timeout` is NOT on macOS (production blocker)

Symptom during a from-scratch test:
```
>> COLMAP feature extraction
tools/pipeline.sh: line 95: timeout: command not found
ERROR: COLMAP feature extraction failed/timed out (>360s)
```
macOS ships no GNU `timeout`, and `gtimeout` (coreutils) isn't installed here.
So a hardened pipeline that wrapped stages in `timeout N cmd` aborted at the
very first COLMAP stage.

Portable fix (no external deps — perl is always present):
```bash
if command -v gtimeout >/dev/null 2>&1; then TIMEOUT_BIN=gtimeout
elif command -v timeout >/dev/null 2>&1; then TIMEOUT_BIN=timeout
else TIMEOUT_BIN="perl -e 'alarm shift; exec @ARGV'"; fi

run_timed() {
  local secs="$1"; shift
  if [[ "$TIMEOUT_BIN" == perl* ]]; then
    perl -e 'alarm shift; exec @ARGV' "$secs" "$@"
  else
    "$TIMEOUT_BIN" "$secs" "$@"
  fi
}
```
`alarm N` then `exec` replaces the perl process with the child, so when the
alarm fires the child receives SIGALRM and dies (default handler). Verified:
`perl -e 'alarm 2; exec "sleep","30"'` dies in exactly 2.007s, exit 142.

Budgets used (CPU, 300 frames ≈ 42s clip):
- feature extraction: `2*N + 120` s
- exhaustive matching: `0.12*N*N + 120` s
- mapping (SfM): `1.5*N + 300` s
- training: `2.5*iters + 300` s

## 2. RESULT_BASE path mismatch (silent "no .ply" failure)

`train_mlx.py` (ghif/splat-apple) writes output to a CWD-RELATIVE `results/`:
```python
os.makedirs("results", exist_ok=True)
output_dir = os.path.join("results", f"{dataset_name}_mlx_cpp_{timestamp}")
... save_ply(os.path.join(ply_dir, f"{dataset_name}_final.ply"), ...)
```
Because the pipeline script does `cd "$ROOT"`, the .ply lands at
`results/<name>_mlx_cpp_<ts>/ply/<name>_final.ply`. If your "locate ply" search
uses `tools/splat-apple/results/` as the base it finds nothing → `ERROR:
training produced no .ply`. Fix: `RESULT_BASE="results"`.
Also gitignore `results/` at repo root (transient training output).

## 3. COLMAP image_path must not contain the database

If `--image_path` is the parent of `--database_path`, COLMAP scans the sqlite
`db.db`, `db.db-shm`, `db.db-wal` files as candidate images:
```
W... feature_extraction.cc:277] sfm/db.db BITMAP_ERROR: Failed to read the image file format.
```
It warns and skips them, but it's noise and wasteful, and could error on larger
sets. Fix: separate the two dirs —
```
FRAME_DIR="frames/$NAME/images"   # only .jpg (COLMAP --image_path)
SFM_DIR="frames/$NAME/sfm"        # db.db + sparse live OUTSIDE image_path
DB="$SFM_DIR/db.db"; SPARSE="$SFM_DIR/sparse"
```
Cleanup must then `rm -rf frames/$NAME` (parent), not just the images subdir.

## 4. Server pipe-full deadlock (silent production hang)

`server.py` originally did `Popen(..., stdout=PIPE)` and only read stdout while
an SSE client was connected. If the browser tab closed / SSE dropped, nothing
drained the child; once the OS pipe buffer (~64KB) filled, the child blocked
forever writing = hung pipeline with no error.

Fix: a daemon reader thread that ALWAYS drains into a ring buffer, plus replay:
```python
RING = deque(maxlen=8000)
def _read_pipe_forever(proc, ring):
    for raw in iter(proc.stdout.readline, b""):
        line = raw.decode(errors="replace").rstrip("\n")
        if line: ring.append(line)
    ring.append("__EXIT__ %d" % proc.wait())
threading.Thread(target=_read_pipe_forever, args=(proc, RING), daemon=True).start()
```
The SSE handler emits any lines after the client's snapshot (by length) and the
`GET /api/pipeline/log` endpoint returns the tail for reconnect replay. The
child can never block on a full pipe.

## 5. Preflight, idempotence, cleanup (disk never fills)

- Disk preflight BEFORE starting: `FREE_KB=$(df -k / | awk 'NR==2{print $4}')`,
  `FREE_BYTES=$((FREE_KB*1024))`, refuse below 4GB. `df -k` is KB; label GB as
  `FREE_BYTES/1024/1024/1024` or you print nonsense like "22067 GB".
- Idempotent: `if [[ -f "$OUT" ]]; then echo "ALREADY_EXISTS"; exit 0; fi`.
- After publish: `rm -rf frames/$NAME train/$NAME` (a 300-frame build is
  ~1.4GB frames + ~282MB train; without cleanup repeated builds fill disk).

## 6. Server robustness extras

- Atomic spawn under a lock (check-then-Popen in one critical section).
- Double-launch guard: also refuse if ANY `pipeline.sh` is running, even one
  launched outside the server: `subprocess.run(["pgrep","-f","pipeline.sh"])`.
- Graceful SIGINT/SIGTERM handler terminates the running child before
  `srv.shutdown()`.
- Upload: 2GB cap, `os.path.basename` + regex-whitelist the filename.

## 7. Accurate webapp progress (not "N/6")

The pipeline emits ~11 `>>` stage markers (preflight, extract, sample, COLMAP
feature, COLMAP match, COLMAP map, assemble, train, locate, publish, clean). A
crude `count(>>)/6` under-reports. In `web/main.js`:
- map each `>> <stage>` line to an index in a STAGES array;
- during the training stage, parse `(\d+)/<iters>` from the MLX progress line
  and interpolate within that stage's span;
- use the panel's configured `--iters`, NOT a hardcoded 2000.

## 8. Memory / disk accumulation defense (crash residue)

A crashed/aborted build can leave transient data that fills disk and blocks
future runs. Observed in a 4h28m TESTMALL run that was killed by timeout: it
left ~477MB in `frames/TESTMALL/`, ~77MB in `train/TESTMALL/`, an orphaned
`results/` trainer dir, and 4 stale `/tmp/dtwin_*.log` files (~730KB).

Pre-flight + post-publish + EXIT trap handle this:
- `frames/<name>/` — 400-1000MB per crash (images + sfm db)
- `train/<name>/` — 50-100MB per crash
- `results/<name>_mlx_cpp_*/ply/` — trainer output dirs; already published as
  `web/assets/<name>/model.ply` but the `results/` copy lingers.
- `/tmp/dtwin_*.log` — ~700KB per session (harmless but clutters `/tmp`).
- **Orphan processes** — stale `colmap`/`ffmpeg`/`train_mlx.py` not tied to any
  running `pipeline.sh`. Verify ancestry with `pstree -p <pid>` before killing;
  do NOT kill processes that descend from the active `pipeline.sh` (confirmed
  via: `pstree -p <pid> | grep -q "( pipeline.sh --video ... )"`).
- **Pre-flight wipe (committed b7bf4e0):** every `pipeline.sh` run starts with
  `rm -rf "frames/$NAME" "train/$NAME"; mkdir -p "frames/$NAME/images" "frames/$NAME/sfm" "train/$NAME"`.
  Idempotent — safe to run even if the dirs don't exist yet.
- **Post-publish cleanup (extended):** `rm -rf "frames/$NAME" "train/$NAME"
  "$RESULT_BASE/${NAME}_mlx_cpp_*"` frees the bulk of disk after the .ply is
  published. `$RESULT_BASE` is `results` (cwd-relative).
- **EXIT trap (committed b7bf4e0):** `trap 'rm -rf "frames/$NAME" "train/$NAME";
  rm -rf "$RESULT_BASE/${NAME}_mlx_cpp_*"; exit 1' EXIT` guarantees transient
  dirs for THIS run's `$NAME` are wiped even on crash/Ctrl-C/SIGTERM. Does not
  affect other builds' data.

**Note on the trap:** it registers after the post-publish cleanup, so a normal
exit still runs the explicit cleanup + then the trap's `rm -rf` is a no-op
(because the dirs are already gone). On crash, the trap fires and wipes the
transient dirs that the crashed stage was using. Only affects `$NAME` of the
crashed run — other builds' data is untouched.
