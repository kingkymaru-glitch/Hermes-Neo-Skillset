# DTwin Pipeline Performance Tuning (verified 2026-08-16)

Found by watching a live `tools/pipeline.sh` run on COLMAP 4.1.0 / Apple Silicon
(10 cores). These are WASTES (hardware left idle), not errors. Apply on the next
edit of `tools/pipeline.sh`. The current run is never touched.

## 1. Mapper pinned to 4 threads on a 10-core box
`colmap mapper` runs with `--Mapper.num_threads 4`. On Apple Silicon (10 cores)
the mapper — SfM + global bundle adjustment, the SLOWEST stage — was using ~88%
of 4 cores while the other 6 sat idle (~60% CPU wasted).
Fix: scale to cores, leave 2 for system/ffmpeg:
`--Mapper.num_threads 8` or `$(($(sysctl -n hw.ncpu) - 2))`.
Risk: none (pure parallelism). Priority: HIGHEST.

## 2. COLMAP GPU force-disabled
Script passes `--FeatureExtraction.use_gpu 0` and `--FeatureMatching.use_gpu 0`.
COLMAP 4.1.0 (Homebrew) has `FeatureExtraction.use_gpu` default = 1, i.e. it
SUPPORTS Apple-Silicon GPU. Forcing CPU SIFT wastes the exact stages GPU SIFT
accelerates 5–10x (feature extraction + sequential matching).
Fix: drop the `=0` (let default GPU) or set `=1`.
CAUTION: COLMAP's Metal backend is finicky on some macOS builds. Verify on ONE
test run — confirm images still register and no `BITMAP_ERROR`/GPU-init crash —
before relying on it in production. Priority: MEDIUM (needs validation).

## 3. Training progress hidden by `| tail -5`
Trainer line:
`run_timed "$TRAIN_TO" python "$ROOT/tools/splat-apple/train_mlx.py" ... 2>&1 | tail -5`
buffers until EOF, so during a multi-minute MLX train the webapp log shows
SILENCE, then 5 lines at the very end. Pure observability loss (does not affect
the result). Fix: drop the `tail -5`, or `tee` to a file and `tail -f` it, so
per-iter loss/progress streams live to `/api/pipeline/log`. Risk: none.
Priority: LOW (observability only).

## How the waste was spotted (repro)
While a run (name CMPK1, 200 frames, 2000 iters) was live:
- `pgrep -fl pipeline.sh` + `pgrep -fl "colmap mapper"` to get the PID.
- `ps -axo pid,%cpu,%mem,comm | grep colmap` + `sysctl -n hw.ncpu` → saw 4-thread
  cap vs 10 cores.
- `colmap feature_extractor --help | grep -i use_gpu` → showed default `=1`,
  proving GPU support exists (the `=0` in the script was a deliberate off-switch).
- `curl -s http://localhost:8753/api/pipeline/log | python3 -c "..."` to scan
  stage markers + errors without spawning a browser (see webapp_viewer_debug.md
  note: do NOT spawn headless Chrome on MARU's Mac).

## Do NOT edit pipeline.sh mid-run
The bash child reads the script incrementally; editing corrupts upcoming stages.
Wait for the current run to finish (or `rm -rf frames/<name> train/<name>` and
re-run) before applying these.
