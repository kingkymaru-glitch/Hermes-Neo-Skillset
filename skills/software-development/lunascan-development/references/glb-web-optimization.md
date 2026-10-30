# LUNASCAN Batch 5 — web-ready .glb optimization

ODM (`lunascan/odm.py`, Batch 3+4) emits a **Draco-compressed** textured `.glb`
(`--gltf`). LunaV's Three.js viewer wants a compact, meshopt + quantized,
webp-textured asset. Batch 5 bridges that gap.

## Toolchain

`tools/3d-optimize/` (Node.js, ESM). Install once:

```
cd tools/3d-optimize && npm init -y && npm pkg set type="module"
npm install @gltf-transform/core @gltf-transform/extensions @gltf-transform/functions \
            meshoptimizer draco3d sharp
```

`optimize.mjs` is invoked as `node optimize.mjs <in.glb> <out.glb> [--no-textures]`.
Python side (`lunascan/optimize.py::optimize_glb`) shells out to it and returns
bool (True = optimized written; False = keep raw glb). Graceful: if `node` or the
script is missing, returns False (RC 0, raw glb kept).

## gltf-transform gotchas (all hit 2026-08-07)

1. NEVER `registerExtensions(ALL_EXTENSIONS)`. It pulls `KHRDracoMeshCompression`,
   whose `install()` eagerly initializes the Draco decoder and THROWS
   `Cannot read properties of undefined (reading 'DT_FLOAT32')` if `draco3d` is
   not installed. Register only the extensions you use + Draco, and supply the
   decoder/encoder modules:

   ```
   io.registerExtensions([KHRMeshQuantization, KHRTextureBasisu, KHRMaterialsUnlit,
            KHRMaterialsEmissiveStrength, KHRDracoMeshCompression]);
   io.registerDependencies({
     "draco3d.decoder": await draco3d.createDecoderModule(),
     "draco3d.encoder": await draco3d.createEncoderModule(),
   });
   ```

2. After re-encoding as meshopt, the stale `KHR_draco_mesh_compression` extension
   declaration lingers in the doc. Strict loaders fail on the dangling claim.
   Drop it before writing:

   ```
   for (const ext of doc.getRoot().listExtensionsUsed()) {
     if (ext.extensionName === "KHR_draco_mesh_compression") ext.dispose();
   }
   ```
   NOTE: `doc.getRoot().removeExtension(...)` is NOT a method — use `ext.dispose()`.

3. Pipeline order: `weld() -> dedup() -> prune() -> flatten() -> quantize()` then
   (optional) `textureCompress({ targetFormat: "webp", encoder: sharp, resize: [2048,2048] })`.
   Register `meshopt.encoder`/`meshopt.decoder` deps right before `io.writeBinary`.

## Verification result (701 dataset)

Raw ODM `site_model.glb` 3.74 MB -> optimized 0.97 MB (74% smaller).
Readback valid, only `KHR_mesh_quantization` extension present. CLI exits non-zero
on failure so `optimize_glb` can fall back.

## Docker auto-start (lunascan/docker_util.py)

`ensure_docker_running()` is called at the top of `run_odm`. If `docker info`
fails: macOS -> `open -a Docker` then poll `docker info` <= `DOCKER_START_TIMEOUT`
(120s); Linux -> `systemctl start docker`; else return False. This makes the .dmg
self-contained (no manual Docker Desktop pre-start). Batch 1 (VideoToolbox) + Batch
2 (CoreML) are Apple-Silicon-native and CANNOT run in Docker — only ODM is
containerized. Do not attempt to dockerize ingest/masking.

## DMG packaging requirement

`build_app.py` MUST `--add-data=app:app` (GUI was never bundled before, so the
Run button crashed) and `--add-data=tools/3d-optimize:tools/3d-optimize` (Node
optimizer). Rebuild + grep the bundled copy to confirm the changed file is present.
