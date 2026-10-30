---
name: lunascan-development
description: Cross-cutting LUNASCAN development patterns — project structure, dependency quirks, testing conventions, and shared pitfalls across all batches.
---

## When to load

Working on any LUNASCAN module (ingest, masking, sfm, export, storage, pipeline). This is the cross-cutting umbrella; load alongside the per-batch skill if one exists.

## Project structure

```
~/LUNASCAN/                    # repo root (NOT ~/Documents — macOS TCC blocks
                               #   Finder-launched apps there; MARU's repos live in $HOME)
  lunascan/
    ingest/                     # Batch 1 — VideoToolbox decode + keyframes
    masking/                    # Batch 2 — CoreML dynamic object removal
    models/                     # Bundled ML models (yolov8n-seg.pt)
    pipeline.py                 # 4-batch orchestrator (ingest→mask→ODM→optimize)
    odm.py                      # Batch 3+4 — OpenDroneMap (Docker) reconstruction
    docker_util.py              # ensure_docker_running() — auto-starts Docker Desktop
    optimize.py                 # Batch 5 — shell out to Node glb optimizer
  tools/3d-optimize/            # Node.js glb optimizer (gltf-transform + meshopt + draco3d + sharp)
  app/                          # Desktop GUI wrapper (PySide6): worker.py, main_window.py, run.py
  tests/                        # test_ingest, test_masking, test_pipeline, test_odm_telemetry,
                               #   test_odm_security, test_docker_util
  build_app.py                  # PyInstaller macOS .app/.dmg builder
  setup.py                      # [gui] extras: PySide6, pyinstaller
```

**DEAD MODULES DELETED (2026-08-10, commit `d161d76`)** — do NOT re-add or import:
`lunascan/sfm/`, `lunascan/export/`, `lunascan/storage/`, `app/publish.py`,
`lunascan/pipeline.py::_upload_to_r2`, `rover_body.py`, `scripts/sfm_speedup_benchmark.py`.
The ODM docker engine (`lunascan/odm.py`) replaced COLMAP SfM + the old export/storage/R2 paths.
`setup.py` console_scripts now only: `lunascan-pipeline`, `lunascan-ingest`, `lunascan-mask`, `lunascan-gui`.

## Dissection + security hardening (2026-08-10)

Two passes reshaped the codebase — read before any further refactor:
- **Dead-code dissection** (commit `d161d76`): method + rebuild gotchas in
  `references/dead-code-dissection.md`. Validated path is `ingest→masking→odm→optimize`.
- **ODM docker security hardening** (commit `4e2f8d5`): SEV-1 read-only image mount + separate
  writable output, SEV-2 `--odm-image` allowlist (no global mutation), SEV-3 digest-pinned image,
  BUG-2 `/tmp` default removed, BUG-4 `is_valid_glb()` gates degraded-success. Full writeup +
  test contract in `references/odm-docker-security-hardening.md`. Suite: 66 tests (was 51).

Python 3.9.6 in `.venv/`. All test/CLI commands run from repo root with `.venv/bin/python`.

## Dependency quirks

- **boto3 1.42**: `ClientError` inherits `Exception`, NOT `BotoCoreError`. Catch both explicitly: `except (BotoCoreError, ClientError, OSError)`.
- **Open3D 0.18 on Apple Silicon**: `search_knn_vector_3d` segfaults. Work around with auto-radius normal estimation (`estimate_normals` with no radius) + fallback colour transfer that avoids the KD-tree call. The export module already does this — don't reintroduce direct KD-tree calls.
- **PyAV**: Use `hwaccel="videotoolbox"` on macOS; fall back to software silently.
- **ultralytics**: Works on Python 3.9. Uses MPS backend auto-detected on Apple Silicon.

## Pipeline integration pitfalls

The `pipeline.py` orchestrator calls sub-module CLIs via their `main(argv)` functions. Every `_run_*` function constructs an `argv` list that must match the target CLI's argparse exactly. Common traps:

### 1. Keyframe file-extension mismatch (`*.jpg` vs `*.png`)

Ingest CLI writes keyframes as `.jpg` (`lunascan/ingest/cli.py` line 82). Pipeline and worker MUST glob `*.jpg`, NOT `*.png`. This mismatch causes "No keyframes extracted — aborting" even when ingest succeeds. **When changing the ingest output format, grep both `pipeline.py` AND `app/worker.py` for the corresponding glob and update both.** Test fixtures in `tests/test_pipeline.py` also create dummy keyframes — update those to match.

### 2. `_run_masking` arg naming: `--keyframes` not `--input`

The masking CLI (`lunascan/masking/cli.py`) expects `--keyframes` (required), not `--input`. The ingest and export CLIs use `--input`; masking uses `--keyframes`. Check each sub-module's argparse before wiring a `_run_*` function.

### 3. `--classes` is comma-separated, not multiple args

The masking CLI's `--classes` takes a single comma-joined string (`"person,car,bird"`). Passing each class as a separate argv element silently interprets only the first as `--classes` and treats the rest as unrecognized positional args.

### 4. Overlap default: tune it, don't guess

The pipeline's `--step-sec` is passed as `--overlap` to the keyframe selector. The keyframe threshold is `(1 - overlap) * 255`. At `overlap=1.0`, threshold=0 and **every frame is kept** — memory explosion. At `overlap=0.6`, threshold=102, which on stable drone footage can prune too aggressively (1 keyframe from 1843 frames — useless for SfM).

**2026-08-10 CORRECTION (commit `b0aee7f`):** the CLI pipeline's `--overlap` DEFAULT was `0.6` — which on the 703 flight kept exactly **1 keyframe out of 1842**, making Batch 3 (ODM) fail with 1 image ("odm exit 1" in 9s). The GUI worker hardcodes `0.95` so GUI runs worked; CLI runs silently broke. **Fixed: `--overlap` default is now 0.95** and the dead `--step-sec` flag (old name, never referenced) was removed. The old help text was BACKWARDS ("Higher=prune more" — actually higher overlap = LOWER threshold = MORE frames kept).

**Calibrated default: 0.95** (threshold=13). Real-world results on a 4K 30fps DJI drone video (~1 min, stable pan):

| overlap | threshold | keyframes | % of total | SfM viable? |
|---------|-----------|-----------|------------|-------------|
| **0.95**| **13**    | **~700**  | **~38%**   | **Yes, dense** |
| 0.90    | 25        | 365       | 19.8%      | Yes, heavy |
| **0.85**| **38**    | **96**    | **5.2%**   | **Yes, balanced** |
| 0.80    | 51        | 27        | 1.5%       | Barely |
| 0.75    | 64        | 6         | 0.3%       | No |
| 0.60    | 102       | 1         | 0.05%      | No |

- `pipeline.py`: `--overlap` argparse default is now 0.95 (the old `--step-sec` dead flag was removed in commit `b0aee7f`; do NOT reintroduce it)
- `app/worker.py`: hardcoded `_run_ingest` overlap argument (0.95) — change in lockstep
- **Change BOTH** — worker.py has its own hardcoded value, not driven by argparse.

The keyframe selector also has a **`min_keyframes=10` safeguard** (`lunascan/ingest/keyframe.py`): if overlap-based selection yields fewer than 10 keyframes (but the source has >10 frames), it falls back to uniform sampling. This prevents SfM from starving even on unusually stable footage. Pass `min_keyframes=0` to bypass for testing.

### 5. DMG must be rebuilt after source changes

The `build_app.py` PyInstaller build bundles `lunascan/` as data with `--add-data=lunascan:lunascan`. Changes to `lunascan/pipeline.py`, `lunascan/ingest/*`, etc. are NOT picked up by an existing `.app` or `.dmg`. After any pipeline/worker fix, rebuild:

```bash
.venv/bin/python build_app.py --dmg
```

The `app/worker.py` import chain (`worker.py` → `lunascan.pipeline._run_*` → sub-module CLIs) means changes to any of those files require a DMG rebuild for the GUI to reflect them.

### 6. YOLO model must be pre-bundled for DMG

The `DynamicDetector` in `lunascan/masking/detector.py` uses `ultralytics.YOLO("yolov8n-seg.pt")`. Inside a PyInstaller `--windowed` app bundle, ultralytics cannot download the model from GitHub — curl error 56 (network/Sandbox failure).

**Fix already applied:**
- Model downloaded to `lunascan/models/yolov8n-seg.pt` (6.7MB)
- `detector.py` has `_resolve_model_path()` that checks `<MEIPASS>/lunascan/models/` (bundled) first, then dev path, then falls back to ultralytics download
- `build_app.py`'s `--add-data=lunascan:lunascan` auto-includes the models directory

**If you add a new model:** drop the `.pt` file in `lunascan/models/`, add its name to `_MODEL_FILENAME` in `detector.py`, and update `_resolve_model_path()`'s alias list. The DMG rebuild picks it up automatically via `--add-data`.

See `references/model-bundling.md` for the full reproduction recipe and `scripts/verify-model-resolver.py` for an automated check.

### 7. COLMAP binary not found from DMG sandbox

The `lunascan/sfm/pipeline.py` `COLMAPPipeline` uses `shutil.which("colmap")` to find the binary. Inside a PyInstaller `--windowed` app bundle, PATH does not include `/opt/homebrew/bin` (Apple Silicon Homebrew) or `/usr/local/bin` (Intel Homebrew), so `which()` returns `None` even though COLMAP is installed.

**Fix already applied:**
- `_find_colmap()` function in `lunascan/sfm/pipeline.py` tries `which("colmap")` first, then checks hardcoded paths `/opt/homebrew/bin/colmap` and `/usr/local/bin/colmap`
- `COLMAPPipeline.available` property now calls `which()` on the resolved path AND checks file existence/executability directly (covers explicit `colmap_bin=` paths too)
- The resolved path is cached back to `self._colmap` on first check so subsequent `run_full()` uses the found binary directly

**Test expectations:**
- `COLMAPPipeline()` → `available=True` on Macs with Homebrew COLMAP
- `COLMAPPipeline(colmap_bin="/nonexistent/colmap")` → `available=False`
- `COLMAPPipeline(colmap_bin=None)` → falls back to discovery (same as default)

See `references/colmap-sandbox.md` for the full reproduction recipe and `scripts/verify-colmap-flags.py` for an automated flag-compatibility check.

### 8. COLMAP 4.1: must use native `feature_extractor` — not hand-rolled SQLite

Hand-crafted SQLite databases (as done by `lunascan/sfm/extractor.py`'s `write_colmap_db`) are **incompatible with COLMAP 4.1**. COLMAP 4.1 uses a different internal database factory/registration system; attempting to open a manually-created DB fails with:

```
database_sqlite.cc:1657] SQLite error: SQL logic error
database.cc:52] Failed to open database with registered factory
No registered database factory succeeded.
*** SIGABRT ***
```

**The fix:** Use COLMAP's native `feature_extractor` subcommand to create the DB and extract SIFT features in one step. The `COLMAPPipeline` class has `run_feature_extraction(db_path, image_dir)` which calls:

```
colmap feature_extractor --database_path <db> --image_path <img> --FeatureExtraction.num_threads -1
```

This creates a properly-formatted database that the matcher and mapper can open without crashes.

**What was replaced** (in `lunascan/sfm/cli.py`):
- Old: `FeatureExtractor(nfeatures=...).full_extract_and_write(db_path, frame_paths, mask_paths)` — manual OpenCV SIFT + hand-rolled SQLite
- New: `pipeline.run_feature_extraction(db_path, kf_dir)` — COLMAP native

**Trade-off:** Mask filtering (removing keypoints inside dynamic-object mask regions) is lost since COLMAP's feature_extractor doesn't support per-image mask paths. The `FeatureExtractor` class still exists in the codebase but is no longer called by the CLI or pipeline. If mask filtering is needed in the future, the approach would be to extract features via COLMAP, then read back and filter the keypoints/descriptors tables using the COLMAP database API.

**Requirements:**
- Parent directory of `db_path` must exist before calling `feature_extractor` (COLMAP checks this — the `run_feature_extraction` method creates it with `db.parent.mkdir(parents=True, exist_ok=True)`)
- The `FeatureExtraction.num_threads` flag (not `SiftExtraction.num_threads`) is the COLMAP 4.1 flag name

**COLMAP 4.1 flag migration table (old → new):**

| Old (3.x) | New (4.1) |
|-----------|-----------|
| `--SiftMatching.use_gpu` | `--FeatureMatching.use_gpu` |
| `--SiftMatching.gpu_index` | `--FeatureMatching.gpu_index` |
| `--SiftExtraction.num_threads` | `--FeatureExtraction.num_threads` |
| `--Mapper.ba_global_images_ratio` | `--Mapper.ba_global_frames_ratio` |

**Verification:** Run `colmap <subcommand> --help 2>&1` on the target machine before writing any command — COLMAP 4.1 output goes to stderr (needs `2>&1` for grep). See `scripts/verify-colmap-flags.py` for an automated check.

### 9. Matching strategy: exhaustive is the safe default on COLMAP 4.1

The SFM module supports three matching backends: `sequential`, `exhaustive`, and `vocab_tree`. For ~200–1600 frames, **use `exhaustive`**. Do NOT use `vocab_tree`: the bundled 112MB tree is FLANN-format and **crashes COLMAP 4.1's `vocab_tree_matcher` with SIGABRT** (observed 2026-08-07). COLMAP 4.1 dropped FLANN for FAISS, so the legacy tree is incompatible — and unlike the feature-extractor path there is no graceful fallback for the matcher. `sequential` only compares adjacent frames (O(n)) and fails to grow the model on smooth/low-parallax footage (it also yielded "no reconstruction" here). `exhaustive` builds the full match graph (O(n²)) and is the most robust for aerial footage on one machine — ~300s for 209 frames, acceptable.

If you must scale past ~2000 images, shard into spatial/exhaustive subsets rather than relying on vocab_tree.

### 9b. SfM engine reconsideration — COLMAP mapper cannot reconstruct smooth drone footage

**Verified failure (2026-08-07):** COLMAP's `mapper` returned "no reconstruction found" on this DJI 4K flight across THREE independent configs — (a) 1609 frames @4K, (b) 209 frames @1920 with DJI-derived focal + soft GPS prior, (c) 209 frames exhaustive matching. Even with priors stripped and `multiple_models=1` + `init_min_tri_angle=4`, the mapper registered 0 images. Root cause: smooth nadir/oblique drone video has too-little angular diversity and near-planar geometry for COLMAP's sparse tracker to initialize, compounded by GPS priors that fight the geometry.

**Founder feedback:** user has used several photogrammetry tools and "COLMAP is never the best" — could never get the result he wanted from COLMAP. **Decision: adopt OpenDroneMap (ODM) as the SfM + dense reconstruction engine** for drone→3D. ODM is purpose-built for drone imagery (handles GPS/EXIF, does dense MVS → mesh → geo-referenced output, can emit `.glb`/`.obj`), and consumes the same DJI video + GPS the ingest stage already produces.

**ODM integration notes (for the next session):**
- ODM ships as a **Docker image** (`opendronemap/odm`). Docker is installed at `/usr/local/bin/docker` but the **daemon was NOT running** (2026-08-07) — starting it requires Docker Desktop (GUI/license). That is a hard prerequisite before any ODM run; cannot be done headlessly.
- ODM ingests a folder of images + (optionally) a GPS/EXIF sidecar. LUNASCAN's existing keyframes (209 @4K) + `telemetry.json` map directly onto ODM's `images/` + `gcp`/`geo` inputs.
- Plan: replace/stage LUNASCAN Batch 3+4 to either (a) shell out to `docker run opendronemap/odm` with the keyframes mounted, or (b) call ODM's Python API (`odm`) if installed. Keep COLMAP path as a fallback only.
- The COLMAP speedups already applied (keyframe pruning to ~209, 1920px downscale, 4096 features, 2h timeout, DJI focal, soft GPS) still matter for any COLMAP fallback and for feeding ODM smaller inputs faster.
- Do NOT delete the COLMAP code yet — keep it behind a `--engine colmap|odm` switch until ODM is verified producing a model on this dataset.

### 9b-i. ODM MIGRATION - DONE AND VERIFIED (2026-08-07)

The plan in 9b was executed. `lunascan/odm.py` (Batch 3+4) is now the default engine; COLMAP is retained only as a fallback. Both test flights produced a usable geo-referenced `site_model.glb`:
- **703** (1843 frames → 209 keyframes) → ODM → **14.4 MB** `site_model.glb` ✓
- **701** (4502 frames → capped 150 keyframes) → ODM → **3.7 MB** `site_model.glb` ✓
- 113 tests pass (as of 2026-08-10); `dist/LUNASCAN.dmg` rebuilt with the ODM backend.

**ODM Docker gotchas SOLVED (reproduce via `references/odm-docker-gotchas.md` + `scripts/verify-odm-command.py`):**
1. **Daemon prerequisite:** ODM is a Docker image (`opendronemap/odm:latest`). The daemon must be running (Docker Desktop). If not, the run dies with a pull/connect error — cannot be started headlessly. Ask the user to start Docker Desktop.
2. **ODM CLI shape:** ODM takes a **positional dataset name** (`code`), NOT `--images`. Stage images into `<project>/code/images` and mount `<project>:/datasets`, then invoke `odm code --project-path /datasets [flags]`. The `--images` flag is rejected by this ODM version.
3. **Meshing DEM tile overflow:** ODM's meshing stage runs `renderdem --max-tiles 165`. On large sites (long flights, big GPS spread) the DEM at fine resolution overflows (e.g. 23856 tiles > 165 → "Max tiles limit exceeded — reconstruction failed"). **Fix:** pass `--orthophoto-resolution 20` (coarse). This does NOT reduce textured-mesh quality (that is set by `--mesh-octree-depth`, default 9). Textured-mesh quality is independent of orthophoto res.
4. **Skip orthophoto/DEM:** LUNASCAN wants the textured 3D model for LunaV, not an orthophoto. Pass `--end-with mvs_texturing` to stop after texturing (also skips the slow orthophoto export). `--gltf` still emits the `.glb`.
5. **Non-zero ODM exit is NOT always failure:** OpenMVS depth-map fusion can hit RAM limits and fall back to tiling, logging a warning and exiting non-zero — yet still write `odm_textured_model_geo.glb`. **Fix in `run_odm`:** after the docker call, locate the `.glb` FIRST; if it exists, accept the run as degraded-success and copy it to `site_model.glb` (warn), instead of failing on `returncode != 0`.
6. **Geo-tagging:** LUNASCAN's VideoToolbox decode drops EXIF, so GPS must be re-embedded into each keyframe JPEG before ODM. Use **piexif** (NOT raw PIL GPS IFD dicts — PIL silently corrupts the JPEG on save with malformed rationals). `load_telemetry_gps` aligns by frame index (record `i` ↔ image `i+1`).
7. **Find the glb:** ODM writes `odm_texturing/odm_textured_model_geo.glb` (geo-referenced) — prefer it over the bare `odm_textured_model.glb`. `find_glb()` checks both + rglob.

Reproduce/verify these gotchas with `references/odm-docker-gotchas.md` and the re-runnable `scripts/verify-odm-command.py` (asserts the docker command shape: positional `code`, no `--images`, `--orthophoto-resolution 20`, `--end-with mvs_texturing`, `--gltf`) and `scripts/verify-odm-run-resilience.py` (mocks docker to assert `run_odm` copies the `.glb` even when ODM exits non-zero).

**Streaming ingest OOM fix (Batch 1):** the old keyframe selector materialised ALL decoded frames (`list(decode_video(...))` → ~46 GB for 1843 4K frames) → SIGKILL (-9). Rewrote `select_keyframes_stream` to stream decode→compare→save, holding only ~2 frames (O(1) RAM; verified 0.0 MB peak over 200k frames). The CLI must NOT `list()` the decoder output. Added `--max-frames` cap (wired through ingest CLI + master pipeline) to bound downstream ODM OpenMVS fusion RAM (see below).

**OpenMVS fusion RAM ceiling (Docker default 7.75 GB):** ODM's dense fusion OOMs above ~250 keyframes at 4K. 703's 209 fit; 701's 250/329 did NOT (OpenMVS "ran out of memory", tiling fallback still failed). **Cap keyframes ≤ ~200** (`--max-frames 150` for 701) for the default Docker RAM limit. If you raise Docker Desktop → Resources → Memory, you can raise the cap.

**Per-dataset validation ritual (user-driven):** "run until we get the model, then validate on the OTHER dataset, and if OK prepare the .dmg + update memory." Concretely: after a pipeline change, run the primary dataset to a produced `site_model.glb`, then re-run on a second independent dataset (different flight/extent) with the same flags — only declare done when BOTH produce a `.glb`. Then rebuild the DMG (`build_app.py --dmg`) and write results back to the Obsidian vault `Projects/LUNASCAN.md` + `HermesProgress.md`.

### 9b-ii. ODM matching-flag LANDMINE (2026-08-10, UNRESOLVED — read before touching `odm.py` matching)

The single biggest production blocker this session. ODM's image-matching control flags are counter-intuitive; the wrong choice makes ODM run for HOURS on 1610 keyframes and never finish.

**Authoritative flag names (ODM 3.12.3, from `docker run --rm opendronemap/odm:latest --help`):**
- `--matcher-type <string>` — FLANN (default) or BOW. NOT the matcher driver.
- `--matcher-neighbors <positive integer>` — match each image to its N **GPS-EXIF-nearest** neighbors. **Default 0 = match by triangulation (full graph).** This is the trap: the help text's "Default: 0" is the full-graph explosion.
- `--matcher-order <positive integer>` — match each image to nearest N by **filename order** (good for sequential video). **BUT: "It is applied only on non-georeferenced datasets. Set to 0 to disable."** → if you geotag the keyframes before ODM (LUNASCAN does, for GPS), `--matcher-order` is **silently ignored** and ODM falls back to GPS-neighbor/triangulation matching anyway.

**What blew up in this session (chronological — do not repeat):**
1. Original code had `--matcher-neighbors 0` (full triangulation graph) → ~300K+ pairs on 1610 frames → ran 16+ min, never finished.
2. Tried `--matching-algorithm sequential` → **`error: unrecognized arguments: --matching-algorithm sequential`** → ODM exit 2 in 5.6s. **This flag does NOT exist in ODM 3.12.3.** Do not use it.
3. Tried `--matcher-order 8` (with GPS still embedded) → ignored on georeferenced data → fell back to full graph → 126K pairs, still going, killed.
4. Tried `--matcher-neighbors 8` (GPS-KNN, N=8) → ~5x smaller than exhaustive (~86K pairs after a few min) but STILL expanding via covisibility rounds; run was still in progress when the session ended. **This is the current state of `odm.py` (line 165: `"--matcher-neighbors", "8"`).**

**RESOLVED (2026-08-10, commit `e6c2bc3`) — decision made by EMPIRICAL test, per founder's "test and adjust for best time vs result" directive:**

- **Fast (default, `geo_anchored=False`):** skip GPS geotag → ODM treats images as non-georeferenced → honors `--matcher-order 8` (sequential by filename) → **~6.4K pairs**, full reconstruction in ~69 min → valid `site_model.glb` (762 KB, 1 mesh/1 node/2 materials) verified end-to-end. ✅ This is the only reliably-bounded path.
- **Geo (`geo_anchored=True`):** embed GPS + `--matcher-neighbors 8` → ODM GPS-KNN covisibility expansion to **~150-230K pairs** (27-51 min just matching). Converges but slow; use only when geo-anchoring matters.
- **CRITICAL:** `ODM_IMAGE` is pinned to **`opendronemap/odm:3.6.1`**. `:latest` is now **3.12.3** which exploded GPS-embedded matching to 300K+ (never finished). `run_odm`/`_run_sfm`/`PipelineWorker` must pass `odm_image=None` so the module pin wins — a stale `:latest` default param clobbers it (this bit once: run showed `:latest` despite the pin because the function default overrode it).
- Flags `--matcher-neighbors 0` (no GPS, full triangulation) is SLOWEST (~227K pairs @51min). Never default to it.
- `--matching-algorithm sequential` does NOT exist in ODM 3.6.1/3.12.3 → exit 2. Never use.

Measured pair-count table + commands: **`references/odm-matching-empirical.md`** (6 configs, all on real 703 footage). Verified: valid `site_model.glb` produced; 113/113 tests pass; DMG rebuilt with QMenu GUI + 3.6.1 pin + geo-anchored toggle (default OFF).

**Verification gotcha:** when adding/changing these flags, do NOT assert with naive substring `in` checks — the explanatory comments in `odm.py` mention `--matching-algorithm` and `--matcher-neighbors` by name, so `"--matching-algorithm" in src` passes even after removal. Check **real flag tuples** with `re.findall(r'"(-{2}[\w-]+)"', src)` and assert membership there. See `scripts/verify-odm-command.py` (asserts `--matcher-neighbors 8` present and matches the live `build_docker_command` output; add a guard that `--matching-algorithm` is absent).

**macOS note:** there is no GNU `timeout` binary here — do not wrap long runs with `timeout 300 python ...` (errors rc=127). Use the agent's background `process` tool with `notify_on_complete=True` and `process(action='wait'|'kill')` instead.

See `references/odm-matching-flags.md` for the authoritative ODM 3.12.3 flag table + failure sequence + diagnostic commands.

### 9c. Verified DJI + COLMAP intrinsics learnings (2026-08-07)

Concrete, tested facts — use these instead of guessing:

- **DJI lens from SRT:** the DJI SRT embeds `focal_len: 240` (0.1mm units = 24mm 35mm-equivalent) and `fnum: 280` (f/2.8). Convert to COLMAP px focal: `px = (focal_35mm_equiv / 36.0) * image_width`. For 4K (3840w) → 2560px; for the 1920 SFM-downscaled width → 1280px. The old hardcoded `focal = 1.2 * max(w,h)` gave a bogus 4608px (seen in the dead-run log) — never use that.
- **Resolution-scaling:** the px focal MUST be computed for the resolution COLMAP actually processes (the 1920-wide downscaled copy), not the 4K original. Mismatch → wrong projection → failed triangulation.
- **GPS as SOFT prior:** write `prior_tx/ty/tz` AND `prior_position_std` (e.g. 10m) into COLMAP's images table. A hard prior (std=0, or omitting the column) locks the solution and frequently causes 0-images-registered on aerial video. This mirrors how Pix4D/Metashape/ODM use RTK/GPS. Also: COLMAP's `feature_extractor` may create the images table WITHOUT `prior_*` columns — ALTER TABLE ADD COLUMN if missing before UPDATE (see `georef.write_priors`).
- **COLMAP camera params are 8-byte DOUBLES**, not floats. When patching the `cameras.params` BLOB, `struct.pack/unpack("<%dd", ...)`. Using `<f` (float) silently corrupts the camera and breaks mapping. This was a real bug caught by verification.
- **Keep 4K originals for export, downscale only for SFM:** `run_feature_extraction(max_dim=1920)` writes a `keyframes_sfm/` dir of 1920px copies (filenames preserved → GPS stays aligned by index) and points COLMAP at it. Export/mesh should still use the 4K originals for detail.
- **GPS aligns by `image_id = i+1` ↔ telemetry record `i`** — so the ONLY safe way to reduce frame count is to re-run Batch 1 ingest with a higher `--overlap` (re-deriving from existing 4K frames misaligns GPS). overlap=0.88 → 209 frames (89% pruned) on this stable flight; overlap=0.60 → only 11 frames (too few). The knee is steep — tune per footage, verify the count.

### 10. Video trimmer: frame range architecture

The GUI has a **Video Trimmer** section (between Output Directory and Pipeline Progress) that shows a horizontal scrollable strip of thumbnails extracted from the loaded video. Users click thumbnails to set start (green border) and end (red border) markers; these become `--start-frame`/`--end-frame` args passed through the entire pipeline chain.

**Key files and the pass-through chain:**

```
MainWindow._trim_start/_trim_end
  → PipelineWorker(start_frame=..., end_frame=...)
    → _run_ingest(..., start_frame=..., end_frame=...)
      → ingest CLI → decode_video(start_frame=..., end_frame=...)
```

**Thumbnail extraction** uses `lunascan/ingest/decoder.extract_thumbnails()` — decodes every N seconds, resizes to 160px wide JPEG. Real-world: 32 thumbnails from a 61s 4K video, ~3-4KB each. See `references/video-trimmer-architecture.md` for the full UI design, click handlers, state management, and wiring guide.

**ffmpeg fallback:** Inside the PyInstaller DMG sandbox, `ffmpeg` is typically unavailable. The `trim_video()` function in `lunascan/ingest/decoder.py` checks `shutil.which("ffmpeg")` — if absent, it returns the original input path (no file copy). The worker detects this (`result == self._video`) and instead passes `start_frame`/`end_frame` to `_run_ingest` for frame-range decode, which skips frames at decode time without creating a trimmed file. See `lunascan/ingest/decoder.py:trim_video()` and `app/worker.py` lines ~91-104 for the two-path logic.

### 11. macOS malloc stack logging — disable it

If `MallocStackLogging=1` or `MallocStackLoggingNoCompact=1` is set in the environment (common after Xcode/Instruments debugging sessions), every COLMAP subprocess runs 10-100x slower because macOS logs every malloc/free with a stack trace. The fix is in `app/run.py`: `os.environ.pop("MallocStackLogging", None)` before any imports. See `references/macos-malloc-logging.md` for diagnosis commands, global cleanup via `launchctl unsetenv`, and verification steps.

### 12. Nadir drone footage: COLMAP mapper parameters

Downward-facing (nadir) drone footage has near-parallel camera axes — standard COLMAP mapper defaults fail because triangulation angles are too acute. The initialisation minimum triangulation angle (`init_min_tri_angle`) defaults to 16° in COLMAP 4.1, which rejects almost all nadir pairs. The fix is a set of relaxed mapper and feature-extraction flags applied in `lunascan/sfm/pipeline.py`:

**Feature extraction** — more keypoints per frame (configurable via `--nfeatures`, default **4096**):

```
--SiftExtraction.max_num_features <nfeatures>   # wired through CLI → COLMAPPipeline.nfeatures
```

**DO NOT re-add `--SiftExtraction.first_octave -1`.** That flag upsamples every 4K frame 2× (to 7680×4320) *before* SIFT — ~4× the pixels = ~4× the runtime for negligible quality gain on drone imagery. It was removed in the 2026-08-06 optimization. For genuinely nadir/low-parallax footage you may raise `--nfeatures` (e.g. 8000–16000) but keep `first_octave` at its default 0.

**Mapper** — relaxed geometry constraints:

```
--Mapper.init_min_tri_angle 1       # default 16 — allow acute triangulation
--Mapper.multiple_models 0          # default 1  — force single model
--Mapper.min_num_matches 5          # default 15 — accept pairs with few inliers
--Mapper.ba_global_function_tolerance 0  # disable early stopping
```

These flags are set in `COLMAPPipeline._run_mapper()` and `run_feature_extraction()`. If you change them, verify they exist in the target COLMAP version: `colmap mapper --help 2>&1 | grep init_min_tri_angle` (COLMAP 4.1 help output goes to stderr).

**Pitfall:** `init_min_tri_angle=1` increases false-positive triangulations (noise points). At overlap=0.95 a 60s 4K DJI pan retains **~1,610 keyframes (≈87% of 1,843)** — the exact count varies with footage stability (more motion → more pruning). The retained-frame count, NOT fps, dominates COLMAP runtime (see Pitfall 18); if SfM is the bottleneck, prune keyframes (lower overlap) or cap the input frame range. Expect more outlier 3D points in the sparse cloud — the Poisson surface reconstruction stage (Batch 4) filters these naturally. If the output mesh is noisy, experiment with `init_min_tri_angle` between 1–8 depending on how steep the drone angle is.

**Still no reconstruction?** The footage may genuinely lack angular diversity (single-pass straight-down — every camera looks parallel). No parameter can fix zero parallax. The fix is to fly a grid pattern or lower the camera angle (e.g., 30° off-nadir) so frames see the same ground from different angles. See `references/nadir-drone-sfm.md` for the full troubleshooting guide with symptom checklist and verification commands.

When adding or modifying a `_run_*` function in `pipeline.py`: open the target CLI's argparse definition and verify every arg name, type, and value format matches exactly. NOTE: pre-ODM this skill said "fixing `pipeline.py` fixes both" (GUI worker) — that is now FALSE. The GUI `app/worker.py` is a SEPARATE copy of the call sequence and must be updated in lockstep; it is NOT a thin passthrough to `pipeline.main()`.

**Concrete current `worker.py` Batches 3–5 call sequence (2026-08-07, post-ODM + Batch 5):**
```python
from lunascan.pipeline import _run_ingest, _run_masking, _run_sfm, _run_export, _print_summary
from lunascan.docker_util import ensure_docker_running
from lunascan.optimize import optimize_glb

# Batch 3+4 ODM (Docker) — note the ODM signature, NOT the old COLMAP one:
rc = _run_sfm(
    keyframes_dir,
    masks_dir if not self._skip_masking else None,
    self._telemetry,
    output_dir,
    fast=True,                       # worker has no fast toggle; ODM fast preset
    odm_image="opendronemap/odm:latest",
    odm_timeout=7200,
    skip=False,
)
# Before ODM migration the worker still called _run_sfm with the 8-arg COLMAP
# signature — that is the "GUI Run button crashes" bug. If Batch 3 fails on the
# GUI, check the signature matches the current _run_sfm.
ensure_docker_running()   # call before _run_sfm so Docker auto-starts

# Batch 5 optimize (graceful): keep raw glb on failure
optimized = output_dir / "site_model.optimized.glb"
if optimize_glb(final_glb, optimized, skip_textures=False):
    optimized.replace(final_glb)
```
**GUI default output dir fix (2026-08-07):** `app/main_window.py` previously hardcoded `output = self._output_dir or Path("/tmp/lunascan")`. Changed to `~/LUNASCAN_Output/<video_stem>` (auto-created, persistent). Do NOT reintroduce `/tmp` — it is ephemeral and the user loses output on reboot.

### 13. Stale keyframe directory — clean before every ingest run

The keyframes directory is NOT cleaned between pipeline runs. If you run the pipeline twice on the same output dir, the second run's Batch 2 (masking) sees ALL keyframes from BOTH runs, causing wrong frame counts, extra work, and memory waste.

**Fix applied (2026-08-06):** `_run_ingest` in `lunascan/pipeline.py` now calls `shutil.rmtree(keyframes_dir)` before running the ingest CLI. The ingest CLI's `mkdir(parents=True, exist_ok=True)` recreates the clean directory. The GUI worker imports `_run_ingest` from pipeline.py, so it inherits this fix — no redundant cleanup in worker.py.

**Test coverage:** `test_pipeline.py` mocks `_run_ingest` so cleanup never runs during tests (the mock skips the function body). Ad-hoc verification confirms: cleanup inside `_run_ingest`, worker deduplicated, stale frames deleted, `skip=True` preserves existing frames.

### 14. Masking batch processing — use `--batch-size` to limit memory

Batch 2 loads ALL keyframes into memory before inference. With 700+ 4K keyframes (3840×2160×3 bytes each), that's ~17 GB — crashes with `Invalid buffer size: 10.44 GiB`.

**Fix applied (2026-08-06):** `lunascan/masking/cli.py` processes frames in configurable batches via `--batch-size N` (default 16). Each batch: load N frames → detect → generate masks → `del` frames. YOLO model stays loaded once (reused across batches). Pipeline passes through `--batch-size` flag.

| batch-size | ~memory/batch (4K) |
|------------|-------------------|
| 4          | 100 MB            |
| 8          | 200 MB            |
| 16 (default) | 400 MB          |
| 32         | 800 MB            |

**Usage:** `lunascan-mask --keyframes ./frames/ --batch-size 8` or `lunascan-pipeline --video drone.mp4 --batch-size 8`. Pixel-identical output verified across different batch sizes. DMG must be rebuilt after source changes (see pitfall 5).

### 14b. THE 4K MEMORY FIX — `--max-dim` keyframe downscale (2026-08-10, commit `ab1562a`)

The real root cause of the 4K memory blow-up was ingest writing keyframes at FULL 4K resolution (3840×2160, no resize) — those flood Batch 2 (masking: 16×4K×3B ≈ 3.5GB/batch → 17GB crash) and Batch 3 (ODM OpenMVS fusion OOMs above ~250 4K frames at the 7.75GB Docker default limit). Batch-size alone wasn't enough.

**Fix:** `lunascan/ingest/cli.py` `_save()` now downscales each kept keyframe via `cv2.resize(..., interpolation=cv2.INTER_AREA)` when `--max-dim` (default **1920**) is exceeded — 4× fewer pixels than 4K → ~4× less RAM in every downstream stage. `--max-dim 0` keeps original resolution.

- Threaded through: `pipeline.py` `_run_ingest` (new `max_dim` kwarg + `--max-dim` argparse) AND `app/worker.py` (new `max_dim` constructor kwarg, default 1920, passed to `_run_ingest`). **Both** must stay in lockstep like the overlap default.
- GPS/telemetry alignment is UNAFFECTED — keyframe filenames (`frame_000NNN.jpg`) preserve the frame index, so ODM geotag still maps image `i` ↔ record `i-1`.
- ODM itself also has `--resize-to` if per-image downscale inside the container is preferred; the ingest-level cap is the LUNASCAN default because it also protects Batch 2.
- Tests: `tests/test_ingest.py` `TestMaxDimDownscale` (2 tests: 4K→1080×1920 at max-dim 1920; 4K preserved at max-dim 0) — monkeypatches `probe_video`/`decode_video`.
- Verification pattern: `find dist/LUNASCAN.app -name "*.bin"` must show NO `vocab_tree*` (the 112MB file was removed from `lunascan/models/` — it's unused and crashes COLMAP 4.1). DMG went 477MB → 358MB.

### 14c. GUI Resolution control + lean DMG + headless GUI verification (2026-08-10, commits `ab1562a` + `77651ea`)

**(b) Resolution dropdown** — `app/main_window.py` Input Files group uses a **QPushButton + QMenu** (NOT QComboBox — see crash fix below): `_resolution_btn` + `_resolution_menu` with 3 checkable actions **720p→1280, 1080p→1920 (default), 4K→0**; `_set_resolution(max_dim,label)` updates state; `_start_pipeline` passes `max_dim=self._resolution_max_dim`; `_reset_all()` restores 1080p.

**⚠️ CRASH FIX (commit `479a50f`): QComboBox → QPushButton+QMenu.** In the PyInstaller DMG bundle, clicking a stylesheet-styled QComboBox popup segfaulted (`QComboBox::showPopup` → `QWindow::geometry()` → `EXC_BAD_ACCESS at 0x8`, SIGSEGV). Qt 6.10.3 + PyInstaller + forced custom popup = crash path; dev venv was fine. **Do NOT reintroduce QComboBox.** Verify after any GUI change: `grep -c QComboBox dist/.../app/main_window.py` → 2 (comment only), zero code refs.

**(c) Geo-anchored toggle** — `app/main_window.py` has a `QCheckBox` "Geo-anchored (slower)" (`_geo_chk`, default OFF). `_geo_anchored` flows: `_start_pipeline` → `PipelineWorker(geo_anchored=...)` → `_run_sfm(geo_anchored=...)` → `run_odm(geo_anchored=...)` → controls geotag + matcher flag. CLI: `--geo-anchored`. Default OFF = FAST.

**⚠️ MATCHING TUNING (commit `e6c2bc3` + `07615b2`) — critical for production speed.** ODM matching on the 703 flight (1610 keyframes @720p) behaves like this (EMPIRICALLY VERIFIED):
- `ODM_IMAGE` is pinned to **`opendronemap/odm:3.6.1`**. `:latest` is now **3.12.3** which exploded GPS-embedded matching to **300K+ pairs (never finished)**. Do NOT let `run_odm(odm_image=...)` default override the pin — `_run_sfm` and `PipelineWorker` must pass `odm_image=None` so the module-level `ODM_IMAGE` wins (the old `:latest` default param clobbered the pin).
- **Fast (default, `geo_anchored=False`):** skip GPS geotag → ODM treats images as non-georeferenced and honors **`--matcher-order 8`** (sequential by filename) → **~6.4K pairs**, full reconstruction in ~69 min. ✅
- **Geo (`geo_anchored=True`):** embed GPS + **`--matcher-neighbors 8`** → ODM does GPS-neighbor covisibility expansion → **~150-230K pairs**, slow (30-45 min just matching). Converges but slow.
- **`--matcher-order` is IGNORED on georeferenced datasets** ("applied only on non-georeferenced datasets") → silently falls back to full graph. So GPS + matcher-order is useless; use matcher-neighbors for geo mode.
- **`--matcher-neighbors 0`** (no GPS, full triangulation) is the SLOWEST (~227K pairs in 51 min, still running). Never default to it.
- **Do NOT use `--matcher-neighbors 8` in fast mode** — it doesn't bound GPS expansion on 3.6.1 either.
- Net: default (no GPS, matcher-order 8) is the only reliably-bounded path. Live result: valid `site_model.glb` (762KB, 1 mesh/1 node/2 materials) produced end-to-end.

**(b) Lean DMG — strip dead model weight BEFORE build.** `build_app.py` bundles `lunascan/` wholesale (`--add-data=lunascan:lunascan`), so EVERYTHING in `lunascan/models/` rides into the DMG. The 112MB `vocab_tree_flickr100K_words256K.bin` was deleted from SOURCE before building → DMG 477MB → 358MB. Rule: anything in `lunascan/models/` ships; delete dead weight there BEFORE `build_app.py --dmg`, don't just gitignore it. Post-build verify: `find dist/LUNASCAN.app -name "*.bin"` — npm `node_modules/.bin` DIRS are normal; check for the model filename specifically.

**(c) Headless GUI verification — write results to a FILE, don't pipe.** `QT_QPA_PLATFORM=offscreen` lets you instantiate `MainWindow` without a display. Two traps hit 2026-08-10:
1. If the script calls `_start_pipeline()` (even with `PipelineWorker.__init__` spied), the spawned worker QThread is never joined → **Abort trap: 6 / exit 134 AFTER all assertions pass**. Harness artifact, not an app defect.
2. Piping the script through `grep` swallowed the PASS line entirely (objc/QThread noise floods stdout). **Pattern: write `ADHOC_RESULT: PASS/FAIL` to an env-specified file from the script, `cat` the file in a separate step, then clean up both.** Assertions that work: combo item text/data exact, default index, selection → worker `max_dim` via `__init__` spy, `_reset_all()` restores 1080p.

### 15. COLMAP steps run silently — add progress logging between stages

COLMAP subprocess calls (feature_extractor, sequential_matcher, mapper) capture stdout/stderr and only show output on error. During normal operation, minutes pass with ZERO log output. The user sees the Batch 3 progress bar stuck at 0% and kills the app, thinking it stalled — when COLMAP is actually running fine.

**Fix applied (2026-08-06):** Progress messages added at every stage boundary:

- **SFM CLI (`lunascan/sfm/cli.py`):** logs `COLMAP pipeline starting on N keyframes (est. X-Y min)`, `[1/3] feature extraction …`, `[1/3] feature extraction complete in Xs`, `[2/3] feature matching …`
- **COLMAP pipeline (`lunascan/sfm/pipeline.py`):** `run_full()` logs `matching (sequential) …`, `matching done in Xs`, `sparse mapper …`, `mapper done in Xs` before each subprocess call and after completion.

This gives users a heartbeat: they see which step is running and how long each took, even though COLMAP's internal progress (stderr percentages) stays hidden. The estimated duration at the start sets expectations — 1,596 4K frames ≈ 9-17 minutes for SIFT extraction alone.

### 16. DJI SRT telemetry — must convert to JSON before SFM

DJI drones produce telemetry as SRT subtitle files with GPS data embedded in HTML `<font>` tags using bracket notation: `[latitude: 2.957820] [longitude: 101.756079] [altitude: 29.100000]`. The ingest module's `parse_telemetry` handles CSV-format SRT but NOT this DJI bracket-key-value format. The SFM module's `load_telemetry` only handles JSON.

**The gap:** passing a raw DJI `.SRT` file as `--telemetry` to the pipeline silently fails — SFM gets 0 telemetry records, no GPS priors are written to COLMAP, and the sparse cloud lacks georeferencing.

**Fix:** convert DJI SRT to JSON before running the pipeline:

```python
import re, json

pattern = re.compile(r'\[latitude:\s*([\d.]+)\]\s*\[longitude:\s*([\d.]+)\]\s*\[altitude:\s*([\d.]+)\]')
records = []
with open("DJI_0703.SRT") as f:
    for match in pattern.finditer(f.read()):
        lat, lon, alt = float(match.group(1)), float(match.group(2)), float(match.group(3))
        records.append({"ts": len(records) * (1/30), "lat": lat, "lon": lon, "alt": alt})

with open("telemetry.json", "w") as f:
    json.dump(records, f)
```

Then run: `lunascan-pipeline --video ... --telemetry telemetry.json ...`

See `references/dji-srt-conversion.md` for the full script with error handling and CSV fallback. A ready-to-run converter is at `scripts/dji-srt-to-json.py` (handles the bracket-key-value format, writes JSON + CSV).

### 17. DMG rebuild checklist — all 3 fixes from this session

Three fixes were applied to the source in one session. All required a DMG rebuild:

1. **Batch processing** (`--batch-size`) — `lunascan/masking/cli.py` + `lunascan/pipeline.py`
2. **Stale keyframe cleanup** — `lunascan/pipeline.py` `_run_ingest`
3. **SFM progress logging** — `lunascan/sfm/cli.py` + `lunascan/sfm/pipeline.py`

After any source change to `lunascan/`:

```bash
cd ~/Documents/LUNASCAN && .venv/bin/python build_app.py --dmg
```

Verify the bundled copy has the fix:
```bash
grep -c "batch.size" dist/LUNASCAN.app/Contents/Frameworks/lunascan/masking/cli.py
grep -c "this will take a while" dist/LUNASCAN.app/Contents/Frameworks/lunascan/sfm/cli.py
```

- Run: `.venv/bin/python -m pytest tests/ -q --tb=short` from repo root
- **113 tests total as of 2026-08-10** (after `ab1562a` +2 `TestMaxDimDownscale`, `aaa3998` +7 `test_docker_util`, `bb11e09` +5 `test_odm_telemetry`). Earlier refs to "99 tests" / "101 tests" / "99/99" are stale.
- **Nested argparse trap**: mocking `ArgumentParser.parse_args` at `pipeline.main()` level does NOT propagate to internally-created parsers in sub-modules (e.g. `_run_ingest` → `ingest.cli.main` creates its own `ArgumentParser`). Don't mock argparse for integration tests — use real CLI invocation via subprocess instead.
- Storage tests use `unittest.mock` to mock `boto3.client` — no `moto` dependency needed.
### 18. COLMAP `_run()` timeout — must exceed real 4K dataset runtime

`COLMAPPipeline._run()` had a default `timeout=600` (10 min). On a real DJI 4K dataset (1,610 retained keyframes) SIFT extraction alone runs 50–65 min, so the subprocess hit `TimeoutExpired` and the **whole pipeline aborted with exit code 1** — looking like a crash, not a timeout. Raised to `timeout=7200` (2 h) on 2026-08-06. If you add heavier stages, raise it further or pass `timeout=None` for no limit.

**Why COLMAP SfM is slow — three multiplicative cost drivers** (this is what a "stall" actually is):
1. **`--SiftExtraction.first_octave -1`** upsamples each frame 2× before SIFT → ~4× pixels → ~4× work. Usually pointless for drone shots. **Remove it** (see Pitfall 12).
2. **`--SiftExtraction.max_num_features`** — 16000 is 4–8× more than the ~2000–4000 a DJI frame needs; each feature is also stored in `colmap.db` (DB balloons to 4–5 GB). Lower to 4096 (now the wired default).
3. **Frame count** — overlap=0.95 retains ~87% of frames (1,610 of 1,843 on a stable 60s 4K pan). More frames = linearly more SIFT. Prune keyframes (lower overlap) or cap the input range to cut this.

Combined A+B+D (drop upsample + 4096 features + wire `--nfeatures`) cut a 1,610-frame run from 50+ min toward a few minutes. **FPS is NOT the driver** — it is total retained keyframe count × per-frame SIFT cost, amplified by (1) and (2). When a user asks "why is it slow / is it FPS?", answer: frame *count* and per-frame feature settings, not the video frame rate.

### 19. SFM `--nfeatures` CLI flag was NOT wired to the pipeline

The `lunascan-sfm` CLI accepted `--nfeatures 8000` but `COLMAPPipeline.run_feature_extraction()` **ignored it** and hardcoded `max_num_features 16000`. So the flag did nothing — every run used 16000 regardless. Fixed 2026-08-06: the CLI passes `nfeatures=args.nfeatures` into the `COLMAPPipeline(...)` constructor, which stores `self._nfeatures` and uses it in `run_feature_extraction` (with an optional per-call override).

**Verification pattern (reusable):** after adding any such flag, grep BOTH the CLI argparse default AND the constructor call site; a flag with no path to the subprocess command string is dead. Ad-hoc check: monkeypatch `_run` to capture the cmd and assert `--SiftExtraction.max_num_features` equals the expected value and `--SiftExtraction.first_octave` is absent. See `scripts/verify-sfm-optimize.py` for the full check (8 assertions).

- Export tests use synthetic PLY data only — no real COLMAP output needed.

### 21. Web-ready .glb optimization (Batch 5) + Docker auto-start + DMG packaging corrections

Three changes landed 2026-08-07 that the next session must know:

**(a) ODM output is Draco-compressed — Batch 5 decodes Draco → meshopt + quantize + webp.**

ODM's `--gltf` emits a **Draco-compressed** `.glb`. To make it web-ready for LunaV's Three.js viewer you must (1) DECODE Draco, then (2) re-encode as meshopt + quantize + compress textures to webp. Implemented in `tools/3d-optimize/optimize.mjs` (Node, `@gltf-transform/*` + `meshoptimizer` + `draco3d` + `sharp`), driven from Python via `lunascan/optimize.py` (`optimize_glb()` shells out to `node optimize.mjs <in> <out>`).

**gltf-transform gotchas (all hit and fixed):**
- **Do NOT use `ALL_EXTENSIONS`.** It pulls in `KHRDracoMeshCompression`, which eagerly `install()`s the Draco decoder at IO-init time and **crashes if `draco3d` isn't installed**. Register only the extensions you use (`KHRMeshQuantization`, `KHRTextureBasisu`, `KHRMaterialsUnlit`, `KHRMaterialsEmissiveStrength`, `KHRDracoMeshCompression`) AND `registerDependencies({ 'draco3d.decoder': await draco3d.createDecoderModule(), 'draco3d.encoder': await draco3d.createEncoderModule() })`.
- **After re-encoding as meshopt, the stale `KHR_draco_mesh_compression` declaration lingers** (gltf-transform keeps the extension in the doc). Strict loaders (and LunaV's MeshoptDecoder path) choke on the dangling claim. Fix: iterate `doc.getRoot().listExtensionsUsed()`, find `KHR_draco_mesh_compression`, and call `ext.dispose()` before `writeBinary`. (`doc.getRoot().removeExtension(...)` is NOT a method — wrong API.)
- **Verification result:** 701 raw ODM glb 3.74 MB → **0.97 MB (74% smaller)**, readback valid with only `KHR_mesh_quantization`. The optimizer CLI exits non-zero on failure so `optimize_glb` can fall back to the raw glb.

**(b) Docker daemon auto-start (`lunascan/docker_util.py`).**

ODM runs in Docker. New `ensure_docker_running()` (called at the top of `run_odm`): if `docker info` fails, on macOS it runs `open -a Docker` and polls `docker info` up to `DOCKER_START_TIMEOUT` (default 120s); on Linux tries `systemctl start docker`; returns False if Docker is truly unavailable. This makes the `.dmg` self-contained — the user no longer has to pre-start Docker Desktop. NOTE: Batch 1 (VideoToolbox) + Batch 2 (CoreML) are Apple-Silicon-native and CANNOT run in Docker on Mac — only ODM is containerized. That is the correct architecture; do not try to "dockerize" ingest/masking.

**(c) DMG packaging MUST bundle `app` AND `tools/3d-optimize` (was missing).**

`build_app.py` historically only did `--add-data=lunascan:lunascan`. Two consequences:
- The GUI `app/` package was **never bundled** → the `.dmg`'s "Run" button crashed (worker.py/main_window.py absent). FIX: add `--add-data=app:app`.
- The Node optimizer `tools/3d-optimize` (with `node_modules`) must be bundled so Batch 5 works in the shipped app → add `--add-data=tools/3d-optimize:tools/3d-optimize`.
- The `optimize.py` resolver computes repo root as `Path(__file__).resolve().parent.parent` (lunascan/ → repo root), so in the bundle the script lands at `<Resources>/tools/3d-optimize/optimize.mjs` and finds `node_modules` next to it. The runtime needs `node` on PATH (the target Mac must have Node installed).

After any change to `lunascan/`, `app/`, or `tools/3d-optimize`, **rebuild the DMG** (`build_app.py --dmg`) — and VERIFY the bundle actually contains the changed file (grep the bundled copy under `dist/LUNASCAN.app/Contents/Resources/`), because a missing `--add-data` ships a silently-broken app.

See `references/glb-web-optimization.md` for the full optimizer recipe + Docker auto-start detail, and `scripts/verify-glb-optimizer.py` to assert the Node optimizer is wired (node present, optimize.mjs + draco3d installed, optimize_glb importable).

### 21b. Docker CLI sandbox resolution + Publish-to-LunaV GUI removed (2026-08-10, commit `aaa3998`)

**(a) "docker CLI not found on PATH — install Docker Desktop" from the DMG is a SANDBOX PATH issue, not a missing install.** PyInstaller `--windowed` bundles run with a minimal PATH, so `shutil.which("docker")` returns None even when Docker Desktop is installed (exact same class of bug as Pitfall 7 for COLMAP). Observed live: full pipeline ran great through Batch 2 (1596 keyframes masked in 51s at ~32ms/frame, bundled YOLO model loaded from `<MEIPASS>/lunascan/models/`), then Batch 3 died with this error.

**Fix:** `lunascan/docker_util.py` now has `find_docker()` — tries `shutil.which("docker")` first (dev machines), then hardcoded candidates `/usr/local/bin/docker`, `/opt/homebrew/bin/docker`, `/Applications/Docker.app/Contents/Resources/bin/docker`, cached in `_found_docker`. `docker_available()` / `daemon_running()` use it (daemon_running invokes the RESOLVED path, not bare "docker"). `lunascan/odm.py` uses `find_docker() or "docker"` at ALL 3 invocation sites: `build_docker_command` (`docker run`), the pull step, and `_image_present` (`docker image inspect`). Any NEW docker call site in odm.py must do the same.

**Test:** `tests/test_docker_util.py` (7 tests, added 2026-08-10): find via PATH, find via hardcoded candidates when PATH misses, None when everything misses, caching, daemon_running uses resolved bin. Sandbox-sim check from shell: `env PATH=/usr/bin:/bin .venv/bin/python -c "from lunascan.docker_util import find_docker; print(find_docker())"` → `/usr/local/bin/docker` on this machine.

**(b) FOUNDER DIRECTIVE — the entire "Publish to LunaV" GUI section was REMOVED.** Deleted from `app/main_window.py`: the `pub_group` QGroupBox UI block (`_publish_check` QCheckBox + `_project_id` QLineEdit), `_maybe_publish()` method, the `self._maybe_publish(output_dir)` call in `_on_complete`, the `QCheckBox` import, the `QCheckBox` stylesheet rules, and the docstring mention. Do NOT re-add a publish button/checkbox unless the founder reverses this. The `app/publish.py` module file still exists but is orphaned (not imported by the GUI anymore) — leave it. Verify removal: `grep -ci "publish" dist/LUNASCAN.app/Contents/Frameworks/app/main_window.py` → 0.

### 21c. Telemetry parse failure must degrade, not crash (2026-08-10, commit `bb11e09`)

**Symptom:** pipeline ran Batch 1+2 fine, then Batch 3 died immediately after "docker CLI resolved" with `ERROR: Extra data: line 2 column 1 (char 2)` — a bare `json.JSONDecodeError` from `load_telemetry_gps()` surfacing as the GUI error string.

**Root cause:** the GUI-loaded telemetry file was malformed (starts with `[]` = 2 chars, then MORE content on line 2 — the classic "empty array + appended records" converter bug). `json.loads` raised, nothing caught it, the whole ODM run aborted. GPS/telemetry is a georeferencing BONUS, not a hard dependency — a bad file must never kill the reconstruction.

**Fix:** `lunascan/odm.py` `load_telemetry_gps()` now returns `[]` (with a `WARNING` that names the offending file) for: missing file, non-JSON content, malformed JSON (`JSONDecodeError`), or non-list JSON. `geotag_keyframes` then tags 0 frames and ODM continues WITHOUT GPS (already the documented graceful path for missing telemetry). Tests: `tests/test_odm_telemetry.py` (5 tests: valid, extra-data, missing, not-a-list, invalid syntax).

**Field-workaround when the user hits this with an old DMG:** the malformed file is whatever the GUI browse dialog last selected — NOT the known-good `~/Desktop/DJI/703/telemetry.json` (verified 1842 records, parses fine) or `701/telemetry.json` (4501 records). Either re-select a valid telemetry file in the GUI, or leave telemetry empty (ODM reconstructs without GPS).

### 23. ODM output cleanup — the log path lies; preserve the REAL nested .glb first

**NEW (2026-08-10).** Two traps when clearing `~/LUNASCAN_Output` test runs:

- **The pipeline log prints a top-level `site_model.glb` that is NOT reliably persisted.** On the `703_720p_fast` validated run the log said `Output (local): .../703_720p_fast/site_model.glb (0.7 MB)` AND `Output optimized -> .../703_720p_fast/site_model.glb (0.7 MB)` — but `mv 703_720p_fast/site_model.glb` FAILED: the file was absent at the top level. `find` confirmed the ONLY `.glb` in the tree was the ODM textured output nested at `<output>/odm/code/odm_texturing/odm_textured_model_geo.glb` (1.8 MB). The optimize step's in-place `replace()` likely no-op'd or logged optimistically. **`find_glb()` is supposed to rglob both + copy to top-level (Pitfall 9b-i #7), but do NOT trust the log line — verify the top-level file EXISTS before backing up / deleting the tree.** The canonical, always-present deliverable is the ODM textured glb at `odm/code/odm_texturing/odm_textured_model_geo.glb` (geo-referenced; prefer over its bare `odm_textured_model.glb` sibling).

- **Each ODM docker run leaves ~7–9 GB of scratch.** A single 703 run produced: `keyframes/` (1600 @1280px), `masks/`, and `odm/` containing `odm_meshing/*.ply`, `odm_filterpoints/point_cloud.ply` (151 MB), `opensfm/.../scene_dense.ply` (282 MB), `opensfm/.../depthmaps/*.dmap` (hundreds of files), and `odm_texturing_25d/` OBJ+textures. Only the ~1–2 MB `.glb` is the deliverable.

**Cleanup ritual (reclaimed ~9.5 GB on 2026-08-10):**
```bash
# 1. copy the real model out BEFORE deleting anything
cp "<output>/odm/code/odm_texturing/odm_textured_model_geo.glb" \
   ~/LUNASCAN_Output/"<name>.glb"
# 2. nuke the scratch tree + logs
rm -rf "<output>" "<output>_run.log"
```
Do NOT `rm -rf ~/LUNASCAN_Output` wholesale without first copying out the nested glb — the real model is buried, not at the top. Also remove sibling dead runs (`703_720p_prod`, `dji_fly_*_video`, `fake/`) in the same pass. The `~/Documents/LUNASCAN` repo and `dist/LUNASCAN.dmg` are NOT scratch — leave them.

### 24. LUNASCAN repo temp cleanup — distinguish regenerable from product before `rm`

The repo is ~4.6 GB. When reclaiming disk, only these are safe to delete without a rebuild:

- **`build/`** — PyInstaller scratch. `build_app.py` runs `shutil.rmtree("build")` AND `shutil.rmtree("dist")` at the START of every `--dmg` run (see `build_app.py` lines 84-88), so `build/` is always regenerated. Safe `rm -rf`.
- **`__pycache__/`, `.pytest_cache/`** — interpreter/test caches. Safe `rm -rf`.
- **`dist/LUNASCAN/`** (onedir folder, ~882 MB) — the redundant `--onedir` PyInstaller output that also gets recreated, then wrapped into `.app`/`.dmg`. It is NOT the installed app (`dist/LUNASCAN.app` is). Safe `rm -rf` if you don't reference it directly — but note `build_app.py` wipes `dist/` entirely each run anyway, so a rebuild regenerates it.

DO NOT delete (these are the product or the dev env):

- **`dist/LUNASCAN.app/` + `dist/LUNASCAN.dmg`** — the actual shipped bundle/installer (~1.2 GB). Rebuilding requires a full `build_app.py --dmg` (slow: PyInstaller + hdiutil). Keep unless you intend to rebuild.
- **`.venv/`** (2.3 GB) — the dev environment. Regenerable via `pip install -e '.[gui]'` but that's a multi-minute reinstall. Leave unless disk is critical; ASK before nuking.
- **`lunascan/models/yolov8n-seg.pt`** — committed, bundled into DMG (Pitfall 6).
- **`rover_output/`, `rover_body.*`** — NOT LUNASCAN; a separate FreeCAD rover project (Pitfall 22). Leave.

**Cross-project cache sweep that is always safe:** `rm -rf <proj>/__pycache__ <proj>/.pytest_cache` for LUNASCAN / R-Tessera / leadfinder-my / my-digital-twin. `node_modules` is gitignored; don't hand-delete (rebuilds from `package-lock.json`). `dist/` in non-LUNASCAN projects is usually the build output — verify before wiping.

## Batch 3+4 on a remote GPU host (ODM is the portable stage)

The heavy stage is ODM, and ODM is already a container — which makes it the easiest stage
to relocate. The other batches are *tuned* for Apple but not locked to it, and the
difference matters: Batch 2's detector is ultralytics/torch and runs on CUDA as-is; only
its **default device selection** is the problem (`_detect_device()` in
`lunascan/masking/detector.py` prioritises `mps > cpu` and never returns `cuda`). Batch 1's
decoder is PyAV with `hwaccel="videotoolbox"` and a silent software fallback
(`lunascan/ingest/decoder.py` `_has_videotoolbox()`), and a Linux box with the NVIDIA
driver exposes NVDEC instead (`ffmpeg -hwaccels` lists `cuda`; `h264_cuvid`/`hevc_cuvid`
decoders are present). So the port for those two batches is a device/hwaccel selection
change, NOT a rewrite — add `cuda` to the device order and swap the hwaccel per platform.
Do not tell the user those stages "cannot run" off Apple Silicon; they can, with two
small edits. The genuinely Apple-only pieces are CoreML export (`export_coreml()`) and the
PySide6 `.dmg` GUI, and those should stay on the Mac anyway.

Two facts decide the setup, and both are easy to get wrong:

- **The ODM image tag must be the GPU build.** `opendronemap/odm:<ver>` is CPU-only and will
  ignore the card even under `--gpus all`; `opendronemap/odm:<ver>-gpu` is the CUDA one.
  Pull the `-gpu` tag on a box that has `nvidia-container-toolkit` installed. Keep the CPU
  tag as the default in `odm.py` so Mac hosts keep working — select the GPU tag per host
  rather than hardcoding it into the module default.
- **Keep the version pin.** Pin the GPU tag to the same version as the CPU pin
  (`3.6.1-gpu`), for the same reason as 9b-ii: `:latest` moved the matcher defaults and
  exploded the pair count. A GPU build of the wrong version reintroduces that problem.

Verify the accelerator is really in use — VRAM rising and a non-zero utilization peak while
matching runs. A container that starts cleanly and idles at 0% GPU is executing on the CPU.

Measured on 150 frames of the 720p test clip, production flags
(`--feature-quality medium --pc-quality medium --mesh-octree-depth 9 --matcher-order 8
--end-with mvs_texturing`):

| host | time | output |
|---|---|---|
| RTX 4070 SUPER, 20 cores, 60GB | 160 s | 3.5MB glb, 194,792 verts |
| M1 Pro, 10 cores, 7.75GB Docker | 690 s | 3.9MB glb, 194,121 verts |

~4.3x, with equivalent output (same mesh count, vertex count within 0.3%). The Mac figure
already includes all the matcher/quality tuning documented above; the GPU run needed none
of it to reach its number.

Two prerequisites that bite on a fresh Linux box:
- `colmap` from apt installs but then fails at runtime on a missing `libPoseLib.so`.
  Harmless for ODM (containerised), but fix it before relying on any host-side SfM stage.
- Keep keyframes at `--max-dim 1920`. On a big box the temptation is to raise it, but the
  OpenMVS fusion ceiling is about per-frame pixels, not host RAM — 4K keyframes OOM the
  container's default limit no matter how much memory the host has.

**Measured stage speedups on the same hardware pair** (RTX 4070 SUPER vs M1 Pro):

| stage | Mac M1 Pro | GPU box | ratio |
|---|---|---|---|
| Batch 2 masking (yolov8n-seg, 150 frames) | 25.0 fps | 315 fps | 12.6x |
| Batch 3+4 ODM (150 frames) | 690 s | 160 s | 4.3x |
| splat training (7k iters, 119k gaussians) | ~2.3 h | 244 s | ~34x |

Small-model inference fits in the VRAM headroom a resident LLM server leaves (~5GB free
was enough); reconstruction and splat training want the whole card. Quote the measured
ratio and the caveat that the Mac number already includes a long tuning session — the GPU
number needed none of it.

**CUDA torch installs cleanly on modern Ubuntu/python.** Ubuntu 26.04 with Python 3.14 is
fine — `pip install torch torchvision` from the default index already resolves to a CUDA
build (`+cu130`) on Linux, and `torch.cuda.is_available()` returns True. The trap is the
reverse: a venv created with `--system-site-packages` or an older index can land a CPU-only
wheel, so assert `torch.cuda.is_available()` before benchmarking rather than after.

The two device-selection sites to port are `lunascan/masking/detector.py` (`_detect_device`)
and `lunascan/ingest/decoder.py` (`_has_videotoolbox`).

## CLI entry points

| Module | Command |
|--------|---------|
| Ingest | `.venv/bin/python -m lunascan.ingest.cli --input video.mp4 --output frames/` |
| Masking | `.venv/bin/python -m lunascan.masking.cli --keyframes frames/ --output masks/` |
| SFM | `.venv/bin/python -m lunascan.sfm.cli --keyframes frames/ --output sfm/` |
| Export | `.venv/bin/python -m lunascan.export.cli --input sparse_cloud.ply --output model.glb` |
| Pipeline | `.venv/bin/python -m lunascan.pipeline --video drone.mp4 --output-dir ./out` |

## Output: local-only, web-optimized (no R2 export)

**Founder directive (2026-08-07):** LUNASCAN does NOT export to R2. Output is saved to a user-selected local folder (or auto-created default); the `.dmg` installer for LunaV is hosted on R2 separately (that is serving a static file, NOT pipeline output — compatible with the directive). The old `--r2-upload`/`--r2-bucket`/`--r2-prefix` pipeline flags were REMOVED.

Pipeline stages now:

```
Batch 1 ingest → Batch 2 masking → Batch 3+4 ODM (Docker) → Batch 5 optimize
```

Batch 5 (`lunascan/optimize.py`) post-processes the ODM `.glb` into a web-ready asset. Flags: `--no-optimize`, `--skip-texture-optimize`. Graceful: if `node` or `tools/3d-optimize/optimize.mjs` is missing, it logs a warning and keeps the raw ODM glb (RC=0).

```bash
.venv/bin/python -m lunascan.pipeline \
  --video drone.mp4 --output-dir ./out        # local folder; auto-created if missing
```

Default GUI output (when user picks none): `~/LUNASCAN_Output/<video_stem>` — NOT `/tmp` (was hardcoded `/tmp/lunascan` before 2026-08-07; `/tmp` is ephemeral, do not revert).

## Distribution: LunaV viewer + local-first installer (2026-08-07)

LUNASCAN produces `.glb` locally; LunaV (Next.js) is the viewer only. The integration story changed by founder directive:

- **REMOVED** the "Import from LUNASCAN" button + `ImportScanModal` from LunaV (`src/components/ProjectWorkspace.tsx`) and its `handleImportScan` handler / `importOpen` state / `ImportScanModal` + `ScanGroup` imports. LunaV no longer pulls from R2. The orphaned `ImportScanModal.tsx` file can stay (unused) — do not re-add the button unless the user reverses.
- **ADDED** a Settings panel on the LunaV dashboard (`src/app/dashboard/page.tsx`) with a "LUNASCAN Desktop App" download card. The link is driven by `process.env.NEXT_PUBLIC_LUNASCAN_DMG_URL` (Next.js public env var) so the real URL is set in ONE place (`.env.local`). When unset, the button is dimmed + disabled with a "not configured" note — never hardcode/fabricate a URL.
- **Hosting the installer is a SEPARATE R2 use from pipeline export.** The directive "LUNASCAN does NOT export to R2" refers to pipeline *output*; serving the static `.dmg` from a public R2 object (or GitHub release) is compatible. Bucket + public URL are set by the user (credentials were never in this session).
- Verification: `cd lunavsolution-code && npx next build` must pass (TypeScript clean). The removed-button + new-Settings edits were verified building with 0 errors.

**DMG deliverable:** `dist/LUNASCAN.dmg` (~456 MB after bundling `app` + `tools/3d-optimize` + `lunascan`). Rebuild after ANY source change (see pitfall 5 / section 21c). To host: `aws s3 cp dist/LUNASCAN.dmg s3://<bucket>/LUNASCAN.dmg --endpoint-url <r2>` then set `NEXT_PUBLIC_LUNASCAN_DMG_URL` to the public URL.

## Desktop GUI app (`app/`)

Lightweight macOS native wrapper that lets field inspectors run the pipeline without CLI:

```
app/
  __init__.py        # package marker
  __main__.py        # python -m app entry
  run.py             # launch script (adds repo root to sys.path)
  worker.py          # QThread → 4-batch pipeline (signals to GUI)
  main_window.py     # PySide6 window: drag-drop, progress bars, console, publish toggle
  publish.py         # R2 upload + Supabase POST /rest/v1/models attach
build_app.py          # PyInstaller → macOS .app / .dmg
```

**Architecture pattern:**
- `PipelineWorker(QThread)` runs `lunascan.pipeline` stages sequentially, emitting `stage_started(name)`, `stage_progress(name, pct)`, `stage_finished(name, dt)`, and `log_message(line)` signals.
- GUI connects these signals to 4 per-batch `QProgressBar` widgets and a `QTextEdit` console.
- `_SignalStream` (io.TextIOBase subclass) intercepts logger output and forwards via Qt signal.
- Publish path: `app/publish.py` → `lunascan.storage.r2.R2Uploader` → R2 bucket, then POST to Supabase `/rest/v1/models` with `service_role` key.

**Install + run:**
```bash
.venv/bin/pip install -e '.[gui]'      # pulls PySide6 + pyinstaller
.venv/bin/python app/run.py            # launch GUI
.venv/bin/python build_app.py --dmg    # package as LUNASCAN.dmg
```

**GUI control pattern — Cancel + Reset:** the action row has three buttons: a green **Start Pipeline**, a red-outline **Cancel**, and a dark **Reset**. Cancel terminates the running worker thread. Reset clears all inputs (video path, telemetry, progress bars, stage labels, console) and returns to "Ready" state — useful after a failed run so the user doesn't have to quit and re-open the app. The `_reset_all()` method lives in `app/main_window.py` and is connected to the Reset button in `_build_ui()`. Both Cancel and Reset terminate the worker safely before clearing state.

**Verification pitfall — PySide6 headless:** importing `app.main_window` or `app.__main__` hangs in CI/headless because `PySide6.QtWidgets` needs a macOS window server. Ad-hoc verification MUST skip GUI-module imports and test only `app.worker`, `app.publish`, signal plumbing, and `build_app.py` syntax. Set `QT_QPA_PLATFORM=offscreen` to allow GUI imports without a display.

**LunaV publish env vars required:**
- `R2_ACCESS_KEY_ID`, `R2_SECRET_ACCESS_KEY`, `R2_ENDPOINT_URL` — for `lunascan.storage.r2`
- `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY` — for model-attach API call
- `R2_ACCOUNT_ID` — to construct `pub-<id>.r2.dev` public URL
- Missing any → graceful skip (warning logged, continues locally)

## Supabase edge-function deployment pitfalls

- **"Via AI Assistant" auto-names functions** — Supabase's AI picks random adjective-noun names (e.g. `bright-action`). Use **"Via Editor"** to set the exact function slug.
- **JWT verification toggle** — keep ON when the function reads `Authorization` header and calls `supabase.auth.getUser()`. The dashboard's "Recommended: OFF" note applies only when JWT is handled elsewhere (e.g. by a gateway).

### 22. Docs-vs-git-state drift — VERIFY live repo state before claiming "done" or "advancing"

The skill body and `Obsidian/Projects/LUNASCAN.md` describe the 08-07 ODM migration + Batch 5 + DMG rebuild as completed ("99/99 tests pass, DMG rebuilt, commit 268005d"). On 2026-08-10 a live check showed **all of that work was sitting UNCOMMITTED and UNPUSHED** in the working tree — last real commit was `a004ba4` (08-05 PySide6 GUI); `git log origin/main..HEAD` empty = local main == remote main. The "done" claims were written to Obsidian/skill but never landed on GitHub.

**Lesson:** never trust a "done/committed" claim from the skill or Obsidian alone. Before reporting project status or "advancing," run this verification set from `~/Documents/LUNASCAN`:

```bash
git fetch origin
git log origin/main..HEAD --oneline          # empty = nothing unpushed
git status -s                                  # M / ?? = uncommitted work
git diff --stat                                # scope of uncommitted changes
.venv/bin/python -m pytest tests/ -q          # 113 expected as of 2026-08-10; confirm green
```

**Repo-hygiene gotcha — STRAY / LARGE files in the LUNASCAN root that must NOT be committed as part of LUNASCAN:**
- `rover_body.py` + `rover_output/` — FreeCAD 6-wheel rover chassis design, a DIFFERENT project. Exclude from LUNASCAN commits.
- `dist/` (2.4 GB `LUNASCAN.dmg`) — built installer; HOSTED ON R2 separately (serving the static `.dmg` is a separate R2 use, permitted by the "no R2 export" directive). Never commit it.
- `lunascan/models/vocab_tree_flickr100K_words256K.bin` (112 MB) — EXCLUDE. Exceeds GitHub's 100 MB hard push limit AND crashes COLMAP 4.1's `vocab_tree_matcher` with SIGABRT (Pitfall 9). The matcher is `exhaustive` now anyway; this tree is dead weight.
- `lunascan/models/yolov8n-seg.pt` (6.7 MB) — COMMIT. Bundled YOLO model, resolved by `_resolve_model_path` (Pitfall 6) and copied via build_app `--add-data=lunascan:lunascan`.
- `tools/3d-optimize/node_modules/` — EXCLUDE, gitignore it. Reproducible via `npm install` from `package.json`/`package-lock.json` (which ARE committed). The DMG build copies the folder; node_modules regenerates on build host.
- `.DS_Store`, `build/` (PyInstaller cache), `LUNASCAN.spec` — exclude (OS/cache cruft).

**Verified ground-truth commit:** the 08-07 ODM migration + Batch 5 + DMG packaging landed as `1cdcf09` (pushed to `origin/main` 2026-08-10, local == remote). It committed: `lunascan/odm.py`, `lunascan/optimize.py`, `lunascan/docker_util.py`, `lunascan/models/yolov8n-seg.pt`, `tools/3d-optimize/{optimize.mjs,package.json,package-lock.json}`, all `lunascan/` + `app/` + `tests/` source edits, updated `.gitignore`. Stale references in this skill/Obsidian to "commit 268005d" for the ODM work are WRONG — `268005d` is the 2026-08-05 R2 storage commit, which predates ODM.

When committing a milestone batch (per the validation ritual in 9b-i), stage only LUNASCAN source + the new `lunascan/odm.py`, `lunascan/optimize.py`, `lunascan/docker_util.py`, `tools/3d-optimize/`. Commit with `git -c user.name=maru -c user.email=kingkymaru@gmail.com` for author consistency (matches the durable convention).

**Also:** `Obsidian/Projects/HermesProgress.md` is referenced in `LUNASCAN.md` but does NOT exist (dead link as of 2026-08-10). Recreate it or drop the reference when touching the vault.

## Per-batch skills

- `lunascan-batch-1-ingest` — VideoToolbox decode + telemetry + keyframe selection
- `lunascan-batch-2-masking` — CoreML YOLO seg + binary mask generation