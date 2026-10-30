---
name: gaussian-splatting-pipeline
description: Local 3DGS capture→AR pipeline on Apple Silicon. No cloud.
---

# Gaussian Splatting Pipeline (local-first, Apple Silicon)

Capture → SfM → train 3DGS (.ply) → deliver on web (splat) + Unity AR (mesh).

## When to use
User wants video/images → a Gaussian-splat "hologram" they can view on web and/or in AR, locally (no cloud upload).

## Pipeline
1. **Capture** → `ingest/<deploy>/` (sacred: never modify/delete).
2. **Frames**: `ffmpeg -i src.mp4 -vf fps=2 frames/<deploy>/frame_%05d.jpg`
3. **SfM (COLMAP)**: feature_extractor + sequential_matcher + mapper → `frames/<deploy>/sfm/sparse/0` (cameras.bin, images.bin, points3D.bin). Recovers camera poses + seed cloud.
4. **Train 3DGS → .ply** (core asset). Trainer on Apple Silicon: splat-apple (MLX/Metal), `references/splat-apple-setup.md`. On an NVIDIA box the trainer is a CUDA implementation instead — the dataset layout is the portable part, not the trainer (see the trainer-portability pitfall below).
5. **Clean** (opt): SuperSplat to crop junk.
6. **Deliver**:
   - Web: three.js gaussian-splat renderer, set `MODEL_URL` to the .ply. Pitfalls in `references/webapp-blank-pitfall.md`.
   - Unity AR: ARFoundation; load `.ply` splat OR baked `.glb` mesh (lighter, ARKit/ARCore-native). Producing that `.glb` cleanly is its own stage: load `image-video-to-glb-blender-refine` — splat → Poisson mesh → headless Blender decimate/UV/vertex-colour/scale/export, plus the subject-isolation step that stops Poisson welding ground and background into the subject. Runnable implementation of the splat→mesh half: `scripts/mesh_from_splat.py` (cluster isolation + Poisson + decimate, writes a vertex-coloured `.ply` for Blender).

## Decisions

- **Splat-first**: the splat is THE asset; COLMAP SfM only recovers poses.
- **Dual-asset** (from Kiri Engine): web = splat (.ply, rich look); Unity AR = mesh (.glb, AR-native). See `references/kiri-dual-asset.md`.
- **Local-first / private**: user prefers local MLX training over cloud (Luma/Polycam/Kiri).
- **Web-first, no build step**: `python -m http.server` + three.js CDN.
- **"Done" = visible in a REAL browser.** Headless WebGL on macOS routinely fails to create a GL context; do NOT blame "headless GL flake" for a blank canvas — root-cause (often a DOM-id mismatch, see webapp-blank-pitfall.md).

## Pitfalls
- **Densification is silently a no-op under the default MLX trainer flags.** The
  gradient-accumulation guard needs BOTH `i < densify_until` AND a full-res render,
  but the resolution ramp holds half-res until `num_iterations/2` while
  `--densify_until` defaults to 1500 — disjoint for any 3000+ iteration run. N stays
  frozen at the COLMAP point count and the model is blocky regardless of runtime.
  Symptom: no `densify @` lines in the log, unchanging `N=` in the progress bar. Pass
  `--densify_from N/2 --densify_until 0.85N`. Detail in `dtwin-pipeline-hardening`.
- **COLMAP 4.1 CLI renames** (Homebrew, no CUDA): `--SiftExtraction.use_gpu` →
  `--FeatureExtraction.use_gpu`; `--SiftMatching.use_gpu` →
  `--FeatureMatching.use_gpu` (exhaustive_matcher); mapper uses
  `--Mapper.num_threads`/`--Mapper.ba_use_gpu`. Strict parser aborts the step
  (and a `set -euo pipefail` script dies silently, no ply) on an unrecognized
  option. Verify with `colmap feature_extractor --help | grep use_gpu`.
- **COLMAP 4.1 requires the database's PARENT dir to exist**: `--database_path
  frames/<d>/sfm/db.db` fails `Check failed: ...ExistsDir` unless
  `mkdir -p "$(dirname "$DB")"` first.
- **ffmpeg `-vf fps=N` is frames/SECOND**, not a fraction of source. To sample
  ~N frames: `output_fps = N / duration_seconds` (`ffprobe -v error
  -show_entries format=duration -of csv=p=0`). Dividing N by frame COUNT is
  wrong (41s/1250-frame clip → fps=0.24 → ~10 frames instead of 300).
- **macOS has no `stdbuf`** — don't gate a background run on `stdbuf -oL`;
  confirm progress via `pgrep -fl colmap|train_mlx` + inspecting dirs, not a
  laggy nohup log tail.
- **`set -u` bites the training step**: a pipeline script using
  `set -euo pipefail` that does `export PYTHONPATH="$ROOT/tools/splat-apple:$PYTHONPATH"`
  dies with `PYTHONPATH: unbound variable` on a clean shell (no prior PYTHONPATH).
  Use `${PYTHONPATH:-}`. Symptom: COLMAP+SfM succeed, then the script aborts
  silently right after "training Gaussian splat" with no .ply.
- **Resume from checkpoint, don't re-run the whole pipeline**: COLMAP/SfM is the
  ~40min cost. If the pipeline dies AFTER the dataset is assembled
  (`train/<d>/images_8` + `train/<d>/sparse/0` both present), you can launch the
  MLX training step directly (source venv, set PYTHONPATH, run train_mlx.py on
  that dir) instead of re-extracting + re-running COLMAP. Never delete those
  two dirs to "start clean" — that's the expensive result.
- **Server-driven pipeline needs a double-launch guard**: if a pipeline can be
  started BOTH from the webapp and via a raw `nohup bash tools/pipeline.sh ...`
  (as during a manual test), the server's in-memory `RUN["proc"]` is None for
  the externally-launched one — so the webapp "Run" would spawn a SECOND
  pipeline onto the same `frames/<d>`, `ingest/<d>` dirs and collide. Guard in
  `POST /api/pipeline`: also `pgrep -f pipeline.sh` and return 409 if non-empty.
- **Stale server after patching server.py**: `curl` a running server to test a
  NEW guard → you hit the OLD in-memory process (still serves the pre-patch
  handler) and the "guard" appears to not work, plus the test POST may actually
  LAUNCH a stray pipeline. Always restart the server after editing server.py
  (`lsof -ti tcp:PORT | xargs kill`, then relaunch) before trusting a curl test;
  kill any stray pipeline the stale test spawned.
- **The pipeline must be exposed IN the webapp** (upload file, pick params,
  Start, follow live log), not just a hidden script. A stdlib `server.py` can
  serve the app AND drive the pipeline via SSE (`POST /api/pipeline` +
  `GET /api/pipeline` EventSource) + raw-body `POST /api/upload?name=&filename=`
  (no multipart). Splat swap at runtime needs `removeSplatScene(0,false)` +
  `dispose()` before loading the next model, or meshes stack. Full endpoints +
  verified fixes: `dtwin-development/references/in-app-pipeline-and-colmap41.md`.
- **A CUDA trainer needs no framework — read the COLMAP model directly.** A working
  gsplat training script is small enough to write: parse `cameras.bin`, `images.bin`,
  `points3D.bin` with `struct` (no `pycolmap`), build camera-to-world from the COLMAP
  quaternion+translation, init gaussians from the sparse points, and call
  `gsplat.rasterization` in the loop. This sidesteps any training framework's own
  dataset conventions. **`points3D.bin` entries carry a VARIABLE-length track** — read
  the track length and skip `8 * length` bytes per point; a fixed-stride skip corrupts
  every point after the first. Working script: `scripts/train_gsplat_cuda.py`.
- **When porting a splat `.ply` between trainers, check the stored opacities.** Some
  writers store the raw logit (may be negative) and some store the already-sigmoided
  value in `[0,1]`. A reader that unconditionally applies the inverse sigmoid
  double-transforms the second case and the render comes out washed out. Detect the
  range before converting.
- **A hand-written 3DGS `.ply` writer must emit unique `f_rest_*` names.** The SH
  rest coefficients are stored channel-major (`R0..Rk, G0..Gk, B0..Bk`), so the
  property list is a flat range `f_rest_0 .. f_rest_{3*(n-1)-1}`. Emitting them as
  nested `[i, i+1, i+2]` triples duplicates names (`f_rest_1` twice) and a strict
  loader rejects the file. Verify the header before trusting a written splat: count
  `property` lines, assert `len(props) == len(set(props))`, and confirm the count is
  `3 + 3 + 3 + 3*(coeffs-1) + 1 + 3 + 4` for SH degree 3 (62 for degree 3).
- **Opacities must be shaped `(N,)`, not `(N,1)`.** `gsplat.rasterization` asserts
  `opacities.shape == batch_dims + (N,)`; a column-vector parameter raises
  `AssertionError: torch.Size([N, 1])` at the first render call. Keep the parameter
  `(N,1)` for the optimizer if you like, but `.squeeze(-1)` in the forward that feeds
  the rasterizer.
- **A training script must load its data directory the way the OTHER trainer expects.**
  The MLX trainer reads `<data_dir>/sparse/0/`; COLMAP runs commonly write
  `<data_dir>/sfm/sparse/0/`. Pointing one at the other fails as "Loaded 0 points, 0
  cameras" and then a broadcast error deep in the gaussian init — which reads like a
  corrupt model, not a wrong path. Check which layout the dataset actually has and
  link/copy into the expected one before debugging the loader.
- **Write the training loop so it prints an `it/s` rate and a final machine-readable
  RESULT line.** The rate is the deliverable when the purpose is a benchmark, and a
  single RESULT line makes the two-machine comparison mechanical instead of
  eyeballed. Log every N steps with elapsed seconds, not just loss.
- **`torch` from the default index on Linux is CPU-only.** `pip install torch` on a
  Linux box with an NVIDIA card still reports `torch.cuda.is_available() == False`.
  Install the CUDA wheel explicitly (the cu-index URL) and assert
  `torch.cuda.is_available()` plus a real matmul before benchmarking anything — a
  silent CPU fallback makes a GPU comparison meaningless.
- **Report PSNR honestly as a SAME-RENDERER comparison or not at all.** Quality cannot
  be compared by reading each trainer's own reported PSNR: the number depends on the
  renderer, the held-out views, and the loss. To make it meaningful, render BOTH `.ply`
  files through ONE renderer on the SAME set of views against the SAME ground-truth
  images, then quote both. If that was not done, say the speed is proven and the quality
  is not — do not imply equivalence from similar loss curves.
- **Webapp render loop**: start it BEFORE DOM/touch binding so a null-ref can't blank the scene; verify id consistency HTML↔JS.
- **Unity**: keep isolated/removable (`rm -rf unity/`) — user wants "clean install, remove later".
- **Use `sequential_matcher`, not `exhaustive_matcher`, for video**: `exhaustive_matcher` is N² pairs and burned ~4.2h on a 300-frame TESTMALL build. `sequential_matcher` (overlap=10) is ~15× faster. See `references/sequential-matcher-performance.md` for invocation, budget math, and caveats.
- **The MLX trainer is Apple-Silicon-only — moving training to a CUDA box means swapping the trainer, not moving the pipeline.** `splat-apple` (`train_mlx.py`) is MLX/Metal and cannot run on Linux; there is no Metal there. What IS portable is the dataset: `train/<deploy>/images_8/` plus `train/<deploy>/sparse/0/` (COLMAP cameras/images/points3D) are plain files any trainer reads, so the data layout is the stable interface between stages. On an NVIDIA box use a CUDA 3DGS implementation — `gsplat` (nerfstudio's CUDA rasterizer; modern and well-maintained) or the original Inria `gaussian-splatting` repo (older, slower). Never plan this as "move the pipeline"; plan it as a trainer swap behind the same data layout. The payoff is the iteration rate: a discrete NVIDIA card trains at a multiple of MLX-on-M1-Pro it/s, which is what makes the port worth doing. **Three preconditions before attempting it:**
(1) the box needs a CUDA build of the rasterizer AND a CUDA torch — a venv that installed
`torch` from the default index on Linux is CPU-only and reports
`torch.cuda.is_available() == False`, so install the CUDA wheel explicitly; (2) the SfM
stage must work on the box too — `colmap` from a distro package can install and then fail
at runtime (a missing `libPoseLib.so` on Ubuntu), so run `colmap --version` before planning
around it; (3) check the box's free VRAM first, because a resident LLM server may already
hold most of the card. Budget the port as real development — the trainer swap is not a
config change.

## Verify
- SfM: registered-image count + point count in sparse model.
- Train: `results/<deploy>_mlx_cpp_*/ply/<deploy>_final.ply` exists, non-trivial size.
- Web: real browser shows splat (or placeholder) + pin-tap card works.
- Commit after each step (this user: `git -c user.name=maru -c user.email=kingkymaru@gmail.com`).