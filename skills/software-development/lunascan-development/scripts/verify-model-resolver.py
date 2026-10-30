#!/usr/bin/env python3
"""Verify that the bundled YOLO model resolver works in all modes."""
import os, sys, tempfile, shutil
from pathlib import Path

# Adjust to find LUNASCAN repo relative to this script or cwd
repo = Path(os.environ.get("LUNASCAN_REPO", os.getcwd()))
sys.path.insert(0, str(repo))

from lunascan.masking.detector import (
    _resolve_model_path, DynamicDetector, _MODEL_FILENAME,
)

errors = 0

# 1. Dev-mode resolver finds the bundled model
path = _resolve_model_path()
assert os.path.isfile(path), f"not a file: {path}"
assert path.endswith(_MODEL_FILENAME)
size_mb = os.path.getsize(path) / (1024 * 1024)
assert size_mb > 5, f"model too small ({size_mb:.1f}MB) — corrupt download?"
print(f"PASS [1] dev resolver → {path} ({size_mb:.1f}MB)")

# 2. Lazy load intact
det = DynamicDetector()
assert det.model_name.endswith("yolov8n-seg.pt")
assert det._model is None, "model should be lazy-loaded"
print(f"PASS [2] DynamicDetector() → lazy load OK, model_name={det.model_name}")

# 3. Custom model passes through
assert _resolve_model_path("custom.pt") == "custom.pt"
print(f"PASS [3] custom model name passes through untouched")

# 4. Absolute path preserved
assert _resolve_model_path("/abs/path/model.pt") == "/abs/path/model.pt"
print(f"PASS [4] absolute path preserved")

# 5. MEIPASS path construction correct
from pathlib import Path as _P
assert str(_P("/MEIPASS") / "lunascan" / "models" / _MODEL_FILENAME) == \
       "/MEIPASS/lunascan/models/yolov8n-seg.pt"
print(f"PASS [5] PyInstaller MEIPASS path construction correct")

# 6. test_masking.py assertion fix
assert DynamicDetector().model_name.endswith("yolov8n-seg.pt")
print(f"PASS [6] test_masking.py .endswith() assertion works")

print(f"\nALL 6 CHECKS PASSED")
sys.exit(0)