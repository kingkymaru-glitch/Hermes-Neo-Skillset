---
name: lunascan-batch-3-sfm
description: LUNASCAN Batch 3 — COLMAP sparse SfM with SIFT + mask filtering + GPS/IMU priors
---

COLMAP-backed sparse Structure-from-Motion for LUNASCAN.  SIFT feature
extraction with binary mask filtering (Batch 2 masks exclude dynamic
keypoints), GPS/IMU telemetry priors injected into COLMAP's images table,
and .ply point cloud export.

## Dependencies

COLMAP must be installed:
  brew install colmap

## Module layout

  lunascan/sfm/
    extractor.py   — SIFT + mask filter + COLMAP SQLite DB write
    georef.py      — LLA→ECEF→ENU, YPR→quaternion, prior injection
    pipeline.py    — COLMAP subprocess (matcher → mapper → PLY export)
    cli.py         — lunascan-sfm CLI with 10 flags

## CLI

  lunascan-sfm \
    --keyframes ./frames/ \
    --masks ./masks/ \
    --telemetry telemetry.json \
    --output /tmp/lunascan/sfm/ \
    --matching exhaustive \
    --nfeatures 4000 \
    --focal 1.2 \
    --ba-iters 50

  --dry-run for config-only.

## Key design decisions

- Mask filtering: SIFT extracted on full image, then keypoints inside
  mask==255 regions removed *before* COLMAP DB write.  More efficient
  than pre-masking images (preserves features near mask boundaries).
- COLMAP DB: SQLite with standard schema.  cameras=SIMPLE_RADIAL
  (model 2), keypoints as float32 blob (x,y,scale,orientation),
  descriptors as uint8 blob (128-dim SIFT).
- GPS priors: LLA→ECEF→ENU conversion relative to first frame.
  prior_tx/ty/tz written to images table; prior_q* identity unless
  yaw/pitch/roll present in telemetry.
- COLMAP pipeline: exhaustive_matcher → mapper (BA 50 iters) →
  model_converter → .ply.

## Test status

22 tests in test_sfm.py:
  - extractor: SIFT detection, mask filtering, DB write/readback,
    zero-keypoint frames
  - georef: ENU conversion, GPS displacement, quaternion identity,
    telemetry (array + GeoJSON)
  - pipeline: COLMAP available, mock stages, failure propagation
  - CLI: dry-run, bad paths, missing images, masks+telemetry combo

## Pitfalls

- Synthetic images must have texture (noise + circles) for SIFT to
  find keypoints on small images (256×256); smooth gradients yield 0.
- COLMAP on macOS returns exit code 1 for warnings even on success;
  pipeline._run() only raises CalledProcessError for rc > 1.
- GPS conversion uses WGS84 ellipsoid; origin is first telemetry record.
- The `keypoints` table in COLMAP expects 4 columns per keypoint (not 6
  with affine shape). SIFT format is correct.

## References

- [COLMAP SQLite schema](references/colmap-schema.md) — table layouts,
  binary blob formats, camera model parameter vectors.
