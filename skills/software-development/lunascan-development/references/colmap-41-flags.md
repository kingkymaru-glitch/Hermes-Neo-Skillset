# COLMAP 4.1 flag migration

COLMAP 4.1.0 renamed several CLI flags from the 3.x series. All commands that pass flags to COLMAP subprocesses must use the 4.1 names.

## Flag mapping

| Old (COLMAP 3.x) | New (COLMAP 4.1) | Used in |
|-------------------|------------------|---------|
| `--SiftMatching.use_gpu` | `--FeatureMatching.use_gpu` | `exhaustive_matcher`, `sequential_matcher` |
| `--SiftMatching.gpu_index` | `--FeatureMatching.gpu_index` | `exhaustive_matcher`, `sequential_matcher` |
| `--SiftExtraction.num_threads` | `--FeatureExtraction.num_threads` | `feature_extractor` |
| `--Mapper.ba_global_images_ratio` | `--Mapper.ba_global_frames_ratio` | `mapper` |

## How to discover correct flags

COLMAP 4.1 help goes to **stderr**, not stdout. Always use `2>&1`:

```bash
colmap exhaustive_matcher --help 2>&1 | grep FeatureMatching
colmap mapper --help 2>&1 | grep ba_global
colmap feature_extractor --help 2>&1 | grep FeatureExtraction
```

## Automated check

Run `scripts/verify-colmap-flags.py` — it parses `lunascan/sfm/pipeline.py` for stale old-name flags and cross-references against the actual `colmap --help` output to confirm new names are valid.

## Hand-rolled SQLite DB incompatibility

COLMAP 4.1 cannot open manually-created SQLite databases (as done by `lunascan/sfm/extractor.py`). The internal database factory layer rejects them with `SQL logic error` / `No registered database factory succeeded` followed by SIGABRT. Always use `colmap feature_extractor` to create the initial database — it sets up the correct schema and metadata.