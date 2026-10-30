# SFM Matching Strategies & COLMAP 4.1 Migration

## Matching strategy comparison (96 DJI 4K keyframes, real test)

| Strategy | Command | Complexity | Match time | Total time | Result |
|----------|---------|-----------|------------|------------|--------|
| `sequential` **(default)** | `sequential_matcher` | O(n) | 27.6s | 124.9s | No reconstruction (nadir footage) |
| `exhaustive` | `exhaustive_matcher` | O(n²) | 130.5s | 233.9s | No reconstruction (nadir footage) |
| `vocab_tree` | `vocab_tree_matcher` | O(n log n) | N/A | CRASH (SIGABRT) | FLANN tree incompatible with COLMAP 4.1 FAISS — NO graceful fallback at the matcher stage |

**Winner: exhaustive** — for ~200–1600 frames use `exhaustive` matching. It is the most robust for aerial/low-parallax footage (builds the full match graph). For this DJI 4K flight, `sequential` and `vocab_tree` both failed (`sequential` → no reconstruction; `vocab_tree` → SIGABRT crash). `exhaustive` ran ~300s on 209 frames — acceptable. Do NOT use `vocab_tree`: the bundled 112MB tree is FLANN-format and crashes COLMAP 4.1's `vocab_tree_matcher` (no fallback). Scale past ~2000 images via spatial/exhaustive sharding, not vocab_tree.

## COLMAP 4.1 flag migration table

Always verify flag names with `colmap <subcommand> --help 2>&1` — help output goes to stderr.

| COLMAP 3.x flag | COLMAP 4.1 flag |
|-----------------|-----------------|
| `--SiftMatching.use_gpu` | `--FeatureMatching.use_gpu` |
| `--SiftMatching.gpu_index` | `--FeatureMatching.gpu_index` |
| `--SiftExtraction.num_threads` | `--FeatureExtraction.num_threads` |
| `--Mapper.ba_global_images_ratio` | `--Mapper.ba_global_frames_ratio` |

## Native feature_extractor requirement

COLMAP 4.1's internal database factory rejects hand-crafted SQLite databases. **Always use `colmap feature_extractor`** to create the initial DB — do not use the legacy `extractor.py` `write_colmap_db` method.

Error signature of hand-rolled DB:
```
database_sqlite.cc:1657] SQLite error: SQL logic error
database.cc:52] Failed to open database with registered factory
No registered database factory succeeded.
*** SIGABRT ***
```

`COLMAPPipeline.run_feature_extraction(db_path, image_dir)` handles this correctly:
- Creates parent directory (`db.parent.mkdir(parents=True, exist_ok=True)`)
- Removes existing DB
- Runs `colmap feature_extractor --FeatureExtraction.num_threads -1`

Trade-off: mask filtering (keypoint removal in dynamic-object regions) is lost.

## Vocab tree: FLANN → FAISS incompatibility

COLMAP 4.1 switched vocabulary tree storage from FLANN to FAISS (May 2025). Prebuilt FLANN trees crash:

```
visual_index.cc:690] Check failed: file_version == 1 || file_version == 2
Failed to read faiss index. This may be caused by reading a legacy flann-based index...
*** SIGABRT ***
```

The bundled `lunascan/models/vocab_tree_flickr100K_words256K.bin` (112MB) is FLANN format. **`vocab_tree_matcher` crashes with SIGABRT** — there is NO graceful fallback at the matcher stage (unlike the feature-extractor path). Do not use `vocab_tree` matching on COLMAP 4.1. To enable vocab tree matching you would need to build a FAISS-compatible tree with `colmap vocab_tree_builder` from a large (>1000 image) dataset — but prefer `exhaustive` for typical drone sets.

## COLMAP binary discovery from DMG sandbox

`_find_colmap()` in `lunascan/sfm/pipeline.py` searches:
1. `shutil.which("colmap")` — PATH-based (works in dev, fails in DMG sandbox)
2. `/opt/homebrew/bin/colmap` — Apple Silicon Homebrew
3. `/usr/local/bin/colmap` — Intel Homebrew

`COLMAPPipeline.available` validates: `which()` check OR file-exists + executable. Explicit `colmap_bin=` paths validated same way.

## Signal handling in subprocess

COLMAP crashes (SIGABRT) produce negative return codes in Python's `subprocess.run()`:
- `returncode < 0` → killed by signal → `_run()` raises `CalledProcessError`
- `returncode == 1` → COLMAP macOS warning → logs stderr, continues  
- `returncode > 1` → real failure → raises `CalledProcessError`

## Code locations

| Component | File | Line/Area |
|-----------|------|-----------|
| Matching strategies | `lunascan/sfm/pipeline.py` | `_run_matching()` method |
| Vocab tree resolver | `lunascan/sfm/pipeline.py` | `_resolve_vocab_tree()` function |
| COLMAP discovery | `lunascan/sfm/pipeline.py` | `_find_colmap()` function |
| Feature extraction | `lunascan/sfm/pipeline.py` | `run_feature_extraction()` method |
| Flag constants | `lunascan/sfm/pipeline.py` | `_COLMAP_CANDIDATES`, `_VOCAB_TREE_FILENAME` |
| CLI argparse | `lunascan/sfm/cli.py` | `--matching` choices line 38 |
| Pipeline argparse | `lunascan/pipeline.py` | `--matching` default line 193 |
| Worker hardcoded | `app/worker.py` | `_run_sfm()` call line 117 |

## Verification script

Run `scripts/verify-colmap-flags.py` to check that pipeline code uses correct COLMAP 4.1 flag names against the installed binary.