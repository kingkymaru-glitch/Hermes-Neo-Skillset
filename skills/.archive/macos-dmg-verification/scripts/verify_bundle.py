#!/usr/bin/env python3
"""Parametric verifier for a PyInstaller-built macOS .dmg.

Mounts the dmg read-only, asserts EXACT-DIR absence of a module list,
asserts PRESENCE of marker strings in bundled files, AST-parses key files,
detaches, exits non-zero on any failure.

Edit MODULES_ABSENT / MARKERS_PRESENT per project, then run:
    python verify_bundle.py /path/to/dist/APP.dmg
"""
import ast
import subprocess
import sys
import tempfile
from pathlib import Path

# --- EDIT THESE ---------------------------------------------------------
APP_NAME = "LUNASCAN"          # volume + .app name
PKG = "lunascan"               # top-level python package dir in Resources
# Exact dirs that MUST NOT exist in the bundle (dead modules):
MODULES_ABSENT = ["sfm", "export", "storage"]
# (file_in_bundle, substring_that_must_be_present):
MARKERS_PRESENT = [
    ("lunascan/pipeline.py", "from lunascan.odm import run_odm"),
    ("lunascan/pipeline.py", "0.95"),
    ("lunascan/odm.py", "matcher-order"),
    ("lunascan/odm.py", "WITHOUT GPS"),
]
FILES_AST_PARSE = [
    "lunascan/pipeline.py",
    "lunascan/odm.py",
    "lunascan/optimize.py",
]
# -----------------------------------------------------------------------

def main(dmg: Path) -> int:
    if not dmg.is_file():
        print(f"DMG not found: {dmg}")
        return 2
    with tempfile.TemporaryDirectory() as tmp:
        # attach
        r = subprocess.run(
            ["hdiutil", "attach", str(dmg), "-nobrowse", "-quiet",
             "-mountpoint", f"{tmp}/mnt"],
            capture_output=True, text=True)
        if r.returncode != 0:
            print("hdiutil attach failed:\n", r.stderr)
            return 3
        mnt = Path(f"{tmp}/mnt")
        res = mnt / f"{APP_NAME}.app" / "Contents" / "Resources"
        fails = []
        # 1. absent modules (exact dir check — no substring globs!)
        for m in MODULES_ABSENT:
            if (res / PKG / m).exists():
                fails.append(f"DEAD MODULE STILL PRESENT: {PKG}/{m}")
        # 2. markers present
        for rel, marker in MARKERS_PRESENT:
            f = res / rel
            if not f.is_file() or marker not in f.read_text():
                fails.append(f"MARKER MISSING: {rel} <- '{marker}'")
        # 3. AST parse
        for rel in FILES_AST_PARSE:
            f = res / rel
            if f.is_file():
                try:
                    ast.parse(f.read_text())
                except SyntaxError as e:
                    fails.append(f"SYNTAX ERROR: {rel}: {e}")
            else:
                fails.append(f"FILE MISSING: {rel}")
        # detach
        subprocess.run(["hdiutil", "detach", str(mnt), "-quiet"],
                       capture_output=True, text=True)
        if fails:
            print("VERIFY FAILED:")
            for f in fails:
                print("  -", f)
            return 1
        print("VERIFY PASS: bundle contains intended source (dead gone, fixes in)")
        return 0

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("usage: verify_bundle.py <path-to.dmg>")
        sys.exit(2)
    sys.exit(main(Path(sys.argv[1])))
