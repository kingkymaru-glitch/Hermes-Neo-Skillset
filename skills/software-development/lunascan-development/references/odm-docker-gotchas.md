# ODM Docker Gotchas — condensed field notes (2026-08-07)

LUNASCAN Batch 3+4 uses OpenDroneMap (`opendronemap/odm:latest`) via Docker as
the dense reconstruction engine (replaces COLMAP, which failed 3x on smooth
drone footage). These are the non-obvious failure modes and their fixes, with
verbatim error signatures so you can recognise them fast.

## 0. Prerequisite — Docker daemon must be up
ODM is a Docker image. If the daemon isn't running, the run dies on
pull/connect. Cannot be started headlessly.
- Symptom: `docker: Cannot connect to the Docker daemon at unix:///var/run/docker.sock.`
- Fix: ask the user to launch Docker Desktop. `docker info` should return cleanly.

## 1. Wrong CLI shape — `--images` rejected
ODM 4.x wants a **positional dataset name**, not `--images`. Stage images in
`<project>/code/images` and mount `<project>:/datasets`, then:
```
docker run --rm -v <project>:/datasets opendronemap/odm:latest --project-path /datasets code [flags]
```
- Symptom: `odm: error: unrecognized arguments: --images ...`
- Fix: `build_docker_command()` emits `code` positionally; images go in
  `output/odm/code/images` (set by `run_odm` before the docker call).

## 2. Meshing DEM tile overflow on large sites
- Symptom (in `odm/code/log.json`):
  ```
  renderdem ... --max-tiles 165 ...
  DEM resolution is (288024, 1374183), ... will split DEM generation into 23856 tiles
  Max tiles limit exceeded (165). This is a strong indicator that the reconstruction failed
  ```
  Note: the SfM reconstruction itself SUCCEEDED (e.g. `Reconstruction 0: 329 images, 14042 points`).
- Cause: at fine `--orthophoto-resolution` (2 cm/px) the meshing DSM is huge.
  The meshing stage runs `renderdem` (to build the DSM for the mesh) and hits
  the 165-tile cap BEFORE texturing. `--end-with mvs_texturing` does NOT skip
  this (meshing is before texturing).
- Fix: `--orthophoto-resolution 20` (coarse). 2 cm → 23856 tiles; 20 cm → ~60
  tiles < 165. Textured-mesh quality is set by `--mesh-octree-depth` (default
  9), NOT orthophoto resolution, so this is safe.
- Memory note: also keep keyframes ≤ ~200 (see §4). 701 at 250/329 frames OOM'd
  OpenMVS fusion at Docker's default 7.75 GB; 150 frames fit.

## 3. ODM exits non-zero but still writes the .glb
- Symptom: `OpenMVS ran out of memory, we're going to turn on tiling to see if
  we can process this.` then a non-zero docker exit, yet
  `odm/code/odm_texturing/odm_textured_model_geo.glb` EXISTS.
- Old behaviour: `run_odm` did `if proc.returncode != 0: return _fail(...)` —
  aborted BEFORE copying, so no `site_model.glb`.
- Fix: in `run_odm`, locate the `.glb` FIRST; if present, accept the run as
  degraded-success (warn) and copy it. Only fail if no `.glb` was produced.
- Verify: `scripts/verify-odm-run-resilience.py` (mocks docker, asserts copy).

## 4. OpenMVS fusion RAM ceiling (Docker default 7.75 GB)
- ODM dense fusion OOMs above ~250 4K keyframes at the default Docker RAM limit.
  703 (209 kf) fit; 701 (250 then 329) did not.
- Fix: cap keyframes with `--max-frames 150` (or ≤ ~200). Wire: ingest CLI
  `--max-frames` → `select_keyframes_stream(max_keep=...)`. To allow more
  frames, raise Docker Desktop → Resources → Memory.

## 5. Geo-tagging — use piexif, not raw PIL GPS IFD
LUNASCAN's VideoToolbox decode drops EXIF, so GPS must be re-embedded into each
keyframe JPEG before ODM (ODM reads GPS from EXIF).
- BUG: hand-building a PIL GPS IFD dict with rationals → `bad operand type for
  abs(): 'tuple'` / "tag 6 had too many entries" → JPEG corrupted on save.
- Fix: use **piexif** (`piexif.dump` + `Image.save(..., exif=...)`). Install:
  `.venv/bin/pip install piexif`. `load_telemetry_gps` aligns by frame index
  (telemetry record `i` ↔ image `i+1`).

## 6. Find the right glb
ODM writes `odm_texturing/odm_textured_model_geo.glb` (geo-referenced). Prefer
it over the bare `odm_textured_model.glb`. `find_glb()` checks both + rglob.

## Repro / verify
- Command shape: `scripts/verify-odm-command.py`
- Run resilience: `scripts/verify-odm-run-resilience.py`
- End-to-end: run 703 AND 701 to a `site_model.glb` before declaring done.
