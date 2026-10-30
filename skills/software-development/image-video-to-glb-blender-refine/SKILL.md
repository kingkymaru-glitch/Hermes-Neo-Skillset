---
name: image-video-to-glb-blender-refine
description: Use when photos or video must become a .glb 3D model.
---

# Images/video -> .glb 3D model

## Choose the direction FIRST — this is the decision that matters

There are two opposite architectures. Picking wrong wastes hours.

| | BOTTOM-UP (photogrammetry) | TOP-DOWN (parametric) |
|---|---|---|
| path | frames -> COLMAP -> 3DGS -> Poisson -> Blender | frames -> AI spec -> codegen -> headless Blender |
| time | tens of minutes to hours | **seconds** |
| output | noisy real surface | clean editable model |
| geometry | measured (up to scale) | inferred / invented |
| editable | no | yes, parametric |
| use for | survey, measurement, as-found record | visual asset, AR, twin, demo |

**Default to TOP-DOWN** unless the user explicitly needs measured geometry. A user
who says the output "looks too perfect" or complains it "takes forever" is asking
for top-down; do not keep tuning the photogrammetry. Photogrammetry is the right
answer only when the number matters more than the look.

---

# TOP-DOWN: AI spec -> parametric script -> headless Blender

The AI's job is producing a **spec**, not a script. Everything after the spec is
deterministic codegen, so the same spec always yields the same model.

```
1 INGEST    sample 6-12 frames spread across the clip
2 ANALYSE   vision model reads them -> structural inventory
            (object type, element list, counts, proportions, colours)
3 SPEC      normalised JSON {object, materials[], parts[{op,...}], provenance}
4 CODEGEN   spec -> parametric Blender Python  (deterministic)
5 BUILD     blender --background --python-exit-code 1 --python <script>   (seconds)
6 VERIFY    render the .glb from fixed angles and look at it
```

Design rules that make this work:

- **Spec is data, not prose.** One entry per element with an `op` discriminator
  (`disc`, `box`, `column_grid`, `hip_roof`, `solar_panel`, `railing_ring`, ...).
  Generalise by adding ops, not by free-form codegen.
- **Use several views.** A single frame cannot tell you a roof is hipped, how many
  columns there are, or what is hidden behind the front. Sample across the clip.
- **Emit `provenance` into the spec and stamp it into the .blend + GLB**
  (`scene["lunascan_measurable"]`). A model whose geometry was inferred must never
  be presentable as measured. Carry `measurable: false` unless real dimensions
  were supplied.
- **Recovering an old .blend's builder:** Blender stores Python as **Text
  datablocks** inside the .blend. `bpy.data.texts` after `wm.open_mainfile` often
  hands you the exact script that made the model — check there before rewriting
  something from scratch.
- **Pass the GLB path explicitly to codegen.** Deriving it from the script path
  silently produces `name_build.py.glb`.
- **Helper vocabulary that covers most structures:** `mat()`, `cube()`,
  `frustum()` (4-sided cone, rotated 45deg, for tapered columns), `cyl_between()`
  (rails, ridges, fan infill), and a mesh-from-pydata `roof_face()` for tiled
  slopes with sinusoidal relief.
- **Verify by rendering.** `BUILD_OK` only proves Blender ran.

## Tolerating model output (the part that decides whether it works at all)

A vision model produces a spec that is 95% right and then fails on one detail.
Every one of these was hit by a real run, in this order, each costing a full
inference to discover. Repair them in a NORMALISATION LAYER, not by editing the
prompt and hoping:

1. **Missing commas between array elements.** The dominant defect. The reply is
   unparseable but otherwise perfect. Repair narrowly: insert a comma only where
   a value is followed by a newline and then the next key/element, and drop
   trailing commas. Require the newline so it cannot fire inside a string.
2. **Material referenced but never defined.** A part names `RidgeRed` and the
   materials list omits it. Synthesise it with a colour guessed from the name.
3. **Optional sub-block omitted.** `hip_roof` with no `apex_cap`, railings with no
   `post`. Keep all defaults in ONE table keyed by op, deep-merged into each part,
   so emitters never need `.get()` and codegen can trust the schema.
4. **Palette entries that are not defined materials.** `stone_palette: [Stone0,
   Stone1]` with neither defined — the generated script dies on an undefined name.
   One level up from defect 2; fix both.
5. **A block written in the WRONG SHAPE.** The prompt shows column-style blocks
   (`size_top`/`size_bot`/`height`), so the model reuses that shape for a railing
   post's `base`/`cap`. Coerce it to `[x,y,z]`. Related: a sibling block nested
   one level too deep (`rails` inside `post`), and a field filled with `0` rather
   than omitted (`cap_z: 0` puts the cap on the ground).

Rules that make this work:

- **Never reject a near-valid spec.** The user should not hand-edit JSON to see a
  first result. Repair, then record every change in `provenance.auto_repairs` and
  surface it as a warning.

## Check what the model SAW against what it EMITTED

Ask the model to report its observations (`observed: {roof_form, columns,
platform, railing, fixtures}`) as well as the parts, then compare the two. This
separates two failure modes that look identical in the output:

- a model that **saw nothing** — poor reading, re-running is wasted effort
- a model that **saw everything and emitted one part** — poor emission, and
  re-running or switching to a stronger provider genuinely fixes it

Real case: `observed` correctly listed a roof, columns, a platform, a railing and
a solar panel; `parts` contained only the roof. Chamfer 0.10 with no explanation.
The same prompt and video produced 6 parts on an earlier run — local small VLMs
are inconsistent this way, so never judge one run.

Report the gaps as warnings and let the reviewer decide. Do NOT synthesise the
missing parts: what the geometry should be is a judgement call, and inventing it
silently makes the review step a formality.
- **Repair only ADDS or coerces. It never renames, reorders or drops.** Those are
  the reviewer's judgement calls, and silently making them turns the review step
  into a lie.
- **Order matters:** normalise shapes → fill defaults → resolve materials.
- **Test repair against the real broken payload.** Save the actual malformed
  model output as a fixture; re-running inference to check a regex costs minutes.

## Downloading model weights (the other thing that decides whether it works)

- **Never run two downloads concurrently.** HuggingFace writes each shard to its
  own temp blob, so parallel fetches of the same file produce two `.incomplete`
  blobs racing to rename one target. This wastes the whole transfer and leaves the
  cache inconsistent. Assert single-flight.
- **Retry with resume.** A large fetch over a home connection WILL drop. One-shot
  download fails the entire setup after ten minutes of progress.
- **A `.incomplete` blob means not ready.** HuggingFace creates the cache dir the
  moment a download starts, and can leave a valid-looking snapshot symlink
  pointing at a stub. Require total weight bytes above a floor AND no
  `.incomplete` present, or the app reports "ready" and then fails at inference.
- **`du` lies about the cache size** when blobs are xet-backed symlinks. Resolve
  the symlink (`ls -lL`) before concluding a download is missing.
- If the metadata host resolves but the weights host does not, check the primary
  resolver — a Tailscale MagicDNS resolver (`100.100.100.100`) can fail a CDN
  host that the wider internet serves fine.

## Embedded viewer gotchas

- **GLTFLoader cannot fetch across `file://` origins.** Serve the viewer and the
  model over a loopback HTTP server on a free port, with a route per file, rather
  than copying the model next to the HTML.
- **QtWebEngine offscreen has no WebGL2.** Testing needs ANGLE + SwiftShader, and
  `--disable-gpu-sandbox` is what stops the context being lost mid-run. Without it
  a run fails and then passes unchanged. Require three consecutive green runs.
- **A build is not verified by an exit code.** Assert on the viewer's own reported
  status (mesh and triangle counts) after loading.

---

# BOTTOM-UP: photogrammetry (only when measurement is the point)

## The rule that governs the whole design

**Blender cannot reconstruct geometry from photographs.** It has no SfM/photogrammetry
engine. Any request shaped like "photos -> Blender -> model" is based on a false premise,
and agreeing with it wastes a build. The only honest architecture is:

```
CAPTURE -> RECONSTRUCT (engine) -> BLENDER REFINE -> .glb
```

Blender's real contribution is what makes the output look CAD-clean rather than like
photogrammetry mush: outlier removal, decimate, remesh, smart-UV unwrap, vertex-colour
material, centre/orient/scale, single deterministic GLB export. Say this plainly to the
user before building anything.

## Measurement vs appearance - never blur these

- The **COLMAP point cloud** is the measurement source (metric up to scale).
- The **splat-derived mesh** is the visual asset only.
- Surface extraction (Poisson/TSDF) rounds corners and bridges gaps, so **never measure
off the mesh**.
- A reconstruction has **no absolute scale**. Without a reference it is unitless. Record
  scale provenance in the manifest and refuse to imply measurability that does not exist.
  Simplest honest reference: user supplies the object's **longest dimension**; scale =
  declared / longest bbox axis. State the caveat - it is only valid if that is what they
  actually measured.

## Pipeline that works (verified end to end)

```
ffmpeg frames @2fps        (video) or a folder of stills
COLMAP feature_extractor -> sequential_matcher -> mapper
MLX 3DGS train             (needs COLMAP poses; gives visual fidelity)
Open3D Poisson             splat -> vertex-coloured .ply
Blender --background       refine -> .glb
```

Run each stage as a separate process with its own log, make the driver resumable
(`--from-stage`), and emit a manifest carrying params + scale provenance + honesty notes.

## Pitfalls that cost real time

1. **Blender exits 0 when its Python raises.** Always invoke with `--python-exit-code 1`,
   else a failed run looks successful and surfaces later as a misleading missing-file error.
2. **Poisson on a whole-scene splat produces a blob.** A scene splat contains ground,
   background and sky floaters and Poisson welds all of it into one surface. Isolate the
   subject first with **DBSCAN largest-cluster**, not a bounding-box crop: a moving capture
   yields a long strip, so any axis-aligned box that contains the subject also contains a
   large slice of surroundings. Scale `eps` with cloud extent (`eps = max_extent * 0.02`)
   so it works despite the missing absolute scale.
3. **Percentage-cropping the bbox removes almost nothing.** Splat bounds are set by a few
   distant floaters; trimming a percentage of the *extent* barely touches the dense region.
4. **MLX 3DGS `--rasterizer cpp` (Metal) is ~9x faster than the default python path**
   (measured 1.6 vs 0.18 it/s). Check `mlx_gs/renderer/renderer.py` for a cpp branch and a
   built `_rasterizer_metal*.so` before accepting python-path speed.
5. **3DGS training is slow once the resolution schedule hits full res.** A 0.5x->1.0x
   schedule means the back half is ~4x the per-iteration cost. Budget for it or lower it.
6. **COLMAP dies silently after a Homebrew abseil upgrade.** Symptom: `dyld: Library not
   loaded ... libabsl_*.dylib` on launch. Cause: onnxruntime (and anything else) still
   linked against the previous abseil sonames. Fix: `brew reinstall onnxruntime`.
7. **Apple Silicon has no CUDA, so COLMAP dense stereo is unavailable.** Force
   `--FeatureExtraction.use_gpu 0 --FeatureMatching.use_gpu 0`; go to 3DGS for density
   rather than trying to make `patch_match_stereo` work.
8. **COLMAP model_analyzer output is the honest check** that a reconstruction happened
   ("Registered images: N"). Assert on it instead of assuming the mapper succeeded.
9. **Verify by rendering, not by exit codes.** A GLB that loads can still be inside-out,
   blank or a blob. Render it from fixed angles in Blender and look at the images.
10. **3DGS output dirs are timestamped** (`results/<dataset>_mlx[_cpp]_sh<N>_dens_<ts>/`
    with the PLY under `ply/`). Globbing for the newest run is more robust than
    reconstructing the exact suffix.

## Capture discipline (say this before the user shoots)

- A **single object** wants a turntable or tight orbit, not a walkaround flythrough.
- A wide drone path over a landscape is a **scene** capture; extracting a clean object
  mesh from it will disappoint. Diagnose this before blaming the pipeline.
- ~60-80% frame overlap; steady motion; avoid shiny, transparent or textureless subjects
  (SfM has no features to match on them - a physics limit, not a tuning issue).

## Packaging note

Bundling Blender into a .dmg costs ~600MB stripped, and COLMAP must be bundled too (it is
not part of Blender). The result needs codesigning + notarisation or macOS reports the app
as damaged. Blender is GPL: bundling and invoking it as a separate process is fine (mere
aggregation, not linking), but ship its licence text and never imply Blender is your code.
