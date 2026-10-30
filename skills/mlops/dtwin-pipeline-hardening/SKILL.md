---
name: dtwin-pipeline-hardening
description: "DTwin macOS: ffmpeg→COLMAP→MLX splat→.ply hardening."
---

# DTwin Pipeline Hardening (macOS / Apple Silicon)

Local-first pipeline: ffmpeg → COLMAP SfM → MLX Gaussian splat → `.ply`.
Target: `tools/pipeline.sh` + `server.py` on a Mac without GNU coreutils.

## When to Use
- Any task that edits, debugs, or hardens `tools/pipeline.sh`, `server.py`,
  or the DTwin video→splat pipeline on macOS.
- Before declaring a local capture pipeline “production-ready”.

This skill covers the RECONSTRUCTION half (ffmpeg → COLMAP → splat → `.ply`).
For the stage after it — turning a mesh or splat into a clean, web-ready `.glb`
with headless Blender (decimate, UV, vertex colour, scale, export) — load
`image-video-to-glb-blender-refine`.

## Portable Timeout (macOS has no `timeout`)
GNU `timeout` is absent by default. Use a perl alarm wrapper:

```bash
run_timed() {
  local secs="$1"; shift
  perl -e 'alarm shift; exec @ARGV' "$secs" "$@"
}
```

Verified: kills a runaway process in exactly the cap time (exit 142 = SIGALRM).
Wrap every heavy stage: feature_extraction, matcher, mapper, training.

## COLMAP Matcher: Sequential, Not Exhaustive
For **video / temporal captures** (frames are ordered by time):

- **Wrong:** `colmap exhaustive_matcher` — O(N²) pairs = hours for 300 frames.
- **Right:** `colmap sequential_matcher --overlap 10 --loop_detection 1`

```bash
colmap sequential_matcher \
  --database_path "$DB" --image_path "$FRAME_DIR" \
  --SequentialMatching.overlap 10 \
  --SequentialMatching.loop_detection 1 \
  --SequentialMatching.loop_detection_period 10 \
  --SequentialMatching.loop_detection_num_images 50 \
  --SequentialMatching.loop_detection_num_nearest_neighbors 1
```

Speedup: ~15x fewer pairs (44,850 → 3,000 for 300 frames). Timeout budget:
`MATCH_TO = N * overlap * 0.3 + 120` seconds (not N²).

## COLMAP Dir Layout
Keep images and sfm workdirs separate:

```
frames/<name>/images/   ← only .jpg files (COLMAP --image_path)
frames/<name>/sfm/      ← database.db + sparse/ (NOT inside image_path)
```

If `sfm/` lives inside the image folder, COLMAP scans `db.db`/`.db-shm`/`.db-wal`
as candidate images and emits `BITMAP_ERROR` warnings.

## train_mlx.py Output Path
The MLX trainer writes under the **current working directory**, to
`results/<name>_mlx[_cpp]_sh<N>[_dens]_<ts>/ply/` — not to a fixed
`tools/splat-apple/results/`. The suffix varies with the flags passed, so do NOT
hard-code `_mlx_cpp_`: run from `tools/splat-apple` with
`--rasterizer cpp --sh_degree 3`, the run landed in
`results/dataset_mlx_cpp_sh3_dens_<ts>/`, and a `find ... -name '*_mlx_cpp_*'`
misses it entirely.

Glob the prefix only, and take the newest run:

```bash
RESULT_BASE="results"
PLY=$(ls -td "$RESULT_BASE/$NAME"_mlx_*/ply/*.ply 2>/dev/null | head -1)
```

Inside `ply/` the snapshots are `<name>_best.ply` (highest PSNR seen so far) and
`<name>_final.ply` (last iteration). Prefer `_best`, but be aware the best-PSNR
snapshot is often captured while the resolution ramp is still at half res, so
"best PSNR" can be a LOWER-resolution model than the final one — check which
schedule phase it came from before treating it as the quality peak.

## GPU Concurrency Guard
Two `train_mlx.py` processes on the same Apple Silicon GPU crash with:

```
[METAL] Command buffer execution failed: Impacting Interactivity
```

Guard before training:

```bash
if pgrep -f "train_mlx.py" >/dev/null 2>&1; then
  echo "ERROR: another training is using the GPU"; exit 7
fi
```

## Disk / Memory Preflight
- **Disk guard:** `FREE=$(df -B1 / | awk 'NR==2{print $4}')`; abort if `< 4GB`.
- **Memory guard:** training RSS is typically ~1.5–2GB on 16GB machines; no
  special cap needed, but watch for unbounded growth.
- **Auto-cleanup:** after successful publish, delete `frames/<name>/` and
  `train/<name>/` (the `.ply` in `web/assets/<name>/` is the durable artifact).

## Server Pipe-Drain Deadlock Fix
When `subprocess.Popen(stdout=PIPE)` is used and the browser SSE client
disconnects, the child blocks once the ~64KB OS pipe fills.

Fix: a **background reader thread** that always drains stdout into a ring
buffer. The ring buffer also supports reconnect replay (`GET /api/pipeline/log`).

```python
def _read_pipe_forever(proc, ring):
    try:
        for raw in iter(proc.stdout.readline, b""):
            ring.append(raw.decode(errors="replace").rstrip("\n"))
    finally:
        rc = proc.wait()
        ring.append("__EXIT__ %d" % rc)
```

## Production Checklist
- [ ] `bash -n tools/pipeline.sh` passes
- [ ] `python3 -m py_compile server.py` passes
- [ ] `node --check web/main.js` passes
- [ ] DELETE endpoint tested: `curl -X DELETE /api/assets/<name>` → `{"deleted":"..."}`
- [ ] Timeout actually kills (test with `sleep 30` under 2s cap)
- [ ] Sequential matcher active (not exhaustive) for video inputs
- [ ] MAP_TO budget sized ~3x measured mapper time (not naive N*1.5)
- [ ] Browser served with Cache-Control: no-store (no stale-JS cache)
- [ ] Cross-origin isolation headers (COOP + COEP) present on ALL responses
- [ ] Viewer auto-frames camera to splat bounding box
- [ ] images/ and sfm/ are separate dirs
- [ ] GPU guard present before training step
- [ ] Auto-cleanup removes transient dirs on success
- [ ] Server ring-buffer drain thread running

## Stage Timeout Budgets: Size to Reality, Not Naive Formulas
The mapper (SfM + global bundle adjustment) is the SLOWEST stage, not the
matcher. A naive `N*1.5 + 300` budget (750s for 300 frames) killed EVERY
build at the same point — `Retriangulation and Global bundle adjustment` —
producing `ERROR: COLMAP mapping failed/timed out (>750s)`, exit 4, and NO
`.ply`. Symptom was identical across dji_test, pontoon, and TESTMALL.

Correct budget: `MAP_TO = N * 7 + 600` seconds (≈45min for 300 frames on CPU).
Bundle adjustment on 168 registered images takes 20–45 min. Rule: measure real
stage time once, then budget ~3x. When a build dies mid-stage with a timeout,
the budget is wrong — not the data.

## MLX Training Monitoring (Metal GPU shows ~0% CPU)
`train_mlx.py` runs on the Metal GPU, so `ps`/`top` shows ~0% CPU and that is
NORMAL — not a hang. To confirm liveness:
- Progress renders: `results/<name>_mlx_cpp_<ts>/progress/progress_XXXX.png`
  written every 100 iters (next after `progress_0000.png` is iter 100, NOT iter 1 —
  so in the first ~2 min ONLY `progress_0000.png` exists; that is NOT stalled).
- `results/` dir grows; `.ply` appears only at the END (not incremental).
- `pgrep -f train_mlx.py` confirms the process is alive.

### Measuring throughput (don't guess the ETA)
Watch two consecutive progress PNGs across a `sleep` window and infer iters/sec:
```bash
P=~/DTwin/results/<name>_mlx_cpp_*/progress
ls -lT "$P"                       # mtime of progress_0100.png, progress_0200.png
sleep 70; ls -lT "$P"             # next appearance = +100 iters since last seen
```
Empirical baseline (verified 2026-08-16, `dji_701`, 300 frames @ 1920×1080,
`--rasterizer cpp`): ~1.1 it/s ⇒ 2000 iters ≈ 30 min. First PNG (iter 0) writes
at startup; iter 100 lands ~78s later; iter 200 ~107s after that. A new PNG every
~2 min = healthy and on track. If NO new PNG after >5 min, it IS hung — investigate.

## Trainer Quality Gaps & Improvement Backlog (verified by reading source)
The `tools/splat-apple/train_mlx.py` + `mlx_gs` trainer started as a *minimal* 3DGS.
Status as of 2026-08-16 (a session implemented A = checkpoint + resolution-ramp,
and B = densification + SH-degree):

- **[DONE] Checkpointing (gap #1, trainer-side).** `train_mlx.py` now saves a
  resumable PLY every `checkpoint_every` iters (default 250) + a `best_psnr.ply`
  snapshot, plus a NaN guard. `save_ply`/`load_gaussians_from_ply` round-trip SH
  degree>0 (shape `(N,16,3)`) correctly.
- **[DONE — but SILENTLY DISABLED by the default flags] Densification (gap #2).**
  `gaussians.densify_and_prune` clones/splits/prunes; optimizer state is recreated
  after each growth. Gated by `--densify_from/--until/--interval` (default
  500/1500/100) and `--no_densify` to disable.
  **The defaults never fire.** The gradient-accumulation guard is
  `densify_from <= i < densify_until AND scale == 1.0` — it only counts gradients
  during the FULL-RESOLUTION phase, but the resolution ramp keeps `scale` at 0.5
  until `num_iterations/2` while `--densify_until` defaults to 1500. For any run of
  3000+ iterations those windows are disjoint, so densification is a structural
  no-op: N stays frozen at the COLMAP point count and the output is blocky and
  low-detail no matter how long you train.
  **Symptom:** `grep -c 'densify @' <train.log>` returns 0 and the `N=` counter in
  the progress bar never changes from the initial point count.
  **Fix without editing the trainer:** derive the window from the full-res phase —
  `--densify_from <num_iterations/2> --densify_until <0.85*num_iterations>`. Confirm
  the fix by watching for `[densify @N]` lines and a rising `N=`.
- **[DONE] SH degree 0→3 (gap #3).** `init_gaussians_from_pcd(..., sh_degree=K)`
  builds `(N,(K+1)²,3)`; `renderer.render` evaluates the real SH basis when
  `sh_coeffs.shape[1] > 1`. `--sh_degree 0/1/2/3`.
- **[DONE] Resolution ramp (gap #4).** `train_mlx.py` renders at 1/4 res for the
  first ~15% of iters, 1/2 to ~50%, full after — ~2× faster to same quality.
- **[OPEN — HIGH RISK] `pipeline.sh` EXIT trap STILL wipes results.** The trap
  `rm -rf $RESULT_BASE/${NAME}_mlx_cpp_*` runs on **every** exit (incl. success),
  so even with in-trainer checkpoints the final `results/<name>_mlx_cpp_*/` is
  deleted once the run ends and the only survivor is `web/assets/<name>/model.ply`
  (if publish was reached). **CONFIRMED FIRE:** on 2026-08-16 the completed
  `dji_701` run's `train/dji_701` + `results/..._mlx_cpp_*` were auto-deleted by
  this trap the moment the job ended, destroying the in-progress checkpoint set.
  FIX (NOT yet applied): relax the trap to preserve `results/<name>_mlx_cpp_*/`
  (or at least `best_psnr.ply`) unless the run explicitly failed; or copy
  checkpoints to a non-transient dir (`splats/<name>/`). Apply this before calling
  the pipeline crash-safe.
- **[BACKLOG] Live webapp progress (#5), exposure/background (#6).** Unchanged.

### MLX 3DGS implementation gotchas (verified 2026-08-16 — re-read before editing train_mlx.py / gaussians.py / renderer.py)
MLX on this Mac is **0.30.6**. Several PyTorch-era assumptions break hard:
- **No boolean-array indexing.** `means[bool_mask]` raises. Convert every mask to
  int indices first: `idx = mx.array(np.nonzero(np.asarray(mask_bool))[0])`.
  Applies to clone/split/prune selection and any `params[mask]` slice.
- **No `mx.image` module.** `mx.image.resize` does not exist. Downscale targets with
  PIL (`Image.fromarray(...).resize((w,h), 2)`) then rewrap as `mx.array`; drive
  resolution through the camera (scale `fx/fy/cx/cy` + `W/H`), since the rasterizer
  derives image size from `camera.width/height` + `intr`.
- **Densify must use PRE-GROWTH arrays.** Compute BOTH the clone and split masks
  from the pre-growth `grads`/`scales`/`opac`, then append all new Gaussians in one
  pass. Do NOT recompute a mask after `mx.concatenate` grows the arrays — the
  gradient tensor still has the old N and will broadcast-mismatch (shape (N0) vs
  (N0+Δ)). Standard 3DGS grows clone+split together; replicating it per-step with
  stale shapes is the #1 densify crash.
- **Opacity threshold is on SIGMOID, not raw.** `init` opacities start at 0 (raw),
  so a prune on `raw_opac < min_opacity` deletes EVERYTHING on the first densify →
  N collapses to 0. Use `mx.sigmoid(opac)[:,0] < min_opacity` (and `> min_opacity`
  for clone/split eligibility), recomputed on the current arrays right before each
  mask.
- **`init_gaussians_from_pcd` returns a `Gaussians` dataclass, not a dict.** The
  train loop treats `params` as a dict (`params["means"]`). Wrap at init:
  `g = init_gaussians_from_pcd(...); params = {"means":g.means, "scales":g.scales,
  "quaternions":g.quaternions, "opacities":g.opacities, "sh_coeffs":g.sh_coeffs}`.
- **`save_ply` reshapes `sh[:,1:,:]` — guard N==0.** `sh[:,1:,:].reshape(N,-1)`
  crashes when N=0 (empty rest). Guard: `if K>1 and N>0: rest=... else rest=zeros((N,0))`.
- **SH>0 needs the renderer to evaluate the basis.** The stock renderer was DC-only;
  higher SH bands would be silently ignored (flat/black in-browser). `render()` must
  branch on `sh_coeffs.shape[1]`: if >1, compute `RGB = SH_C0*f_dc + sum f_rest_lm *
  SH_l^m(dir)` with the real SH polynomials; else DC only.
- **argparse: `--densify` is ambiguous.** It prefix-matches `--densify_from/
  --densify_until/--densify_interval` → `error: ambiguous option`. Densify is ON by
  default; to disable pass `--no_densify`. Never pass bare `--densify`.
- **Python rasterizer is SLOW for big scenes.** `--rasterizer python` (CPU) on the
  70k-point `sample` dataset timed out at 600s for just 60 iters. Use
  `--rasterizer cpp` (Metal) for any real run; reserve `python` for tiny (<200
  Gaussian) smoke tests.
- **Validate via real subprocess, not importlib.exec_module.** Loading the trainer
  through `importlib.util.spec_from_file_location` + `exec_module` mis-resolves
  `load_colmap_dataset`'s path ("COLMAP binary files not found" / 0 cameras) even
  though the same flags work as a real `python train_mlx.py ...` subprocess. Always
  smoke-test training as a subprocess. Copy-paste recipe in
  `references/mlx-3dgs-gotchas.md`.
5. **No live progress in webapp.** `server.py` serves only the final asset;
   `progress_*.png` exist but aren't surfaced. Could stream latest PNG + loss/PSNR
   via `/api/train-status`. Nice-to-have for monitoring without terminal.
6. **No exposure / background handling.** Optional learned per-image exposure.

## Web Viewer: Cross-Origin Isolation (SharedArrayBuffer) — the REAL "blank canvas" bug
The gaussian-splats-3d library defaults `sharedMemoryForWorkers: true`, so its
sort worker uses a `SharedArrayBuffer`. Browsers only expose `SharedArrayBuffer`
on **cross-origin-isolated** pages, which requires two response headers:

```
Cross-Origin-Opener-Policy: same-origin
Cross-Origin-Embedder-Policy: require-corp
```

Without them the worker throws
`DataCloneError: SharedArrayBuffer transfer requires self.crossOriginIsolated`,
the splat silently fails to render, and the user sees only the placeholder
pillar with the status stuck at "viewing <name>". This affects **every** `.ply`,
not just new ones — it looks like a data problem but is a serving-header problem.

Fix (belt-and-suspenders):
1. Send both headers in `server.py` `end_headers()`.
2. Also pass `sharedMemoryForWorkers: false` to the Viewer constructor so a
   dropped header can never break rendering again:
   `new Viewer({ ..., sharedMemoryForWorkers: false })`.

Diagnose headlessly without a real GPU:
```
"/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" --headless=new \
  --no-sandbox --use-angle=swiftshader --enable-unsafe-swiftshader \
  --enable-logging=stderr --v=0 --virtual-time-budget=10000 --dump-dom \
  "http://127.0.0.1:8753/web/index.html" 2>&1 | grep -iE "splat|error|SharedArrayBuffer"
```
(Add `--disable-gpu` to test the WebGL-unavailable path instead; that "no WebGL"
error is headless-only and NOT the real bug in the user's browser.)

## Web Viewer: Auto-Frame Camera to Each Capture
Each COLMAP reconstruction has its own coordinate space and scale, so a
hardcoded camera (`position.set(2.2,1.8,3.2)`, target `(0,0.8,0)`) shows a new
capture blank or microscopic. Fix: compute the splat's bounding box and fit the
camera after `addSplatScene`:

```js
const mesh = viewer.getSplatMesh();
const box = mesh.computeBoundingBox(true, 0);   // THREE.Box3
const center = box.getCenter(new THREE.Vector3());
const radius = Math.max(...box.getSize(new THREE.Vector3()).toArray(), 0.001);
camera.position.set(center.x + r*0.6, center.y + r*0.4, center.z + r);
camera.near = radius/100; camera.far = radius*50; camera.updateProjectionMatrix();
controls.target.copy(center); controls.update();
```

## Web Viewer: Browser Cache + Module Specifier Pitfalls
Two silent causes of "error persisted / still broken" in the browser viewer:

1. **Bare module specifier fails the importmap.** Dynamic `import('vendor/x.js')`
   resolves against the importmap; a bare `vendor/...` key is NOT auto-mapped.
   Use a relative path `'./vendor/x.js'` (resolves to `/web/vendor/x.js`), or add
   an explicit importmap key.

2. **Browser caches stale JS.** `SimpleHTTPRequestHandler` sends `Last-Modified`
   but no `Cache-Control`, so the browser keeps serving an old `main.js` even
   after the file is fixed. Fix: override `end_headers()` to send
   `Cache-Control: no-store, no-cache, must-revalidate`, then hard-refresh
   (Cmd+Shift+R). Verify with `curl -sI .../main.js | grep -i cache-control`.

## Post-Convert GLB Validation (catches the defect that shipped broken CMPK1)
The `ply_to_glb.py` stage writes the portable `.glb`, but a malformed GLB
silently ships and then throws in the viewer. Two real defects seen 2026-08-16:

1. **Null-padded JSON chunk.** GLB spec requires the JSON chunk padded with
   `0x20` (space) to the 4-byte boundary. A `0x00` pad makes GLTFLoader throw
   `Unexpected non-whitespace character after JSON at position N`.
2. **Wrong `target` on a bufferView.** For a POINTS cloud (POSITION + COLOR_0
   only) there must be NO index bufferView. A `target: 34963`
   (ELEMENT_ARRAY_BUFFER) on the color/position view is invalid and rejects the
   asset. The correct value is `34962` (ARRAY_BUFFER) or omitted.

The on-disk `tools/ply_to_glb.py` was correct (space-padded, `target:34962`),
yet an in-flight run produced BOTH defects — i.e. the converter that actually
ran differed from the file on disk (stale interpreter / pre-fix variant).
**Lesson: never trust "the script looks right" — validate the artifact.**

Reusable validator: `scripts/glb_validate.py <file.glb>` → exits 0 PASS / 1 FAIL
and names the defect. Add a post-convert guard so a malformed GLB is
regenerated, not shipped:

```bash
GLB_OUT="web/assets/$NAME/model.glb"
"$SPLAT_VENV/bin/python" "$ROOT/tools/ply_to_glb.py" "$OUT" "$GLB_OUT" --max-points 200000 \
  || echo "WARN: .glb conversion failed (splat still published)"
# post-convert validation guard (prevents silently-broken viewer assets):
if ! "$SPLAT_VENV/bin/python" "$ROOT/scripts/glb_validate.py" "$GLB_OUT"; then
  echo "ERROR: produced $GLB_OUT failed GLB validation; regenerating"
  "$SPLAT_VENV/bin/python" "$ROOT/tools/ply_to_glb.py" "$OUT" "$GLB_OUT" --max-points 200000
fi
```

Regenerate a broken asset from its valid `.ply` without re-running the pipeline:
```bash
tools/splat-apple/.venv/bin/python tools/ply_to_glb.py web/assets/<NAME>/model.ply web/assets/<NAME>/model.glb --max-points 200000
```

## COLMAP Tuning (10-core Apple Silicon — default settings waste CPU)
- **Mapper thread cap.** `colmap mapper --Mapper.num_threads 4` leaves ~60% of a
  10-core Mac idle during the LONGEST stage (SfM + global BA). Bump to `8`
  (leave 2 for system + ffmpeg + the viewer). Biggest single speedup.
  **APPLIED 2026-08-16** in `tools/pipeline.sh` (`--Mapper.num_threads 8`).
- **GPU is force-disabled.** `feature_extractor`/`sequential_matcher` run with
  `--FeatureExtraction.use_gpu 0` / `--FeatureMatching.use_gpu 0`. COLMAP 4.1.0
  shows `use_gpu` default `= 1` (GPU-capable build), so GPU SIFT would accelerate
  feature+matching ~5–10x. **Medium confidence** — COLMAP's Metal backend is
  finicky on some macOS builds; enable behind a tested flag and do one
  verification run before trusting it. Check capability:
  `colmap feature_extractor --help | grep -i use_gpu` (shows default `=1` if GPU-capable).
  **DEFERRED (user MARU ordered: finish trim/mesh + #1 + #3 first, investigate #2 last).**
  When implementing: set both flags to `1`, run a 10-frame probe on the user's Mac
  to confirm Metal SIFT actually runs (not just that the flag is accepted) BEFORE
  relying on it for a full multi-hundred-frame build.
- **Training progress is invisible.** `pipeline.sh` pipes training through
  `2>&1 | tail -5`, which buffers until EOF — during the multi-minute train the
  log shows silence. Swap for `tee train/$NAME/train.log` (or `tail -f` the log)
  so iteration/loss streams live. The progress PNGs in
  `results/<name>_mlx_cpp_*/progress/progress_XXXX.png` are the real liveness signal.
  **APPLIED 2026-08-16** in `tools/pipeline.sh`: replaced `| tail -5` with
  `| tee "$TRAIN_DIR/train.log"` so the full log is captured (and `tail -f`-able).

## Pitfalls
- **Densification can be ON by default and still never run.** See the densification
  entry above: the flag defaults and the resolution ramp can be disjoint, so a long
  training run silently produces a blocky model. Check `grep -c 'densify @'` on the
  log and the `N=` counter before judging output quality.
- **Editing pipeline.sh mid-run:** the bash child reads the script
  incrementally; editing corrupts upcoming stages. Wait for completion.
- **Backslash drift in Python patches:** `python3 -c` double-escapes backslashes.
  Prefer `write_file`, `patch`, or `sed -i ''` for surgical edits.
- **Terminal background rules:** foreground commands cannot use `nohup`, `&`,
  or `setsid`. Use `terminal(background=true, ...)`.
- **Branch switching with local files:** if `git checkout` fails because of
  local files, back them up, checkout, then restore.
- **`curl | python3` security warnings:** local-only endpoints (`localhost`)
  are safe; the warning is a generic curl-pipe rule.
