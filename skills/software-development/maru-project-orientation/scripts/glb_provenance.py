#!/usr/bin/env python3
"""glb_provenance.py — print the generator stamp and structure of .glb files.

WHY: attributing a model to the tool that made it must come from the file, not from
how the asset looks. glTF records the exporting tool in asset.generator; this reads it
plus enough structure (meshes/nodes/materials/images) to tell a procedural build from
an optimised reconstruction export.

USAGE
  python3 glb_provenance.py <file-or-dir> [<file-or-dir> ...]

Directories are walked for *.glb (skipping node_modules/.git/.venv/site-packages).
Exit code is 0 even for unparseable files — it prints the reason per file instead.
"""

from __future__ import annotations

import json
import os
import struct
import sys

SKIP_DIRS = {
    "node_modules", ".git", ".venv", "venv", "site-packages", "dist",
    "build", ".next", ".vercel", "mesh-venv", "__pycache__",
}


def glb_json(path: str) -> dict:
    """Return the JSON chunk of a .glb, or raise ValueError with the reason."""
    with open(path, "rb") as fh:
        data = fh.read()
    if len(data) < 12:
        raise ValueError("file shorter than a glTF header")
    magic, version, length = struct.unpack("<4sII", data[:12])
    if magic != b"glTF":
        raise ValueError(f"not a binary glTF (magic={magic!r})")
    off = 12
    while off + 8 <= len(data):
        clen, ctype = struct.unpack("<I4s", data[off:off + 8])
        if ctype.rstrip(b"\x00") == b"JSON":
            chunk = data[off + 8:off + 8 + clen]
            # JSON chunks are space-padded to a 4-byte boundary; trailing NULs make
            # json.loads raise "Extra data".
            text = chunk.decode("utf-8", "replace").rstrip("\x00 \t\r\n")
            return json.loads(text)
        off += 8 + clen  # chunk lengths are already 4-byte aligned
    raise ValueError("no JSON chunk found")


def walk(target: str) -> list[str]:
    if os.path.isfile(target):
        return [target]
    found = []
    for root, dirs, files in os.walk(target):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        found.extend(os.path.join(root, f) for f in files if f.lower().endswith(".glb"))
    return sorted(found)


def report(path: str) -> None:
    print(f"--- {path}")
    try:
        doc = glb_json(path)
    except Exception as exc:  # noqa: BLE001 - report, never crash the sweep
        print(f"    UNREADABLE: {exc}")
        return
    asset = doc.get("asset", {}) or {}
    print(f"    size          = {os.path.getsize(path):,} B")
    print(f"    generator     = {asset.get('generator', '(none)')}")
    print(f"    version       = {asset.get('version', '(none)')}")
    print(f"    extensions    = {doc.get('extensionsUsed')}")
    print(
        "    counts        = "
        f"meshes={len(doc.get('meshes', []))} "
        f"nodes={len(doc.get('nodes', []))} "
        f"materials={len(doc.get('materials', []))} "
        f"images={len(doc.get('images', []))}"
    )
    names = [n.get("name") for n in doc.get("nodes", [])][:10]
    if any(names):
        print(f"    first nodes   = {names}")


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print(__doc__)
        return 2
    for target in argv[1:]:
        if not os.path.exists(target):
            print(f"--- {target}\n    MISSING")
            continue
        for path in walk(target):
            report(path)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
