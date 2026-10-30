#!/usr/bin/env python3
"""Verify LUNASCAN Batch 5 glb optimizer wiring (re-runnable, no real ODM needed).

Checks:
  1. Node.js is on PATH (optimizer runtime prerequisite).
  2. tools/3d-optimize/optimize.mjs exists.
  3. draco3d + @gltf-transform are installed in that folder's node_modules.
  4. lunascan/optimize.py imports and optimize_glb is callable.

Does NOT run a full optimization (needs a real ODM glb). Use the 701 fixture at
~/Desktop/DJI/701/lunascan_output/site_model.glb to smoke-test the real shrink.
"""
import shutil
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent.parent  # skills/../.. -> repo root guess
# Resolve repo root from this file: skills/<cat>/<skill>/scripts -> 4 up
SKILL_ROOT = Path(__file__).resolve().parent.parent
REPO_ROOT = SKILL_ROOT.parents[2]  # skills/software-development/lunascan-development -> up 3? adjust:
# Structure: ~/.hermes/skills/software-development/lunascan-development/scripts
#   parents[0]=scripts, [1]=lunascan-development, [2]=software-development, [3]=skills, [4]=hermes
REPO_GUESS = REPO_ROOT  # fallback

ok = True


def check(label, cond):
    global ok
    print(f"[{'PASS' if cond else 'FAIL'}] {label}")
    if not cond:
        ok = False


node = shutil.which("node")
check("node on PATH", bool(node))

opt = REPO_GUESS / "tools" / "3d-optimize" / "optimize.mjs"
check("tools/3d-optimize/optimize.mjs present", opt.is_file())

if opt.is_file():
    nm = opt.parent / "node_modules"
    check("node_modules present", nm.is_dir())
    check("draco3d installed", (nm / "draco3d").is_dir())
    check("gltf-transform installed", (nm / "@gltf-transform").is_dir())

# Python side import
sys.path.insert(0, str(REPO_GUESS))
try:
    from lunascan.optimize import optimize_glb  # noqa: F401
    check("lunascan.optimize.optimize_glb importable", True)
except Exception as e:  # pragma: no cover
    check(f"lunascan.optimize import ({e})", False)

if not ok:
    print("\nBatch 5 optimizer wiring INCOMPLETE — see references/glb-web-optimization.md")
    sys.exit(1)
print("\nBatch 5 optimizer wiring OK")
sys.exit(0)
