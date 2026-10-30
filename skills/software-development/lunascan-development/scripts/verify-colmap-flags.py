#!/usr/bin/env python3
"""Verify COLMAP 4.x flags in pipeline.py match the installed binary."""
import subprocess, sys, os
from pathlib import Path

colmap_bin = os.environ.get("COLMAP_BIN", "/opt/homebrew/bin/colmap")
src = Path(os.environ.get(
    "LUNASCAN_REPO",
    os.path.expanduser("~/Documents/LUNASCAN"),
)) / "lunascan" / "sfm" / "pipeline.py"

if not src.exists():
    print(f"SKIP: pipeline.py not found at {src}")
    sys.exit(0)

pipeline_text = src.read_text()

# --- Source code checks ---
stale_checks = {
    "--SiftMatching.use_gpu": "--FeatureMatching.use_gpu",
    "--SiftMatching.gpu_index": "--FeatureMatching.gpu_index",
    "ba_global_images_ratio": "ba_global_frames_ratio",
}
ok = True
for stale, new in stale_checks.items():
    if stale in pipeline_text:
        print(f"FAIL: pipeline.py still has stale flag '{stale}' (should be '{new}')")
        ok = False
    else:
        print(f"OK: no stale '{stale}' in pipeline.py")

# --- Binary checks ---
flag_checks = [
    ("FeatureMatching.use_gpu", "exhaustive_matcher"),
    ("FeatureMatching.gpu_index", "exhaustive_matcher"),
    ("ba_global_frames_ratio", "mapper"),
]
for flag, section in flag_checks:
    r = subprocess.run(
        [colmap_bin, section, "--help"],
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, timeout=5,
    )
    if flag in (r.stdout or ""):
        print(f"OK: --{flag} exists in colmap {section}")
    else:
        print(f"FAIL: --{flag} NOT found in colmap {section}")
        ok = False

if not ok:
    sys.exit(1)
print("\nALL COLMAP flags verified")