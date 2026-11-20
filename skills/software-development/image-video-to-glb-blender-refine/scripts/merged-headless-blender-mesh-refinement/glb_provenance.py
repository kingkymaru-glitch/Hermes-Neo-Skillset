#!/usr/bin/env python3
"""
glb_provenance.py — report what actually produced a .glb, and what survived.

Reads the glTF JSON chunk and prints the `asset.generator` string plus the
primitive attribute sets. Decisive for "was this Blender or a reconstruction?"
and for confirming COLOR_0 / TEXCOORD_0 were not silently dropped on export.

  python3 glb_provenance.py model.glb [more.glb ...]

GOTCHA: glTF chunks are already 4-byte aligned, so advancing the cursor is
exactly `off += 8 + chunk_length`. Applying a SECOND padding adjustment makes the
next chunk header misalign and json.loads raises
`Extra data: line 1 column N` — a parser bug that looks like a corrupt file.
"""
import json
import os
import struct
import sys

KNOWN = {
    "Khronos glTF Blender I/O": "Blender exported it",
    "draco_decoder": "re-encoded by a Draco / glTF optimiser",
    "meshoptimizer": "re-encoded by meshoptimizer",
    "gltf-transform": "re-encoded by gltf-transform",
}


def read_json_chunk(path):
    with open(path, "rb") as fh:
        data = fh.read()
    if data[:4] != b"glTF":
        raise ValueError("not a binary glTF (missing 'glTF' magic)")
    version, total = struct.unpack("<II", data[4:12])
    off = 12
    while off + 8 <= len(data):
        clen, ctype = struct.unpack("<I4s", data[off:off + 8])
        if ctype.rstrip(b"\x00") == b"JSON":
            raw = data[off + 8:off + 8 + clen]
            return version, total, json.loads(raw.decode("utf-8", "replace").rstrip("\x00 \t\r\n"))
        off += 8 + clen          # chunks are already padded; do NOT pad again
    raise ValueError("no JSON chunk found")


def report(path):
    version, total, js = read_json_chunk(path)
    asset = js.get("asset", {})
    gen = asset.get("generator", "(none)")
    print(f"--- {path}")
    print(f"    size={os.path.getsize(path):,}B  glTF v{version}  declared={total:,}")
    print(f"    generator = {gen}")
    for key, meaning in KNOWN.items():
        if key.lower() in gen.lower():
            print(f"    -> {meaning}")
            break
    print(f"    copyright = {asset.get('copyright', '(none)')}")
    print(f"    extensionsUsed = {js.get('extensionsUsed')}")
    meshes = js.get("meshes", [])
    print(f"    meshes={len(meshes)} nodes={len(js.get('nodes', []))} "
          f"images={len(js.get('images', []))} materials={len(js.get('materials', []))}")
    if meshes:
        prim = meshes[0].get("primitives", [{}])[0]
        attrs = list(prim.get("attributes", {}).keys())
        print(f"    primitive attributes = {attrs}")
        for want in ("COLOR_0", "TEXCOORD_0", "NORMAL"):
            state = "present" if want in attrs else "MISSING"
            print(f"      {want}: {state}")
        if "COLOR_0" not in attrs:
            print("      NOTE: no COLOR_0 — the exporter dropped vertex colour. "
                  "A material must reference the colour attribute.")
    print(f"    materials = {[m.get('name') for m in js.get('materials', [])]}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(2)
    for p in sys.argv[1:]:
        try:
            report(p)
        except Exception as exc:
            print(f"--- {p}\n    ERROR {exc}")
