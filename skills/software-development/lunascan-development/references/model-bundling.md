# Model bundling for PyInstaller DMG

## Symptom

Batch 2 (masking) fails when run from the `.app`/`.dmg`:
```
ERROR: ❌ Download failure for https://github.com/ultralytics/assets/releases/download/v8.4.0/yolov8n-seg.pt.
Retry limit reached. Curl return value 56
```

## Root cause

PyInstaller `--windowed` macOS app bundles have restricted network access. Ultralytics' auto-download of `yolov8n-seg.pt` from GitHub fails. The model file (6.7MB) must be pre-downloaded and bundled inside the app.

## Fix applied

1. **Pre-download model**: `lunascan/models/yolov8n-seg.pt` (6.7MB, committed to repo)
2. **Path resolver**: `lunascan/masking/detector.py` has `_resolve_model_path()` that checks three locations in order:
   - `<MEIPASS>/lunascan/models/yolov8n-seg.pt` — PyInstaller bundle (from `--add-data`)
   - `<package>/../models/yolov8n-seg.pt` — development (alongside source)
   - `yolov8n-seg.pt` — CWD fallback (triggers ultralytics download)
3. **Auto-bundled**: `build_app.py`'s `--add-data=lunascan:lunascan` copies the entire `lunascan/` tree into `Contents/Resources/`, including `models/`
4. **Lazy load**: `DynamicDetector` stores the resolved path but defers `YOLO(path)` to `detect()` time

## Adding a new model

1. Drop `.pt` file in `lunascan/models/`
2. Update `_MODEL_FILENAME` or add the new name to the alias check in `_resolve_model_path()`
3. Update `DynamicDetector.__init__` to call `_resolve_model_path(model)` (already does)
4. Rebuild DMG: `.venv/bin/python build_app.py --dmg`
5. Verify: run `scripts/verify-model-resolver.py`

## Design notes

- `_resolve_model_path` is idempotent — absolute paths pass through, unknown names pass through (for ultralytics download in dev)
- Model is 6.7MB; adds ~7MB to the 376MB DMG — negligible
- The `--add-data` approach means every DMG rebuild automatically includes current models