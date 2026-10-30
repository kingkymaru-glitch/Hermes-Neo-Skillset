# Nadir Drone SfM Troubleshooting

## The problem

Downward-facing (nadir) drone footage produces near-parallel camera rays. COLMAP's sparse mapper triangulates 3D points by intersecting rays from multiple cameras — if all rays are nearly parallel, the intersection is poorly constrained and the mapper fails to initialise even a single image pair.

## Overlap calibration for nadir footage

Keyframe density matters more for nadir footage than for oblique. The L1 diff on 64x64 thumbnails prunes frames based on visual change, but for SfM you need spatial diversity. With nadir footage, you need MORE keyframes (not fewer) because the angular separation between frames is tiny.

Calibrated on a 4K 30fps DJI video (~1 min, stable pan at ~120m altitude):

| Overlap | Threshold | Keyframes | % of total | SfM viable? |
|---------|-----------|-----------|------------|-------------|
| **0.95**| **13**    | **~700**  | **~38%**   | **Yes, dense** |
| 0.90    | 25        | 365       | 19.8%      | Yes, heavy |
| 0.85    | 38        | 96        | 5.2%       | Barely |
| 0.80    | 51        | 27        | 1.5%       | No |
| 0.75    | 64        | 6         | 0.3%       | No |
| 0.60    | 102       | 1         | 0.05%      | No |

**Current default: 0.95** (`pipeline.py --step-sec`, `worker.py` hardcoded value). The min_keyframes=10 safeguard in `keyframe.py` provides a floor — if overlap-based selection drops below 10, it falls back to uniform sampling.

## Symptoms

- Mapper runs for 60-130s and produces NO sparse model (empty `sparse/` directory)
- Log shows "no reconstruction found"
- No crash or SIGABRT — the mapper exits cleanly with rc=0 or rc=1
- Feature extraction succeeds (DB is 140MB+ for ~100 frames)
- Matching completes normally (28s sequential, 130s exhaustive)

## Parameter checklist (COLMAP 4.1)

All set in `lunascan/sfm/pipeline.py`:

| Flag | Default | LUNASCAN value | Effect |
|------|---------|---------------|--------|
| `SiftExtraction.max_num_features` | 8192 | 16000 | More keypoints → more matches |
| `SiftExtraction.first_octave` | -1 | -1 | Start at full resolution |
| `Mapper.init_min_tri_angle` | 16 | 1 | Accept acute triangulation |
| `Mapper.multiple_models` | 1 | 0 | Force single global model |
| `Mapper.min_num_matches` | 15 | 5 | Accept pairs with few inliers |
| `Mapper.ba_global_function_tolerance` | 0 | 0 | Disable early stopping |

`init_min_tri_angle` is the most impactful. At default 16°, COLMAP requires at least 16° between camera rays to triangulate. Nadir at 120m with 2m forward movement between frames gives ~1° — 16° rejects everything.

## Diagnostic commands

```bash
# Check if mapper produced anything
ls /path/to/sfm/sparse/
# Should contain: cameras.bin, images.bin, points3D.bin (or subdirectory 0/)

# Manual re-run with verbose output
colmap mapper --database_path /path/to/colmap.db \
  --image_path /path/to/keyframes \
  --output_path /path/to/sfm \
  --Mapper.init_min_tri_angle 1 \
  --Mapper.multiple_models 0 \
  --Mapper.min_num_matches 5 \
  --Mapper.ba_global_function_tolerance 0 \
  --log_to_stderr 1 2>&1 | tee mapper.log
```

## If it still fails

The footage genuinely lacks angular diversity. Options:

1. **Fly a grid pattern** — cross-pass flight lines so each point on the ground is seen from at least 2-3 different angles
2. **Tilt the camera** — 20-30° off-nadir instead of straight down
3. **Add GPS/telemetry priors** — wire `georef.py` GPS injection into the pipeline. GPS priors seed bundle adjustment with known camera positions, which can bootstrap reconstruction even with weak geometry

No algorithm can fix zero parallax. If every frame is taken from the same camera angle pointing at the same flat surface, triangulation is mathematically impossible regardless of parameters.