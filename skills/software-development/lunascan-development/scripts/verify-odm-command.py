#!/usr/bin/env python3
"""Verify lunascan.odm.build_docker_command emits a correct OpenDroneMap
invocation (the non-obvious shape that actually works on DJI drone footage).

Run from the LUNASCAN repo root:
    .venv/bin/python /path/to/scripts/verify-odm-command.py

Asserts (fast default, geo_anchored=False):
  - positional dataset name `code` (NOT --images, which this ODM version rejects)
  - --orthophoto-resolution 20  (avoids meshing DEM renderdem --max-tiles 165 overflow)
  - --end-with mvs_texturing    (skip orthophoto/DEM; --gltf still emits .glb)
  - --gltf present
  - --mesh-octree-depth present (drives mesh quality, independent of orthophoto res)
  - --matcher-order 8          (FAST: non-georef sequential matching, ~6.4K pairs.
                               ODM ignores --matcher-order on georeferenced data, so
                               fast mode SKIPS GPS geotag to make this engage.)
  - opendronemap/odm:3.6.1     (pinned; :latest is now 3.12.3 which explodes to 300K+)
  - --matcher-neighbors ABSENT in fast mode (it is the slow GPS-KNN path)
Also asserts geo mode (geo_anchored=True) uses --matcher-neighbors 8.
"""
import re
import sys
from pathlib import Path

# import from repo root (skill lives under .hermes; repo is elsewhere)
REPO = Path(__file__).resolve()
for cand in (REPO.parents[3], REPO.parents[4]):
    if (cand / "lunascan" / "odm.py").exists():
        sys.path.insert(0, str(cand))
        break
else:
    sys.path.insert(0, ".")
from lunascan.odm import build_docker_command  # noqa: E402


def real_flags(cmd):
    """Extract the real flag tokens (strings starting with --) from a command list.

    NOTE: do NOT just do substring `in cmd_str` — the explanatory comments in
    odm.py mention flag names by string, so a naive check passes even after the
    flag is removed. Parse the actual tokens.
    """
    return set(re.findall(r"-{2}[\w-]+", " ".join(cmd)))


def main() -> int:
    # --- FAST mode (default) ---
    cmd = build_docker_command(Path("/tmp/lunascan_odm"), fast=True, geo_anchored=False)
    cmd_str = " ".join(cmd)
    flags = real_flags(cmd)

    checks = {
        "positional 'code' dataset name": "code" in cmd,
        "no '--images' flag (rejected by ODM)": "--images" not in cmd,
        "--orthophoto-resolution 20": "--orthophoto-resolution" in cmd and "20" in cmd,
        "--end-with mvs_texturing": "--end-with" in cmd and "mvs_texturing" in cmd,
        "--gltf present": "--gltf" in cmd,
        "--mesh-octree-depth present": "--mesh-octree-depth" in cmd,
        "--matcher-order 8 (fast sequential)": "--matcher-order" in flags,
        "--matcher-neighbors ABSENT in fast mode (slow GPS-KNN)":
            "--matcher-neighbors" not in flags,
        "ODM pinned to 3.6.1 (NOT :latest=3.12.3 blowup)":
            "opendronemap/odm:3.6.1" in cmd_str,
        "mounts project dir to /datasets": any("/datasets" in str(c) for c in cmd),
        "uses opendronemap/odm image": any("opendronemap/odm" in str(c) for c in cmd),
    }

    ok = True
    for label, passed in checks.items():
        print(f"  [{'PASS' if passed else 'FAIL'}] {label}")
        ok = ok and passed

    if "--matcher-order" in flags:
        i = cmd.index("--matcher-order")
        val = cmd[i + 1]
        good = val == "8"
        print(f"  [{'PASS' if good else 'FAIL'}] --matcher-order value == 8 (got {val})")
        ok = ok and good

    # --- GEO mode (geo_anchored=True) ---
    print("\n--- geo-anchored mode ---")
    cmd_g = build_docker_command(Path("/tmp/lunascan_odm"), fast=True, geo_anchored=True)
    flags_g = real_flags(cmd_g)
    gchecks = {
        "--matcher-neighbors 8 (geo GPS-KNN)": "--matcher-neighbors" in flags_g,
        "--matcher-order ABSENT in geo mode": "--matcher-order" not in flags_g,
    }
    for label, passed in gchecks.items():
        print(f"  [{'PASS' if passed else 'FAIL'}] {label}")
        ok = ok and passed
    if "--matcher-neighbors" in flags_g:
        i = cmd_g.index("--matcher-neighbors")
        good = cmd_g[i + 1] == "8"
        print(f"  [{'PASS' if good else 'FAIL'}] geo --matcher-neighbors value == 8")
        ok = ok and good

    print(f"\nFast command: {cmd_str}")
    print(f"\nRESULT: {'ALL PASS' if ok else 'FAILURES PRESENT'}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
