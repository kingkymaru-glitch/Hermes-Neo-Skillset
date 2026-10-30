---
name: headless-blender-mesh-refinement
description: "Use when a raw mesh/splat must become a clean GLB."
---

# Headless Blender Mesh Refinement

Turning a raw reconstruction (photogrammetry mesh, splat-derived mesh, CAD
import, scan) into a clean, web-ready `.glb` — using Blender in `--background`
mode as a pure post-processing stage. Blender never reconstructs.

## When to use
- Any "images/video → 3D model" ask where the user expects a clean `.glb`.
- A raw reconstruction exists and needs decimation, UVs, vertex colour, a
  normalised transform, or a single-file export.
- A model "loads but looks wrong" and you need to establish what produced it.

Composes with the reconstruction half: `dtwin-pipeline-hardening` and
`gaussian-splatting-pipeline` cover ffmpeg→COLMAP→3DGS. This skill is the stage
AFTER those.

## THE RULE: Blender refines, it never reconstructs
Blender has **no photogrammetry / SfM / MVS engine**. There is no
"images → Blender → model". If a user asks for that, say so plainly and give them
the real shape:

```
CAPTURE  ->  RECONSTRUCT   ->  BLENDER REFINE  ->  GLB
(user)      (COLMAP/ODM/3DGS)  (this skill)       (output)
```

Never let a request be built on the assumption that Blender generates geometry.
The refine pass is still what makes a model look "CAD-perfect" — raw
photogrammetry is 500k–5M noisy triangles and Blender turns it into a clean 50k
mesh with sane UVs and a normalised transform — but the geometry itself must come
from a reconstruction engine.

## The refine stages
1. **Import** the mesh (PLY / OBJ / GLB). Join multiple objects into one so the
   downstream maths is unambiguous.
2. **Capture the vertex-colour attribute name** *before* any modifier runs —
   decimate/remesh can drop or rename it.
3. **Clean** — merge doubles, delete loose, dissolve degenerate.
4. **Remesh** (optional, `REMESH` modifier, VOXEL mode) — for splat-derived soup
   where you want uniform topology. Costs detail.
5. **Decimate** — `DECIMATE` modifier, `decimate_type='COLLAPSE'`.
6. **Shade** — `shade_smooth()` + `WEIGHTED_NORMAL` (wrap in try/except; not fatal
   if it fails).
7. **UV unwrap** — `bpy.ops.uv.smart_project()` in edit mode.
8. **Material** — see the vertex-colour pitfall below. Non-optional.
9. **Normalise** — centre on origin, drop to Z=0, apply a scale factor from a
   declared real measurement.
10. **Export** — `bpy.ops.export_scene.gltf(export_format="GLB")`, then verify the
    file exists and is non-empty.

Runnable implementation: `scripts/blender_refine.py`.

## Invocation
```bash
"/Applications/Blender.app/Contents/MacOS/Blender" \
  --background --python-exit-code 1 \
  --python scripts/blender_refine.py -- \
  --in mesh.ply --out out.glb --target-tris 60000 --scale-longest-mm 0
```
`--python-exit-code 1` is **mandatory**, not cosmetic — see pitfalls. Blender
passes its own argv, so everything after `--` is yours.

## Pitfalls

### Blender exits 0 even when its Python script raises
Without `--python-exit-code 1` a failed run reports success. The caller then reads
a file that was never written and surfaces a misleading "file not found" instead
of the real error. The same trap bit the CDM surroundings worker. Always pass the
flag, and still verify the output file exists and is non-zero.

### A vertex colour attribute is dropped unless a material references it
glTF only exports `COLOR_0` when a material actually reads the attribute. Without
this the colour silently disappears and the model ships grey. Build a material
with a `ShaderNodeAttribute` (attribute_name = the captured colour attribute)
feeding the Principled BSDF `Base Color`. Verify by reading the primitive's
attribute list back out of the exported file.

### Decimate ratio above 1.0 is silently ignored
`DECIMATE` ratio must be in `(0, 1]`. A ratio > 1 is not an error — Blender just
skips it, leaving a huge mesh that looks fine in the log. Clamp with
`ratio = max(0.01, min(1.0, target_tris / tris_now))` and count triangles as
`sum(len(p.vertices) - 2 for p in polygons)` so quads from a voxel remesh are
counted doubled.

### Poisson on a whole-scene splat produces a blob
Surface extraction welds *everything* in the cloud into one surface, including
ground, background and sky floaters. A scene capture then meshes into a shapeless
column instead of the subject. Isolate the subject first — see
`references/mesh-from-splat.md`. A bounding-box crop is usually the WRONG tool:
path-based captures (a drone flying a route) produce a long strip cloud where any
box containing the subject also contains a large slice of the surroundings. Use
density clustering (DBSCAN, keep the largest connected blob).

### A reconstruction has no absolute scale
COLMAP and 3DGS are both metrically correct only up to an unknown factor. Without
a declared reference the model is unitless and **no measurement may be taken from
it**. Record scale provenance explicitly (method, the declared value, and a
`measurable: true/false` flag) rather than implying precision that does not
exist. This matters for a liability-averse user: an unmeasurable model presented
as measurable is a fabricated capability.

### The declared measurement must be the object's LONGEST extent
Scaling by "longest bounding-box axis" is the cheapest reference (one number, no
UI). It is only valid if the user measured the object's longest dimension — a
measurement of some smaller feature scales the whole model wrongly. Label the
input field accordingly. Two-point picking (click two points, type the distance)
is the honest upgrade. Clean floaters BEFORE taking the bounding box, or one stray
point throws the scale.

### Blender 5.x deprecation noise
`mat.use_nodes = True` and `world.use_nodes = True` emit
`DeprecationWarning: ... expected to be removed in Blender 6.0`. Harmless; do not
let it read as failure.

## Verify — two independent checks
A model that loads without error can still be garbage (inside-out, exploded,
blank).

1. **Provenance.** Read the glTF `asset.generator` string straight out of the
   GLB's JSON chunk. This is decisive evidence of what actually produced a file
   and settles "was this Blender, or was this a reconstruction?" without guessing
   from appearance.
   - `Khronos glTF Blender I/O vX.Y.Z` → Blender exported it
   - `draco_decoder` → re-encoded by a Draco/meshopt optimiser
   - a custom name → a bespoke writer
   Run `scripts/glb_provenance.py <file.glb>`; it also prints the primitive
   attributes so you can confirm `COLOR_0` / `TEXCOORD_0` survived.
2. **Render it.** Load the `.glb` in headless Blender from 2–3 fixed angles and
   actually look at the output. This is how you catch a mesh that is technically
   valid and visually wrong.

## Interpreting a poor result honestly
When the refined mesh looks wrong, decide which half failed before changing
anything:
- **Splat/scene itself wrong** → the capture, not the refine. Check the trainer's
  `progress_*.png` renders: if the splat render is recognizable, the
  reconstruction is fine and the fault is downstream.
- **Splat fine, mesh a blob** → subject isolation, see the Poisson pitfall.
- **Mesh fine, looks low-poly/blocky** → an under-converged splat. Gaussians that
  have not shrunk to fine detail mesh into voxel-looking blocks. Check the
  iteration count and PSNR before touching the refine settings.

## Capture discipline (a pipeline cannot fix this)
An object needs an **orbit** of the subject (~60–80% frame overlap). A wide
flythrough of a landscape is the hardest possible input for object extraction:
the subject is one feature in a much larger scene, with ground and background
competing for the reconstruction. Tell the user this up front rather than
delivering a disappointing model and blaming the code. Subjects that are shiny,
transparent, or textureless fail feature matching outright — a physics limit, not
a tuning problem.

## Files
- `scripts/blender_refine.py` — the refine stage (run directly).
- `scripts/glb_provenance.py` — read generator + attributes from a `.glb`.
- `references/mesh-from-splat.md` — splat→mesh recipe, cluster isolation.
