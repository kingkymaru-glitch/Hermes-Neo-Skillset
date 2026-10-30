---
name: dtwin-development
version: 1
author: hermes
license: mit
metadata:
  hermes:
    tags: [dtwin, digital-twin, gaussian-splat, supersplat, web-ar, qr]
    related_skills: [lunascan-development]
description: DTwin digital-twin splat to SuperSplat to web twin to AR.
---

## When to Use
Load this skill whenever the task touches the DTwin project at `~/DTwin`:
scaffolding, ingest, the splat kitchen, SuperSplat cleanup, the `web/` twin
viewer, the AR upgrade (`app/`), QR shipping (`docs/`), or spinning up a new
deployment (mall / port / substation / water dam). Also load it when reasoning
about DTwin↔LUNASCAN overlap on a shared site (they are complementary layers).

> Server launch/port-confusion + trim/mesh pipeline details: see
> `references/server_and_mesh_ops.md`.
> Parallel-agent (Neo/Trinity/Smith) coordination pitfalls: see
> `references/parallel_handshake_coordination.md`.
> Webapp/viewer debugging (Run does nothing, GLB JSON errors, ffmpeg-in-daemon, stale auto-load): see
> `references/webapp_viewer_debug.md`.
> Trim/Mesh + asset-browser pipeline (per-stage artifacts, src_idx fix, Original/Trimmed
> toggle, 📂 Folder button — all landed 2026-08-16): see `references/trim-mesh-ui-pipeline.md`.

## When to load (detailed)
Any work on the DTwin project at `~/DTwin`: scaffolding, ingest, splat kitchen,
SuperSplat clean, the `web/` twin viewer, AR upgrade (`app/`), QR shipping
(`docs/`), or a new deployment (mall / port / substation / water dam).

## Locked decisions (do not re-litigate without user sign-off)
1. **Web-first.** QR → web twin + pins is the FIRST shippable win (every phone,
   no app, no account, no VPS coverage needed). Native AR (Unity + Lightship
   VPS) is a later *upgrade* at the Decision Gate, not a blocker.
2. **Template + deployment instances.** DTwin = reusable engine. A *deployment*
   is one subject (mall = sample #1; port / substation / water dam = future).
   Each deployment is config under `deployments/<name>/`, never a rewrite.
3. **Cloud kitchen first.** Luma / Polycam / Scaniverse emit raw `.ply`.
   Apple-Silicon MLX 3DGS port is the local/private fallback — GATED (see rules).
4. **SuperSplat cleanup** → compressed `.sog` (browser-based, no install).
5. **Pins are authored data**: `deployments/<deploy>/tags.json`
   `{id, pos:[x,y,z], title, body, media}`. Never hardcode pins in the viewer.
6. **`ingest/` is sacred.** Originals read-only; pipeline never writes there.
7. **VPS engine is per-deployment**, chosen at the Gate (not now): indoor
   (mall/substation) → Lightship VPS; outdoor (park/port/dam) → Geospatial/Lightship.
8. **Ask before installing anything outside Homebrew.**
9. **Default viewer artifact is the `.glb`, not the `.ply`.** The Gaussian-splat `.ply` is the
   source-of-truth fidelity asset; the pipeline converts it post-train to a lightweight point-cloud
   `.glb` (`web/assets/<name>/model.glb` via `tools/ply_to_glb.py`). The `web/` asset browser + build
   panel "View" load `model.glb` (GLTFLoader, POINTS primitive, `KHR_materials_unlit`). MARU's words:
   "i dont want to view the .ply, i want to view the .glb." Do NOT revert the UI to load `.ply` by
   default. If a future task needs the splat viewer, keep `.glb` as the default and add `.ply` as an
   explicit secondary action.

## Hard project rules (enforce every session)
- `git init`; **commit after every successful step** (author maru/kingkymaru@gmail.com).
- NEVER modify/delete files in `ingest/` — originals are sacred.
- After each phase write `PHASE_REPORT.md` (what done, metrics, risks, next step).
- **MLX local-training install is gated**: it needs `pip`/venv (outside Homebrew).
  STOP and ask before creating the venv / pip-installing the MLX 3DGS port.
  Cloud kitchen is the default path.
- Capture is the USER's job (end-effector, on-site). Agent cannot start Phase 1
  without the user shooting + AirDropping footage.
- **Reporting style (MARU):** be terse and plain. When asked "what happened" /
  "is it ok", answer in ≤100 words, simple terms, direct — no essays, no
  over-explanation. Explain the mechanism only when asked HOW. Lead with the
  answer/status, then the one-line fix.

## PARALLEL-AGENT COORDINATION (Neo + Trinity + Smith on one Mac) — read BEFORE every edit
Since 2026-08-15 DTwin runs parallel Hermes agents in the SAME `~/DTwin`
working tree (MARU types in both windows and arbitrates). Neo = this agent
(canonical); Trinity = the parallel instance; Smith = a third worker agent that
may be spun up for a cross-lane task. Neither sees the other's chat; the
ONLY channel is git + the handshake file.
- **STANDING HABIT (MARU, 2026-08-16):** the handshake is NOT optional per-task —
  it is a habit to KEEP ALIVE during concurrent work. On EVERY DTwin turn that
  touches files, FIRST re-read `docs/AGENT_HANDSHAKE.md` + run
  `git log --oneline -5 trinity` + `git branch --show-current` (confirm `neo`),
  THEN claim, THEN edit. MARU explicitly asked Neo/Trinity/Smith to "keep the
  habit of the handshake alive." If you were about to edit without it, STOP and
  reconcile first.
- **ALWAYS read `docs/AGENT_HANDSHAKE.md` first** (Obsidian mirror
  `Projects/DTwin_Handshake.md` is for MARU's visibility only — edit the repo
  copy, then sync). It holds the current REGISTRY of claims + a HANDOFF LOG.
- **Port map (dtwin-development agents, 2026-08-16):** DTwin web server = **8753**
  (authoritative; `~DTwin/server.py`, `directory=ROOT`=cwd). Trinity's sibling
  project TriniD runs its OWN server on **9877** (NOT 8787). **8787 is NOT a DTwin
  port** — it is Hermes' own `msgsrvr` (seen as `localhost:msgsrvr` under `lsof`),
  so do not treat an 8787 listener as a DTwin clash. Before launching any server,
  `lsof -i :<port>` to confirm free; if a stale server is rooted at the wrong cwd
  (e.g. `~/TriniD`), kill it and relaunch from `~/DTwin` (see WRONG-cwd pitfall).
- **Branch isolation**: Neo works on branch `neo`, Trinity on `trinity`. Do NOT
  edit on the wrong branch. Both branches share the disk working tree, so the
  running pipeline artifacts are visible to both — but code edits live on your
  own branch.
- **Claim before you edit**: set your area `WORKING` in the handshake REGISTRY,
  `git add + commit`, THEN edit. When done set `DONE` + a handoff note (asset
  path / API shape), commit again. If the area you want is `WORKING`/claimed by
  the other agent, do NOT touch it — set `WAITING_ON_<NAME>` and pick a free
  area or idle.
- **This repo has NO `origin` remote** (local-only). Coordination is via local
  branches + the handshake; use `git fetch`/`git log <other-branch>` (not
  `git push/pull`) to see the other agent's moves. Stale claims (>24h, no
  commit) are fair game — note the takeover.
- The handshake REGISTRY maps areas to holders: `unity/` AR = Trinity
  (`SplatLoader.cs`, `PinManager.cs` — do NOT touch); `web/` viewer + `tools/`
  pipeline + `server.py` = Neo. `deployments/` + `docs/` = SHARED (commit small,
  check the handshake first).
- Full protocol + a worked example: `references/parallel-agent-coordination.md`.

## Folder contract
| Folder | Role | Mutability |
|--------|------|------------|
| `ingest/<deploy>/<zone>/` | RAW originals (video + .ply from scan app) | **SACRED** |
| `frames/<deploy>/<zone>/` | Extracted stills (only if local training) | Rebuildable |
| `splats/<deploy>/<zone>/` | Raw Gaussian splat from kitchen | Rebuildable |
| `clean/<deploy>/<zone>/` | SuperSplat `.sog` + mesh `.obj` fallback | Release asset |
| `web/` | Reusable web-twin viewer engine (global) | Shipped artifact |
| `app/` | Future AR engine (Unity/Lightship, global) | Shipped artifact |
| `docs/` | Reports, runbooks, QR, feedback | Documentation |
| `deployments/<name>/` | Per-subject: `manifest.json`, `tags.json`, `zones.json`, `qr/` | Config+shipping |

## Reproducible end-to-end pipeline (run ANY new video the same way)
The full ingest→frames→COLMAP→train→ply path was originally run ad-hoc; it is
now a single reusable script so "process this file" is one call. See
`scripts/process_video.sh` — it takes a source .mp4 + a deploy name, extracts
frames, runs COLMAP auto SfM, assembles the `train/<deploy>/` dataset, and is
ready for the MLX training step in `references/local-3dgs-training-mlx.md`.
Reuse it for every new capture; do not re-derive the steps by hand.

### VERIFIED parameterized script + in-app control panel (2026-08-15)
The CURRENT working pipeline is `tools/pipeline.sh`:
`tools/pipeline.sh --video <src.mp4> --name <deploy> --frames N --iters N`
→ publishes a runnable splat at `web/assets/<deploy>/model.ply`. The pipeline
must live IN the webapp with controls: `server.py` (stdlib) serves `web/` AND
drives it (`POST /api/pipeline`, SSE `GET /api/pipeline`, `/api/pipeline/stop`,
`/api/assets`, raw-body `POST /api/upload?name=&filename=` → `ingest/<id>/`);
`web/index.html`+`web/main.js` are the LunaV-family look with a left control
panel (Source upload/path, Parameters, Build with Run/Stop/View Hologram +
live log + progress). Splat swap at runtime needs `removeSplatScene(0,false)` +
`dispose()` first. Details + verified COLMAP 4.1/ffmpeg fixes →
`references/in-app-pipeline-and-colmap41.md`.

## PITFALL — COLMAP 4.1 CLI renames (strict parser; aborts under `set -e`)
Homebrew COLMAP 4.1.0. An unrecognized option aborts the step AND (with
`set -euo pipefail`) kills the whole script silently (no ply). Valid 4.1.0 names:
- `--SiftExtraction.use_gpu` → **`--FeatureExtraction.use_gpu`** (feature_extractor)
- `--SiftMatching.use_gpu` → **`--FeatureMatching.use_gpu`** (exhaustive_matcher)
- mapper: drop the Sift flag; use `--Mapper.num_threads` (`--Mapper.ba_use_gpu` exists).
Verify with `colmap feature_extractor --help | grep use_gpu`. Also COLMAP 4.1
**requires the database's parent dir to pre-exist** (`--database_path
frames/<d>/sfm/db.db` → `Check failed: ...ExistsDir` unless
`mkdir -p "$(dirname "$DB")"`). The old `sample` run dodged both only because
its commands were ad-hoc. Table + transcript: `references/in-app-pipeline-and-colmap41.md`.

## PITFALL — ffmpeg `-vf fps=N` is frames/SECOND, not fraction of source
To sample ~N frames: `output_fps = N / duration_seconds` (via `ffprobe -v error
-show_entries format=duration -of csv=p=0`). Dividing N by the FRAME COUNT is
wrong — a 41s/1250-frame clip gave `fps=0.24` → ~10 frames instead of 300.

## PITFALL — macOS has no `stdbuf`
`stdbuf -oL -eL` does not exist on macOS → a background command gated on it
fails to run. Use `python3 -u` wrappers or accept block-buffering; confirm
progress via `pgrep -fl colmap|train_mlx` + inspecting `frames/`/`results/`,
not a laggy nohup log tail.

## PITFALL — do NOT edit `tools/pipeline.sh` while a build is RUNNING
The pipeline runs under `bash`, which reads the script INCREMENTALLY as it
executes. If you patch `pipeline.sh` mid-run, the live process picks up your
change for the stages it has NOT yet reached (mapping/training/cleanup) →
corruption of the in-flight build. When a pipeline is active (check
`pgrep -f pipeline.sh` / `pgrep -f train_mlx.py`), hold ALL edits until it
finishes; you may only observe (read logs via `curl
http://localhost:8753/api/pipeline/log`, inspect `frames/`/`results/`). If a fix
is urgent, prepare the new script content but do NOT write it until the build
completes.

## WEBAPP ASSET BROWSER — interactive select + delete (committed 2026-08-15)
The Assets panel in `web/index.html` was previously a comma-separated string —
unclickable, no view, no delete. Committed fix on branch `neo` (b0c8f77):
- Backend: `DELETE /api/assets/<name>` removes `web/assets/<name>/model.ply`
  and cleans up the empty deploy dir.
- Frontend: `window.ASSET_ROW(name)` template builds a clickable row per asset
  with **◉ View** (loads splat) and **✕ Delete** (with confirm). Clicking the
  row itself also loads the splat.
- `refreshAssets()` in `main.js` replaces the comma-string with real DOM rows
  via `(window.ASSET_ROW || defaultAssetRow)`.
- CSS: `.asset-row` styling (glass-panel hover, compact, LunaV-family look).
Fallback: if `ASSET_ROW` is not defined (e.g. older cached page), `defaultAssetRow`
renders a clickable row.

## PITFALL — memory / disk accumulation across runs (crash residue)
A crashed/aborted build can leave transient data that fills disk and blocks
future runs. The pre-flight cleanup in `pipeline.sh` handles this, but the
agent must also know what to look for:
- `frames/<name>/` — 400-1000MB per crashed build (images + sfm db)
- `train/<name>/` — 50-100MB per crash (assembled dataset)
- `results/<name>_mlx_cpp_*/ply/` — trainer output dirs; already published as
  `web/assets/<name>/model.ply` but the `results/` copy lingers
- `/tmp/dtwin_*.log` — ~700KB per session; harmless but clutters `/tmp`
- **Orphan processes** — stale `colmap` / `ffmpeg` / `train_mlx.py` not tied to
  any running `pipeline.sh`. A crashed build's children survive as zombies;
  verify ancestry with `pstree -p <pid>` before killing. Do NOT kill processes
  that descend from the active `pipeline.sh`.
- **Pre-flight cleanup (committed b7bf4e0):** every `pipeline.sh` run starts
  with `rm -rf frames/$NAME train/$NAME` (idempotent), so a stale deploy ID
  never interferes with the next build.
- **Post-publish cleanup:** after the .ply is copied, `rm -rf frames/$NAME
  train/$NAME $RESULT_BASE/${NAME}_mlx_cpp_*` frees the bulk of disk.
- **EXIT trap:** `trap 'rm -rf frames/$NAME train/$NAME; rm -rf $RESULT_BASE/${NAME}_mlx_cpp_*; exit 1' EXIT`
  guarantees transient dirs for THIS run's $NAME are wiped even on
  crash/Ctrl-C/SIGTERM. Does not affect other builds' data.

## PERFORMANCE — `sequential_matcher` committed, the default for video (2026-08-15)
The biggest single processing-time win from the 2026-08-15 production pass.
`colmap exhaustive_matcher` brute-force matches EVERY image pair = **N²** pairs
(300 frames → 44,850). On a real 300-frame build (TESTMALL) it burned **~4.2h**
in matching alone and was still on block 31/36 when observed. DTwin's input is
always a **video** (temporally ordered, consecutive frames overlap), so
exhaustive is massively wasteful.

**Fix committed on branch `neo` (2026-08-15, commits 0cb9ba9 + fedaef3):**
`tools/pipeline.sh` now uses `colmap sequential_matcher` by default:
- Pairs: 44,850 → 3,000 (overlap=10) = **~15× fewer**
- Matching estimate: ~4.2h → **~8-10 min**
- `MATCH_TO` budget updated from `N*N*0.12 + 120` (~3h for 300 frames) to
  `N*10*0.3 + 120` (~17 min), so a real hang still fails fast.
- Invocation: `--SequentialMatching.overlap 10 --SequentialMatching.loop_detection 1 --FeatureMatching.use_gpu 0`
- Full detail, budget math, and "when NOT to use" notes:
  `references/sequential-matcher-performance.md`.

## PERFORMANCE — `MAP_TO` budget fixed (2026-08-15, commit 67ca752)
The mapper stage timeout was set to `N*1.5 + 300` = 750s for 300 frames — too
small for COLMAP mapper + global bundle adjustment on CPU. Every build (dji_test,
pontoon, TESTMALL) timed out at "Retriangulation and Global bundle adjustment"
after registering 0–168 images. Fixed to `N*7 + 600` = 2700s (~45 min) for
300 frames, matching observed CPU mapper + BA timing.

## CAVEAT — the perl alarm-kill timeout may NOT fire on long COLMAP matchers
The portable `perl -e 'alarm shift; exec @ARGV'` helper sets a SIGALRM then
`exec`s the child (same PID → the matcher's parent looks like `bash`, which is
expected). But observed: an `exhaustive_matcher` ran **4h15m**, far past its
~3.03h `MATCH_TO` budget, and was NOT killed — the alarm did not deliver a
fatal SIGALRM to the long-running colmap (colmap may reset/ignore it, or the
alarm is lost across the busy exec'd process). So the timeout is NOT a reliable
hang-stopper for COLMAP matching. Implications: (1) prefer `sequential_matcher`
so the stage is too fast to need killing, and (2) if you rely on the timeout,
test it against the ACTUAL tool (a `sleep` test passing does not prove colmap
gets killed) before trusting a huge `MATCH_TO` bound. Do NOT raise `MATCH_TO`
to "give it more time" — that just tolerates a hang; fix the matcher instead.

## Production hardening of the pipeline + server (2026-08-15, all committed)
When the founder says "optimize code/pipeline/memory, test for production",
these are the concrete, verified fixes. Details + transcript →
`references/pipeline-production-hardening.md`. Live crash/verification evidence
(Metal GPU concurrency crash, portable-timeout timings, server pipe-drain check)
→ `references/gpu-concurrency-and-timeout-verification.md`.
- **PITFALL — GNU `timeout` does NOT exist on macOS** (`timeout: command not
  found` → the hardened COLMAP/train step aborts). `gtimeout` (coreutils) is
  not installed either. Portable fix WITHOUT external deps: a perl alarm-kill
  helper that sets `alarm N` then `exec`s the child, so it dies after N seconds:
  `perl -e 'alarm shift; exec @ARGV' <secs> <cmd...>`. Verified: `alarm 2` on
  `sleep 30` dies in 2.0s (exit 142=SIGALRM). Use it to bound every COLMAP stage
  + training so a hang can't stall the server. Fallback order: `gtimeout` →
  `timeout` → perl.
- **PITFALL — RESULT_BASE path:** `train_mlx.py` writes its output to
  `cwd/results/<name>_mlx_cpp_<ts>/ply/` (cwd-relative), NOT
  `tools/splat-apple/results/`. If the pipeline script points its "locate ply"
  search at the wrong base it returns nothing → `ERROR: training produced no
  .ply`. Set `RESULT_BASE="results"` (relative to repo root, since the script
  `cd`s there).
- **PITFALL — COLMAP image_path must NOT contain the database.** If
  `--database_path frames/<d>/sfm/db.db` and `--image_path frames/<d>` (the
  whole dir), COLMAP scans `db.db`/`db.db-shm`/`db.db-wal` as candidate images
  (`BITMAP_ERROR: Failed to read the image file format` noise). Fix: keep images
  in `frames/<d>/images/` and the db+sparse in `frames/<d>/sfm/` — separate the
  image dir from the working dir. Also means cleanup must `rm -rf frames/<d>`
  (the parent), not just the images subdir.
- **PITFALL — server pipe-full deadlock.** A pipeline started via the webapp uses
  `subprocess.Popen(stdout=PIPE)`; if the browser tab closes / SSE drops, NOBODY
  drains stdout and once the ~64KB OS pipe fills the child blocks forever =
  hung pipeline. Fix: a background reader thread that ALWAYS drains the child's
  stdout into a ring buffer (`deque(maxlen=N)`); the SSE stream + a
  `GET /api/pipeline/log` endpoint both read from it, so a reconnecting client
  gets history and the child never stalls. This is a silent production hang.
- **Preflight + idempotence + cleanup:** check free disk (≥4GB) BEFORE starting
  and abort cleanly (`df -k /` → KB → multiply by 1024 for bytes; label GB
  correctly or it prints nonsense like "22067 GB"); short-circuit if the target
  `web/assets/<name>/model.ply` already exists; after a successful publish
  `rm -rf frames/<name> train/<name>` (transient ~1.4GB+282MB per build) so disk
  never fills across repeated builds.
- **Server robustness:** atomic spawn under a lock, a double-launch guard (refuse
  a 2nd pipeline while ANY `pipeline.sh` runs, including one launched outside the
  server via `pgrep -f`), graceful SIGINT/SIGTERM that terminates the child first,
  2GB upload cap, filename sanitization.
- **PITFALL — Metal GPU concurrency crash (hit live, real).** Two MLX splat
  training jobs running at the same time on ONE Apple-Silicon Mac crash the GPU:
  the second job dies with
  `[METAL] Command buffer execution failed: Impacting Interactivity
  (kIOGPUCommandBufferCallbackErrorImpactingInteractivity)` then
  `libc++abi: terminating due to uncaught exception ... std::runtime_error`.
  This fired when a second build's training started while the first was mid-train.
  Fix: a **GPU guard** at the top of the training step —
  `pgrep -f "train_mlx.py" && { echo "ERROR: another training is using the GPU"; exit 7; }` —
  so the pipeline refuses a second concurrent training instead of crashing. The
  crash is isolated (the first job is unaffected; the hardened script detects the
  abort and exits cleanly), but it wastes a full COLMAP run, so guard, don't
  retry-and-hope. Implication: **run builds ONE at a time**; the double-launch
  server guard covers webapp-driven runs, the GPU guard covers terminal-driven
  runs.
- **Accurate progress in the webapp:** don't count `>>` markers / a fixed number
  (the pipeline has ~11 stages, not 6). Map `>>` stage markers to a stage list and,
  during training, parse the real `(\d+)/<iters>` from the MLX progress line for a
  true % (use the configured `--iters`, not hardcoded 2000).

## Phase runbook (copy-paste agent prompts)
- **P1 Capture(you)+Ingest(agent):** ffprobe metadata; ffmpeg-extract frames
  @2fps → `frames/<deploy>/<zone>/`; for each .ply log splat count+size (plyfile);
  update `deployments/<deploy>/manifest.json`. Report what arrived.
- **P2 Kitchen+Pre-clean:** (gated) venv+MLX train → `splats/<zone>.ply`; if MLX
  fights, STOP → cloud fallback. `clean_splat.py` (Open3D) bbox crop + outlier
  removal + drop opacity<0.15 → `clean/<zone>_clean.ply`; mesh fallback
  poisson → `clean/<zone>_mesh.obj`. You: SuperSplat pass → `.sog`. Agent:
  validate <60MB, stage.
- **P3 Web Twin+Pin Editor (first ship):** `web/` mobile viewer (three.js/
  PlayCanvas + splat renderer) loads `.sog`; pins from `tags.json` as yellow
  sprites, tap→card. Password-gated EDIT MODE: tap scene drops/moves pin,
  downloads updated `tags.json`. Serve locally; give LAN URL for iPhone test.
- **Decision Gate (you+me):** web twin good on-site? → Lite (ARKit Quick Look
  USDZ) or Full (Unity+Lightship VPS, P4).
- **P4 AR (upgrade):** Unity LTS (Apple Silicon) + ARFoundation + Lightship VPS;
  PinManager reads `tags.json`; deep link `?zone=`. Mesh fallback if splat unstable.
- **P5 QR Shipping:** Netlify per-zone `/z/<zone>`; `brew install qrencode`;
  QR PNGs; A5 sign PDF; redirect stub.
- **P6 Operate:** feedback button → `docs/feedback.md`; daily `TODO.md`;
  auto-fix trivial (typos, pin nudge <10cm); queue arch changes for review.

## PITFALL — Open3D 0.18 on Apple Silicon segfaults (blocks P2 clean)
`clean_splat.py` statistical-outlier removal uses Open3D's KD-tree / `search_knn`
path, which **segfaults on Apple Silicon** (`search_knn_vector_3d`). Same bug
LUNASCAN hit. Symptom: process dies with no Python traceback during outlier
removal / normal estimation.
**Fix (validated in LUNASCAN):** auto-radius normal estimation (`estimate_normals`
with no explicit radius) and avoid direct KD-tree calls; do pruning without
`search_knn_vector_3d`. Prefer numpy/array-based denoise + bbox crop. See
`references/open3d-apple-silicon.md`. Never reintroduce direct KD-tree calls.

## PITFALL — web viewer goes blank ("I see nothing")
The `web/` twin viewer has FIVE distinct blank-canvas failure modes. Symptom
split: if the HTML overlays (top bar "DTwin sample", "Placeholder hologram",
status pill) still show but the 3D scene is empty, the JS module loaded but the
canvas isn't drawing. If even overlays are missing, the ES module aborted before
first paint. Full checklist + verified fixes + on-screen error-overlay snippet:
`references/web-viewer-blank-debug.md`. The self-diagnosing `web/diag.html`
(WebGL + three + OrbitControls + splat + render-test + ply-reach probes, printed
on screen as colored check/cross lines) is the FASTEST way to pinpoint which
cause bit — have the user open it and read back the first red line.
1. **Missing `<canvas id="view">` in index.html** — `getElementById('view')`
   returns null → three.js renders to a DETACHED canvas → blank on real browser,
   no error. THE most common real-browser blank. Add the canvas + full-screen CSS.
2. **Null-DOM throw before render loop** — `getElementById('WRONG-ID')` → throw
   aborts the module so the render loop (scheduled last) never runs. Align ids;
   guard every DOM write; start the loop BEFORE DOM binding.
3. **CDN module 404 / blocked** — importmap points at a bad/wrong CDN path or
   network blocks jsdelivr → whole module fails to load → silent blank. Vendor
   three.js + OrbitControls + gaussian-splat viewer into `web/vendor/` and point
   the importmap at `./vendor/...` (verified: fully offline, no CDN).
4. **WebGL-catch re-throw** — only fires when no GL context (headless); guard the
   catch DOM write too. Environmental, not an app bug on a real browser.
5. **importmap `three/addons/` PATH MISMATCH (local 404 aborts the whole module).**
   The blank that bit in the "run the same pipeline on a new file" session. On
   the user's REAL browser (WebGL2 OK, three loads) the symptom is: a red cross
   "OrbitControls import FAILED: Failed to fetch dynamically imported module:
   .../web/vendor/three-addons/controls/OrbitControls.js" then total blank.
   Cause: importmap maps `"three/addons/": "./vendor/three-addons/"` and main.js
   imports `three/addons/controls/OrbitControls.js` → resolves to
   `vendor/three-addons/CONTROLS/OrbitControls.js`. If the file was saved one
   level too shallow (`vendor/three-addons/OrbitControls.js`) → 404 → the ENTIRE
   main.js ES module aborts → no render loop → blank. Fix: `mkdir -p
   vendor/three-addons/controls && mv OrbitControls.js controls/`. ALWAYS nest
   vendored addons under the exact subpath the importmap + import statement
   expect (match `three/addons/<rest>` → `vendor/three-addons/<rest>`). Full
   recipe + the `diag.html` that catches it: `references/importmap-addons-pitfall.md`.

## PITFALL — "loadSplat is not a function" + "Failed to resolve module specifier" (3-part chain, 2026-08-15)
When the Asset panel's View button throws `Uncaught TypeError: window.loadSplat
is not a function` AND the console also shows `Splat load failed: TypeError:
Failed to resolve module specifier 'vendor/gaussian-splats-3d.module.js'`, it is
ONE chain, not two bugs. Fix all three links or it "persists":

1. **Bare module specifier in `import()` fails.** `main.js` sets
   `const SPLAT_PACKAGE = 'vendor/gaussian-splats-3d.module.js'` and does
   `await import(SPLAT_PACKAGE)`. A bare specifier (no leading `./` or `/`) is
   NOT in the importmap and NOT resolvable by the stdlib server → the dynamic
   import throws → **the entire `main.js` ES module aborts before it reaches the
   `window.*` exports at the bottom**. Fix: `'./vendor/gaussian-splats-3d.module.js'`
   (relative URL). The importmap only needs entries for `three` and
   `three/addons/`; it does NOT need a gaussian-splats entry once the path is
   relative.
2. **Module-scoped functions are invisible to inline `onclick`.** `loadSplat`,
   `setStatus`, `placeholder` live inside `main.js`'s IIFE. Inline handlers in
   `index.html` (`window.ASSET_ROW` template) run in GLOBAL scope and cannot see
   them → `window.loadSplat is not a function` even after the module loads. Fix:
   at the bottom of `main.js` export them —
   `window.loadSplat = loadSplat; window.setStatus = setStatus;
   window.placeholder = placeholder;` — and call `window.loadSplat(...)` /
   `window.setStatus(...)` (NOT bare `loadSplat`) from every inline handler.
3. **Browser caching masks the fix ("error persisted" after the code was already
   correct).** The stdlib server sends `Last-Modified` but NO `Cache-Control`, so
   the browser serves a stale cached `main.js`/`index.html` and you debug against
   phantom old code. Verify what's actually served with
   `curl -s http://localhost:8753/web/main.js | grep SPLAT_PACKAGE` BEFORE assuming
   the fix didn't take. Fix: override `end_headers()` in the `Handler` to always
   send `Cache-Control: no-store, no-cache, must-revalidate` (it's a local dev
   server — caching is never wanted), restart the server (and note: `pkill -f
   "python3 server.py"` can MISS an old server whose command line differs — confirm
   with `lsof -iTCP:8753 -sTCP:LISTEN` and `kill -9` the PID, then relaunch). Then
   have the user hard-refresh (Cmd+Shift+R).
Full transcript + the exact console errors: `references/module-specifier-and-browser-cache.md`.

## PITFALL — `addSplatScene` throws / splat invisible (3 post-module-load causes, 2026-08-15)
Once the module loads and `loadSplat` runs, there are THREE more distinct failure
modes (separate from the blank-canvas family in `references/web-viewer-blank-debug.md`).
All three were hit and fixed this session. Full recipes + verification:
`references/web-viewer-splat-loading.md`.
1. **`DataCloneError: SharedArrayBuffer transfer requires self.crossOriginIsolated`.**
   The gaussian-splats-3d sort worker uses `SharedArrayBuffer` (defaults
   `sharedMemoryForWorkers:true`), which needs a **cross-origin-isolated** page. Fix
   server-side: `end_headers()` must send `Cross-Origin-Opener-Policy:
   same-origin` + `Cross-Origin-Embedder-Policy: require-corp` on every response.
   Belt-and-suspenders client-side: `new mod.Viewer({ gpuAcceleratedSort:true,
   sharedMemoryForWorkers:false })`. Without this the splat silently never renders
   (placeholder stays). Verify headers with `curl -sI …/web/index.html | grep -i cross-origin`.
2. **`scene.fog` hid the splat after camera auto-framing.** `new THREE.Fog(0x0b0e13,
   6, 22)` — far-plane 22u + fog color == background → once `frameCameraToSplat()`
   moves the camera out (each COLMAP capture has its own coord space/scale), the
   whole splat is past the fog far-plane = invisible. Fix: delete `scene.fog`.
   Add `frameCameraToSplat(viewer)` (call it right after `addSplatScene`) that
   reads `viewer.splatMesh.computeBoundingBox(true)` (THREE.Box3) and fits the
   camera — a fixed camera tuned for one capture shows others blank/microscopic.
3. **Startup auto-load hardcodes the deleted `sample`.** `const MODEL_URL =
   'assets/sample/model.ply'` + top-level `loadSplat(MODEL_URL)` 404s on every
   page load once `sample` is removed. Fix: default `MODEL_URL` to null, then
   auto-load the first asset from `GET /api/assets`, or honor `?deploy=`/`?model=`.
   When deleting a broken asset, `rm -rf web/assets/<name>` AND confirm
   `/api/assets` no longer lists it.

## PLY → GLB conversion stage (added 2026-08-15, after commit e5676f2)
DTwin now emits a SECOND artifact after the splat: a lightweight **point-cloud `.glb`**
derived from the Gaussian `.ply`. This is the portable preview / AR artifact (opens in
Three.js, Unity, and iOS AR Quick Look without the gaussian-splats library).

- **Converter:** `tools/ply_to_glb.py <in.ply> <out.glb> [--max-points N]` (numpy only,
  runs in the splat-apple venv). Reads the Gaussian-splat .ply (x,y,z, f_dc_0..2, opacity,
  scale, rot), one point per Gaussian at its center, colored by SH DC term
  `c = 0.5 + SH_C0*f_dc` (SH_C0 = 1/(2*sqrt(pi))). Writes glTF 2.0 binary: POSITION (VEC3
  float) + COLOR_0 (normalized UNSIGNED_BYTE, 3 bytes/vertex → small) + primitive mode 0
  (POINTS) + `KHR_materials_unlit` (renders unlit in AR/Three).
- **Wired:** `tools/pipeline.sh` runs it right after publishing the splat (after `DONE $OUT`,
  before cleanup). Output `web/assets/<name>/model.glb`. Caps at `--max-points 200000`.
  Graceful: if venv missing or converter fails, splat still ships (WARN, not ERROR).
- **Size:** dji_test 79,367 Gaussians → 1.19 MB glb vs 5.1 MB splat (~4× smaller).
- **Validation:** assert `blob[:4]==b'glTF'`, version 2, total == file len, each accessor
  count == vertex count. Full recipe + GLB byte-layout: `references/splat-to-glb-conversion.md`.
- **UI DONE (2026-08-15, commit b301b53):** the asset browser now shows + loads the `.glb` as the
  default viewer. `web/main.js` vendored `three/addons/loaders/GLTFLoader.js` (local, no CDN); added
  `loadGlb(url)` (loads glb via GLTFLoader, `frameCameraToObject` to fit camera to its Box3, disposes any
  prior splat/glb) + `frameCameraToObject(obj)`. Auto-load, `defaultAssetRow` click, and build-panel
  `viewBtn.onclick` all now target `assets/<name>/model.glb` (not `.ply`). Asset row shows a gold "glb"
  tag; `window.loadGlb` exposed for inline handlers. `.ply` is still produced by the pipeline (fidelity
  source) but the UI no longer opens it. Still-open: no "Download .glb" button in the row (grab the file
  from `web/assets/<name>/model.glb` directly) — add on next pass if MARU wants it.

### .ply format scope — what the DTwin viewer can actually open
The DTwin web viewer uses gaussian-splats-3d, which only reads **Gaussian-splat .ply**:
vertex props `x,y,z, opacity, scale_0..2, rot_0..3, f_dc_0` (+ optional `f_rest_*` for
higher SH). Exactly the .ply DTwin's own pipeline produces → opens fine (dji_test).
A **generic .ply does NOT open**:
- a mesh .ply (vertices + faces, maybe r,g,b) from Blender/MeshLab/scan app
- a raw point-cloud .ply (x,y,z,r,g,b)
The lib can't find opacity/scale/rot → throws "Could not load file". To open ANY .ply, add
a second loader path in `loadSplat`: detect format, route Gaussian .ply to the splat viewer,
route plain mesh/pointcloud .ply to THREE.js `PlyLoader`. That is a FEATURE ADD, not a fix.

## Verification reality (WebGL apps — do NOT fake)
Headless Chrome on this Mac CANNOT init WebGL (every GL flag combo tried yields a
null context). So headless screenshots cannot prove a splat renders — never claim
"verified" from one. MARU rule: **"done" = visibly on screen in a REAL browser.**
Prove by: static checks (served HTML has the canvas, JS has no null-DOM writes,
module files return 200), an on-screen error overlay (window error +
unhandledrejection → painted div) so failures show as readable text, then ask the
user to hard-refresh and report. A red error box on their screen is the real
diagnostic. See `references/web-viewer-blank-debug.md`.

## PITFALL — pipeline EXIT trap DELETES the finished run's raw data (hit live)
`pipeline.sh`'s `trap ... EXIT` + post-publish `rm -rf` wipe `frames/<name>`,
`train/<name>`, AND `results/<name>_mlx_cpp_*` on EVERY exit — including a
*successful* run. So once a build finishes, the only surviving artifact is what
the script already copied to `web/assets/<name>/model.ply` (+ `model.glb`). The
COLMAP dataset and trainer `results/` are GONE (this bit the dji_701 run in-session:
the job completed, then its `train/dji_701` + `results` vanished — only the
published `web/assets/dji_701` survived). Implications:
- If you want to **re-train / resume / inspect** a finished build, the inputs are
  gone → re-run the whole pipeline, or copy `train/<name>` + `results/...` out
  BEFORE the script exits. For crash-safety INSIDE a run, the trainer checkpoints
  (`--checkpoint_every`) land in `results/<name>_mlx_cpp_*/ply/` which the trap
  also deletes — so copy the best/final ply to `web/assets/<name>/` as the run ends.
- Don't assume `train/<name>/sparse/0/*.bin` still exists after a prior build.
  Use a dataset whose `train/<name>` is current (e.g. `train/sample` survived
  because it was a different NAME than the active build).

## PITFALL — server.py launched from the WRONG cwd serves the wrong assets root
`server.py` uses `directory=ROOT` = the dir it was started in (`os.path.dirname`).
If launched from a different folder (in-session: a stale instance was rooted at
`~/TriniD`, listening on **8790**, and `/api/assets` listed TriniD's assets, not
dji_701), the webapp silently shows the wrong project. Symptom: `/` returns 200
but the model `/web/assets/<name>/model.*` 404s, and `/api/assets` lists the wrong
names. Diagnosis + fix:
- `lsof -iTCP:8753 -sTCP:LISTEN` to find the PID; `pwdx <pid>` (or `lsof -p <pid> | grep cwd`)
  to see its cwd. If it's not `~/DTwin`, it's wrong.
- Kill it (`kill -9 <pid>` — `pkill -f server.py` can miss a differently-named
  interpreter) and relaunch from the DTwin root: `cd ~/DTwin && <python> server.py`
  (the documented port is **8753**). Verify: `curl -s localhost:8753/api/assets`
  lists `dji_701,dji_test`, and the model ply returns 200.
- There may be MORE THAN ONE server process (the stale 8790 + the correct 8753);
  check both ports before concluding "it's down".

## PITFALL — "where does DJI_701 sit in the pipeline?" (asset-level answer)
A named capture (e.g. `dji_701`) is NOT raw video or mid-train — it is a
**PUBLISHED ASSET** (the final pipeline stage). The chain:
`capture(.mp4) → COLMAP SfM → MLX Gaussian training → model.ply` (splat,
N gaussians, ~12MB) `→ model.glb` (web/AR artifact). So `dji_701` lives at
`web/assets/dji_701/` with `model.ply` (source-of-truth splat) + `model.glb`
(portable artifact the viewer loads). If the user "can't see" it: it is almost
always the WRONG-cwd server pitfall above (a stale server rooted at `~/TriniD`
showed TriniD's assets, not dji_701) — kill + relaunch from `~/DTwin`, then
`curl -s localhost:8753/api/assets` must list `dji_701`.

## Trim + Mesh on a published asset (on-demand, NOT automatic)
MARU asked to "have it undergo the trim and mesh." Trim is **interactive only**
(webapp marquee box → `POST /api/trim` writes `model_trimmed.ply`); no auto-trim.
The MESH step runs headless from the splat OR the trimmed cloud. **Every stage is
now persisted in the model folder** (MARU rule 2026-08-16: "every output saved on
that particular model folder so I can adjust it later"). Full reference:
`references/trim-mesh-ui-pipeline.md`.

Asset-folder contract (`web/assets/<name>/`):
`model.ply` (original splat) · `model_trimmed.ply` (after box-deletes) ·
`model.glb` (triangle mesh, default viewer artifact) · `model_points.ply`
(sampled+normal cloud) · `model_raw.ply` (**raw Poisson surface, pre-decimation —
inspect in Blender/MeshLab**) · `model_mesh.ply` (final decimated mesh) ·
`model_mesh_manifest.json` (params+artifact map) · `train.log` (pipeline tee).

- **Server endpoint:** `POST /api/mesh {"name","source":"original|trimmed"}` →
  Poisson (`depth 7`, `sample 40000`) → quadric decimate (≤`max_faces`) → glb.
  `source=trimmed` requires `model_trimmed.ply` (400 otherwise). Persists
  points/raw/mesh + manifest. `GET /api/mesh/log` SSE.
- **Direct CLI (verified dji_701 / CMPK1):** mesh-venv = py3.11 + Open3D 0.19
  (0.18 segfaults on Apple Silicon).
  ```bash
  cp web/assets/<deploy>/model.glb web/assets/<deploy>/model_pcd.glb   # keep splat
  tools/mesh-venv/bin/python tools/splat_to_mesh.py \
      web/assets/<deploy>/model.ply web/assets/<deploy>/model.glb \
      --max-faces 20000 --max-mb 30 --depth 7 --sample 40000
  ```
- **Gotchas fixed 2026-08-16 (see reference for detail):**
  1. Box-select was bound to the sidebar panel, not the `#view` canvas → dead
     select. Bind to canvas + suspend OrbitControls during drag.
  2. `assets/[object Object]/model.ply` = `/api/assets` returned objects
     `{name,has_trimmed}` but row render passed the object as a string. Normalize
     to `.name`.
  3. Trim delete no-op = `trim_splat.py extract` never emitted `src_idx` (real
     splat index per sampled point) AND `/api/points` reloaded the ORIGINAL cloud.
     Now `src_idx` is sent and both `/api/points`+`/api/trim` read the current
     (trimmed) cloud so deletes accumulate.
  4. Poisson surface was built in memory and discarded — now `model_raw.ply` is
     saved so mesh quality is inspectable/reworkable.
- **Assets panel actions (2026-08-16):** ◉ View · 📂 Folder (`GET /api/open-folder`
  → macOS `open`, traversal-guarded) · ✕ Delete.

## PITFALL — the mesh-venv must NOT be committed to git
`tools/mesh-venv/` (18,967 files, ~44MB) was committed by accident on branch
`neo` and will bloat `origin` on push. Fix before any `git push origin neo`:
```bash
cd ~/DTwin
git rm -r --cached tools/mesh-venv
printf '\n# mesh python venv (rebuild: python3.11 -m venv tools/mesh-venv && tools/mesh-venv/bin/pip install open3d numpy plyfile)\ntools/mesh-venv/\n' >> .gitignore
git add .gitignore && git commit -q -m "chore: stop tracking mesh-venv (rebuild via pip)"
```
The venv STAYS on disk and keeps working — only git stops tracking it. Rebuild
recipe is in the `.gitignore` comment so a fresh clone can recreate it. Always
add a venv to `.gitignore` the moment you create it; the repo's `.gitignore`
already excludes `tools/splat-apple/` but NOT `tools/mesh-venv/`.

## Local 3DGS training (MLX/Metal, Apple Silicon) — verified recipe + hardening
The MLX gate (see Hard rules) was cleared when the user said "process to get the
ply locally". The working trainer is `ghif/splat-apple` (MLX backend, Metal).
Full step-by-step, data layout, and gotchas: `references/local-3dgs-training-mlx.md`.
Training hardening (checkpointing + resolution ramp + densification + SH degree),
MLX 0.30.6 API workarounds, and the validated test harness:
`references/mlx-densify-sh-port.md`.
Key points: venv + `pip install -r requirements.txt`; build BOTH C++ extensions
(`setup.py build_ext` AND `setup_mlx.py build_ext`) or import fails with
`ModuleNotFoundError: torch_gs._C`; data dir needs `sparse/0/{...bin}` +
`images_8/` with frame names matching COLMAP; `train_mlx.py --rasterizer cpp`;
output `results/.../ply/sample_final.ply` (valid 3DGS schema for the web viewer).
Still ASK before each new venv/pip install (gate is per-session, not permanent).

## Relationship to LUNASCAN (complementary, do not duplicate)
LUNASCAN = aerial DRONE photogrammetry → OpenDroneMap mesh `.glb` (desktop pro
survey). DTwin = ground PHONE walk-around → Gaussian splat `.sog` (web/AR twin).
Pair both on the same site: LUNASCAN top-down mesh + DTwin walkable splat twin.
The Open3D Apple-Silicon fix is shared — see `lunascan-development` for the deep
writeup; DTwin reuses the same workaround in its clean step.