#!/usr/bin/env python3
"""Validate a DTwin-generated .glb for the defects that break three.js GLTFLoader.

Checks (each is a known failure mode seen in production on 2026-08-16):
  1. GLB container: magic 'glTF', version 2, declared length == file size.
  2. JSON chunk pad byte: GLB spec requires the JSON chunk padded with 0x20
     (space) to the 4-byte boundary. A null (0x00) pad makes GLTFLoader throw
     "Unexpected non-whitespace character after JSON at position N".
  3. bufferView.target: for a POINTS cloud with only POSITION + COLOR_0 there
     must be NO index bufferView. target=34963 (ELEMENT_ARRAY_BUFFER) on the
     color/position view is invalid and rejects the asset.
  4. JSON.parse: the JSON chunk (minus padding) must be valid JSON.

Usage: glb_validate.py <file.glb>   -> exits 0 if OK, 1 if any check fails.
"""
import json, struct, sys

ELEMENT_ARRAY_BUFFER = 34963
ARRAY_BUFFER = 34962


def main():
    if len(sys.argv) != 2:
        print("usage: glb_validate.py <file.glb>")
        sys.exit(2)
    path = sys.argv[1]
    try:
        data = open(path, "rb").read()
    except OSError as e:
        print(f"FAIL: cannot read {path}: {e}")
        sys.exit(1)

    errors = []
    # 1. container
    if len(data) < 12:
        print("FAIL: file too small")
        sys.exit(1)
    magic, ver, length = struct.unpack("<4sII", data[:12])
    if magic != b"glTF":
        errors.append("bad magic (not glTF)")
    if ver != 2:
        errors.append(f"unsupported version {ver}")
    if length != len(data):
        errors.append(f"declared length {length} != file {len(data)}")

    # 2+3+4: JSON chunk
    json_len = struct.unpack("<I", data[12:16])[0]
    json_type = data[16:20]
    json_chunk = data[20:20 + json_len]
    if json_type != b"JSON":
        errors.append(f"chunk0 type is {json_type!r}, expected JSON")
    if json_chunk[-1:] == b"\x00":
        errors.append("JSON chunk padded with 0x00 (null) instead of 0x20 (space) — GLTFLoader will throw")
    elif json_chunk[-1:] != b" ":
        errors.append(f"JSON chunk last byte is {json_chunk[-1:]!r}, expected 0x20 space")
    stripped = json_chunk.rstrip(b" \x00")
    try:
        gltf = json.loads(stripped.decode("utf-8"))
    except Exception as e:
        errors.append(f"JSON chunk does not parse: {e}")
        gltf = {}
    for i, bv in enumerate(gltf.get("bufferViews", [])):
        t = bv.get("target")
        if t == ELEMENT_ARRAY_BUFFER:
            errors.append(f"bufferView {i} has target=34963 (ELEMENT_ARRAY_BUFFER) — invalid for POINTS cloud")
        elif t not in (ARRAY_BUFFER, None):
            errors.append(f"bufferView {i} has unexpected target={t}")

    if errors:
        print(f"FAIL: {path}")
        for e in errors:
            print("  -", e)
        sys.exit(1)
    print(f"PASS: {path} ({len(data)} bytes, {json_len}-byte JSON chunk, space-padded, no index bufferView)")
    sys.exit(0)


if __name__ == "__main__":
    main()
