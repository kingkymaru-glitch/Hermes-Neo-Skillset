# GLB provenance forensics — which tool actually produced this model?

Use when you must attribute a `.glb` to its generator: MARU claims a pipeline made an
asset, an asset looks implausibly clean for photogrammetry, or you need to state which
component of the LunaV family owns an output. Settle it from the file, then from code,
then from git — never from how the asset looks.

## 1. The generator stamp (fastest, decisive)

glTF stores a JSON chunk whose `asset.generator` field names the exporting tool. Read it
with `scripts/glb_provenance.py <path|dir>`, or by hand:

```python
import json, struct

def glb_json(path):
    d = open(path, "rb").read()
    magic, ver, length = struct.unpack("<4sII", d[:12])   # b'glTF', 2, total bytes
    off = 12
    while off + 8 <= len(d):
        clen, ctype = struct.unpack("<I4s", d[off:off + 8])
        if ctype.rstrip(b"\x00") == b"JSON":
            # JSON chunks are space-padded to a 4-byte boundary — strip NULs or
            # json.loads raises "Extra data".
            return json.loads(d[off + 8:off + 8 + clen].decode("utf-8", "replace").rstrip("\x00 \t\r\n"))
        off += 8 + clen          # chunk lengths are already 4-byte aligned
    return None
```

Header layout: `magic(4) | version(4) | totalLength(4)`, then repeated
`chunkLength(4) | chunkType(4) | chunkData`. `chunkType` is `JSON` then `BIN`.

## 2. What each stamp means in this fleet

| `asset.generator` | Producer | Notes |
|---|---|---|
| `Khronos glTF Blender I/O v5.1.20` | **Blender** export | Names the Blender version that wrote it. |
| `DTwin ply_to_glb` | DTwin `tools/ply_to_glb.py` | Point-cloud preview from a splat. |
| `DTwin splat_to_mesh` | DTwin `tools/splat_to_mesh.py` | Poisson mesh from a splat. |
| `draco_decoder` | a Draco re-export | **Not evidence of Blender.** LUNASCAN's post-ODM `3d-optimize` stage rewrites the stamp; the source was OpenDroneMap. |
| absent | third-party CAD / mesh export | e.g. CAD-exported site models. |

The stamp names the *last writer*, not the reconstruction engine — a Draco or
optimiser pass erases the upstream engine's stamp. Pair it with step 3 when the
question is "which pipeline", not "which tool touched it last".

## 3. Code negative — grep for real invocation, not mentions

```bash
grep -rn -e blender -e Blender -e bpy <repo> \
  --include='*.py' --include='*.sh' --include='*.mjs' --include='*.js' \
  --include='*.ts' --include='*.tsx' \
  --exclude-dir=node_modules --exclude-dir=.git --exclude-dir=.venv \
  --exclude-dir=venv --exclude-dir=site-packages --exclude-dir=mesh-venv \
  --exclude-dir=dist --exclude-dir=build --exclude-dir=.next --exclude='*.map'
```

Only two hit shapes prove a Blender pipeline: **`import bpy`** and an **exec of the
Blender binary** (`subprocess` / `execFileAsync` against `.../Blender`). Docstrings,
markdown, and UI labels that merely name Blender (viewer instructions, "Build detailed
(Blender)") are not invocation. Always exclude the virtualenv/site-packages dirs —
`fontTools` (`self.blender`), `open3d`, and `matplotlib` binaries all contain the
token and produce false positives that look like real hits.

Home-wide `grep -r` / `find` over `~/` is too slow to finish (minutes) — scope to the
specific repos, and search protected folders (`Desktop`, `Documents`, `Downloads`) by
naming them explicitly; broad searches skip them silently.

## 4. Git negative — did this pipeline EVER use it

```bash
git -C <repo> log --all -S'blender' --oneline     # empty across all history = durable negative
git -C <repo> log --oneline --all | head -30       # read the real pipeline evolution
```

A commit subject like `refactor: dissect dead code — drop legacy sfm/export/storage`
means the earlier engine was **removed**, so an old architecture doc describing it is
stale. Read the subjects; they document which engine was tried and abandoned.

## 5. Reporting shape

State, per artifact: the generator stamp, the code path that produced it, and whether
Blender is in that path. When a model is unusually clean, attribute it to the *builder*
class (procedural, from coordinates or OSM) rather than a reconstruction pipeline —
procedural geometry is clean by construction, so "too perfect for photogrammetry" is
evidence of a builder, not evidence of a hidden Blender stage in the video pipeline.
