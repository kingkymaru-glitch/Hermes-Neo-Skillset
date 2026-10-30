---
name: opendronemap-photogrammetry
description: Reconstruct 3D .glb from drone imagery via OpenDroneMap.
---

# OpenDroneMap (ODM) Drone Photogrammetry

ODM (`opendronemap/odm:latest`, Docker) is the purpose-built engine for drone/aerial
imagery: dense SfM → MVS depth maps → fused point cloud → mesh → textured `.glb`.
Prefer it over COLMAP when footage is smooth/near-planar (COLMAP's sequential/exhaustive
matcher silently yields "no reconstruction found" even with GPS priors + correct focal).

## When to use
- Turn raw drone video keyframes (or a folder of stills) into a geo-referenced `.glb`.
- COLMAP mapper failed 2+ times on the same dataset.
- You need a *textured dense* model, not just a sparse point cloud.

## Hard-won CLI gotchas (ODM refuses to tell you these)
The ODM container entrypoint is `run.sh <dataset name>`. Get any of these
wrong and it errors out or silently produces nothing.

1. **Positional dataset name, NOT `--images`.** Images must live in
   `<mount>/<dataset>/images`. Mount your project dir to `/datasets`, pass the
   dataset name as a bare positional arg. Wrong: `--images /datasets/images`.
   Right: `-v $PROJECT:/datasets opendronemap/odm:latest --project-path /datasets code`
   with images at `$PROJECT/code/images`.
2. **`--orthophoto-resolution` drives the meshing DEM tile limit.** ODM runs
   `renderdem --max-tiles 165` during meshing to build the DSM. Fine resolution
   (e.g. `2` cm/px) on a large site → tens of thousands of tiles →
   `"Max tiles limit exceeded (165). This is a strong indicator that the reconstruction failed"`
   and the run aborts before texturing. **Coarsen to `20`** (textured-mesh quality is set
   by `--mesh-octree-depth`, not this). 2 cm/px overflowed a 4502-frame flight (23856 tiles);
   20 cm/px is safe.
3. **`--end-with mvs_texturing`** stops processing after the textured model (skips the
   slow orthophoto/DEM export stages). The `--gltf` export still runs. Use this when you
   only want the 3D model (e.g. for a viewer upload), not an orthophoto.
4. **Accept ODM's non-zero exit if a `.glb` was produced.** ODM sometimes exits non-zero
   (OpenMVS tiling fallback, `--end-with` skipping later stages) yet still writes a valid
   `odm_texturing/odm_textured_model_geo.glb`. If the artifact exists, copy it and treat
   the run as a degraded success — do NOT fail the whole pipeline.
5. **Geotag keyframes with GPS before handing to ODM.** If frames were decoded programmatically
   (VideoToolbox/av/OpenCV), EXIF is dropped. Embed GPS via `piexif` (PIL's raw GPS IFD
   handling is fragile — see references). ODM reads GPS from image EXIF for georeferencing.

## Memory / scale bounds (the silent killer)
- **OpenMVS depth-map *fusion* OOMs above ~250 keyframes at Docker's default 7.75 GB RAM
  limit** (on a 16 GB Mac, Docker Desktop defaults to ~7.75 GB). Symptoms: log shows
  `OpenMVS ran out of memory, we're going to turn on tiling` then the process is SIGKILLed.
  A 209-frame flight fit; 250 and 329 both OOM'd. **Cap keyframes to ~150–200** for the
  default Docker RAM ceiling. (Raising Docker's memory limit in Docker Desktop → Settings →
  Resources is the alternative, but not always available.)
- **Ingest must stream, never materialize.** Decoding all 4K frames into a list (~1843 frames
  ≈ 46 GB) gets SIGKILLed (-9). Decode → compare → save → discard, holding ~2 frames
  (O(1) RAM). Add a `--max-frames` cap that the keyframe selector honors.

## Minimal correct ODM command (reference)
See `references/odm_command.md` for the full template + the geotag snippet + RAM math.

## Verification discipline
- Verify edits with the test suite AND a small ad-hoc script (heredoc into the repo, run,
  delete) — do NOT rely on a single successful pipeline run, because long ODM runs produce
  late-arriving background-process exit notifications that can be mistaken for current state.
- Confirm the produced `.glb` is valid by checking magic bytes (`676c5446` = "glTF") and
  non-zero size.

## Pitfalls
- Don't pass `--images` to ODM — it's unrecognized. Use the positional dataset name.
- Don't leave `--orthophoto-resolution` at 2 for large sites — DEM tile overflow.
- Don't treat ODM exit != 0 as hard failure if `odm_textured_model_geo.glb` exists.
- Don't materialize all decoded frames in RAM; stream.
- Don't assume COLMAP "no reconstruction found" means the data is bad — try ODM.
