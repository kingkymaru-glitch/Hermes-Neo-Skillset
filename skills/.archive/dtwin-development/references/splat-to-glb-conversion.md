# Splat → GLB conversion (DTwin)

## Why
MARU asked (2026-08-15): after the `.ply` is produced, add a step to convert it to a
lightweight `.glb` for portable preview / AR. Chose point cloud (not textured mesh)
because "lightweight".

## What the converter does
`tools/ply_to_glb.py <in.ply> <out.glb> [--max-points N]` (numpy only; run it in
`tools/splat-apple/.venv/bin/python` — no torch needed).

- Reads Gaussian-splat .ply: x,y,z, opacity, scale_0..2, rot_0..3, f_dc_0..2
  (our trainer writes SH degree 0, so NO f_rest_* fields).
- One output point per Gaussian, at the Gaussian mean (center).
- Vertex color from SH DC term: `c = 0.5 + SH_C0 * f_dc` where `SH_C0 = 0.28209479177387814`
  (= 1/(2*sqrt(pi))), clipped 0..1.
- Writes glTF 2.0 binary (GLB):
  - accessor 0: POSITION, VEC3, FLOAT (5126), with min/max
  - accessor 1: COLOR_0, VEC3, normalized UNSIGNED_BYTE (5121) — 3 bytes/vertex => small
  - primitive mode 0 (POINTS)
  - material with `KHR_materials_unlit` + `extensionsUsed: ["KHR_materials_unlit"]` so it
    renders unlit in AR Quick Look / Three (not shaded black).
- `--max-points N` subsamples (np.random.default_rng(0), deterministic) above N points.

## GLB byte layout (for validation)
```
12  : magic "glTF" (0x46546C67) + version(2) + total length
+8  : JSON chunk header: length + type 0x4E4F534A ("JSON")
+JL : JSON (padded to 4 bytes with spaces)
+8  : BIN chunk header: length + type 0x004E4942 ("BIN\0")
+BL : concatenated bufferViews, each padded to 4-byte alignment
```
Validate: `blob[:4]==b'glTF'`, `version==2`, `total == len(blob)`,
each accessor count == vertex count, `bin length == buffers[0].byteLength`.

## Pipeline wiring (`tools/pipeline.sh`)
Inserted right after `DONE $OUT` (publish splat), before the cleanup stage:
```bash
step "converting splat -> lightweight .glb (point cloud)"
GLB_OUT="web/assets/$NAME/model.glb"
if [[ -x "$SPLAT_VENV/bin/python" ]]; then
  "$SPLAT_VENV/bin/python" "$ROOT/tools/ply_to_glb.py" "$OUT" "$GLB_OUT" --max-points 200000 \
    || echo "WARN: .glb conversion failed (splat still published)"
  [[ -f "$GLB_OUT" ]] && echo "DONE $GLB_OUT"
else
  echo "WARN: splat-apple venv missing, skipping .glb conversion"
fi
```
Graceful: if venv missing or converter fails, splat still ships. The `.glb` lives in the
durable `web/assets/<name>/` (NOT cleaned by the EXIT trap).

## Verified result (dji_test)
- 79,367 Gaussians -> 1,191,440 bytes glb (vs 5,137,371 bytes splat, ~4.3x smaller)
- Validated GLB: version 2, json_len 904, bin_len 1190508, == file end, == total.

## UI — DONE (2026-08-15, commit b301b53)
The asset browser now views the `.glb` as the default. `web/main.js` vendors
`three/addons/loaders/GLTFLoader.js` (local) and adds `loadGlb(url)` + `frameCameraToObject(obj)`
(camera fit to the glb's Box3). Auto-load, `defaultAssetRow` click, and build-panel `viewBtn`
all target `assets/<name>/model.glb`. Asset row shows a gold "glb" tag; `window.loadGlb`
exposed for inline handlers. `.ply` is still produced (fidelity source) but the UI no longer
opens it. Still-open: no "Download .glb" button (grab `web/assets/<name>/model.glb` directly).

## Why NOT a textured mesh
A mesh .glb needs meshing (poisson reconstruction) from the point cloud -> heavier,
slower, more failure modes. MARU said "lightweight", so point cloud is the right default.
If a textured mesh is later wanted, it's a separate stage (add meshing + UV + texture bake),
not a change to this converter.
