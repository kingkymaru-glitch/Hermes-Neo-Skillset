# COLMAP discovery in PyInstaller DMG sandbox

## Symptom

Batch 3 (SFM) fails when run from the `.app`/`.dmg`:

```
ERROR    COLMAP not found. Install: brew install colmap
ERROR: Batch 3 failed (rc=1)
```

COLMAP is installed (`brew list colmap` shows it), but the app can't find it.

## Root cause

`shutil.which("colmap")` searches `PATH`. PyInstaller `--windowed` macOS app bundles have a minimal `PATH` that does NOT include Homebrew paths:

- `/opt/homebrew/bin` (Apple Silicon) — NOT in DMG PATH
- `/usr/local/bin` (Intel) — NOT in DMG PATH

So `which("colmap")` returns `None` inside the DMG, even though the binary exists on disk.

## Fix: `_find_colmap()` with hardcoded fallbacks

In `lunascan/sfm/pipeline.py`:

1. **`_find_colmap()`** — tries `shutil.which("colmap")` first (works in dev/CLI),
   then checks hardcoded Homebrew paths directly with `os.access(path, os.X_OK)`

2. **`COLMAPPipeline.available` property** — validates the resolved path by calling
   `which()` on it AND checking file existence, not just checking a non-None string.
   This means explicit paths like `colmap_bin="/nonexistent/colmap"` correctly
   return `available=False`.

3. **Path caching** — `available` resolves once via `which()` and caches the result
   back to `self._colmap`, so `run_full()` uses the fully resolved binary path.

## Verification

```python
from lunascan.sfm.pipeline import _find_colmap, COLMAPPipeline

# Default discovery
assert _find_colmap() is not None
assert COLMAPPipeline().available is True

# Bad path → unavailable
assert COLMAPPipeline(colmap_bin="/nonexistent/colmap").available is False

# Good hardcoded path → available
assert COLMAPPipeline(colmap_bin="/opt/homebrew/bin/colmap").available is True

# None fallback → discovers
assert COLMAPPipeline(colmap_bin=None).available is True
```

## DMG rebuild required

Changes to `lunascan/sfm/pipeline.py` require a DMG rebuild:
```bash
.venv/bin/python build_app.py --dmg
```

## Future: additional install paths

If COLMAP is installed elsewhere (MacPorts `/opt/local/bin`, etc.), add the
path to `_COLMAP_CANDIDATES` list at the top of `pipeline.py`.

## COLMAP 4.x flag renames

Homebrew currently installs COLMAP 4.1.x. Several CLI flags changed between
COLMAP 3.x and 4.x. The pipeline code in `lunascan/sfm/pipeline.py` uses
the 4.x names:

| Old (COLMAP 3.x) | New (COLMAP 4.x) |
|---|---|
| `--SiftMatching.use_gpu` | `--FeatureMatching.use_gpu` |
| `--SiftMatching.gpu_index` | `--FeatureMatching.gpu_index` |
| `--Mapper.ba_global_images_ratio` | `--Mapper.ba_global_frames_ratio` |

**How to check your COLMAP version's flags:**

```bash
# List all matching-related options
colmap exhaustive_matcher --help 2>&1 | grep -i "gpu\|FeatureMatching"

# List all mapper options
colmap mapper --help 2>&1 | grep "ba_global"
```

Note: COLMAP writes help to **stderr**, not stdout — always use `2>&1`.

**Symptom if flags are wrong:**

```
WARNING  colmap stderr:
E... base_option_manager.cc:265] Failed to parse options - unrecognised option '--SiftMatching.use_gpu'.
```

The pipeline continues (it treats return code 1 as a warning), but matching
and mapping may produce no output. SfM fails with "no reconstruction found".

**When upgrading COLMAP:** re-run the `--help` commands above, grep
`pipeline.py` for old flag names, and update. Most flags carry forward but
the `SiftMatching → FeatureMatching` prefix change and `images_ratio →
frames_ratio` rename are the known breaking changes.