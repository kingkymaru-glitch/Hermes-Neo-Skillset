# ODM matching — empirical pair-count data (703 flight, 1610 keyframes @720p)

Measured live on `dji_fly_20260805..._703..._video.mp4` (3840×2160 → `--max-dim 1280`),
telemetry `DJI_0703.SRT` → `telemetry.json` (1842 records). Run command:
`docker logs <cid> 2>&1 | grep -c 'Matching frame'` = total pairs. Rate sampled via
`docker logs --since 20s <cid> 2>&1 | grep -c 'Matching frame'`.

All configs add `--feature-quality low --pc-quality low --ignore-gsd --gltf
--mesh-octree-depth 7 --orthophoto-resolution 20 --end-with mvs_texturing`.

## ⚠️ ODM_VERSION CONFOUNDER
`:latest` resolved to **3.12.3** this session (GPS-embedded matching exploded to 300K+ and
NEVER finished). Pinned **`opendronemap/odm:3.6.1`** in `ODM_IMAGE` (module-level, `run_odm`/
`_run_sfm`/`PipelineWorker` must pass `odm_image=None` so the pin wins — a stale `:latest`
default param clobbers it). The numbers below are ALL on **3.6.1** unless noted.

## Configs tested (time-vs-result)

| # | Config | ODM ver | Pairs | Outcome |
|---|--------|---------|-------|---------|
| 1 | GPS + `--matcher-neighbors 0` (full triangulation) | 3.12.3 | 300K+ | never finished (>16 min) |
| 2 | GPS + `--matcher-neighbors 8` | 3.12.3 | 150K+ climbing | killed |
| 3 | GPS + `--matcher-order 8` | 3.6.1 | ignored→full graph | 126K, killed (order silently skipped on georef) |
| 4 | GPS + `--matcher-neighbors 8` | 3.6.1 | 150K+ climbing | converges, slow (~30-45 min matching) |
| 5 | no-GPS + `--matcher-neighbors 0` | 3.6.1 | 227K @51min | still running, slowest |
| **6** | **no-GPS + `--matcher-order 8`** | **3.6.1** | **6,430** | **✅ full reconstruction ~69 min → valid `site_model.glb` (762 KB)** |

## Decision (RESOLVED, commit `e6c2bc3`)
- **Fast (default, `geo_anchored=False`):** skip GPS geotag → ODM treats images as
  non-georeferenced → honors `--matcher-order 8` (sequential by filename) → ~6.4K pairs.
  Model builds, NOT geo-anchored. This is the only reliably-bounded path.
- **Geo (`geo_anchored=True`):** embed GPS + `--matcher-neighbors 8` → GPS-KNN covisibility
  expansion to ~150-230K pairs. Converges but slow. Use when geo-anchoring matters.
- Flag `--matching-algorithm sequential` does NOT exist in ODM 3.6.1/3.12.3 → exit 2. Never use.
- `--matcher-order` is silently ignored on georeferenced datasets ("applied only on
  non-georeferenced datasets"). So GPS + matcher-order = useless; use matcher-neighbors for geo.

## Verification commands
- Live pair count: `CID=$(docker ps --format '{{.ID}} {{.Image}}' | grep odm:3.6.1 | awk '{print $1}'); echo "pairs: $(docker logs $CID 2>&1 | grep -c 'Matching frame')"`
- Skill script `scripts/verify-odm-command.py` asserts fast=matcher-order 8 + geo=matcher-neighbors 8 + pin 3.6.1.
- Re-run the validated fast config:
  `PYTHONPATH=. .venv/bin/python -m lunascan.pipeline --video <mp4> --telemetry <json> \
   --output-dir ~/LUNASCAN_Output/703_720p_fast --max-dim 1280`  (no `--geo-anchored`)
