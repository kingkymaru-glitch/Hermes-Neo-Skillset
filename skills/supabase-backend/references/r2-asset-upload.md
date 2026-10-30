# R2 / browser asset-upload gotchas (ss-rover-cloud, 2026-07-26)

Two recurring upload failures seen shipping a 3D-inspection SaaS where the
browser uploads models/textures straight to Cloudflare R2 via a presigned URL.

## G1 — `<input accept>` greys out a NEEDED extension (file visible but unselectable)

macOS (and others) render any file whose extension is NOT in the `accept`
attribute as **dimmed / unselectable** — the user can SEE it but cannot pick
it. Two real bugs traced to this:

- Split glTF: picker was `accept=".glb,.gltf,.obj"` → the companion `.bin`
  was greyed out, so the user could never select it alongside the `.gltf`.
- Proxy texture: picker was `accept="image/jpeg,image/jpg"` → PNG textures
  were greyed out even though the upload path + R2 presign both accepted PNG.

**Rule:** the `accept` list must include EVERY extension the handler can
actually consume, including companion files. For model upload that means
`.glb,.gltf,.obj,.bin` (the `.bin` travels with a split `.gltf`). For image
textures, list every raster type the presign `ALLOWED_EXT` allows
(`jpg,jpeg,png,webp,gif`). Also confirm the R2 presign Edge Function's
`ALLOWED_EXT` includes the type — a mismatch there fails LATER (400 on
presign), not at the picker.

## G2 — Split glTF (.gltf + .bin) upload fails in the viewer

A `.gltf` is JSON that *references* an external `.bin` (geometry/buffers) and
optionally image files. Uploading ONLY the `.gltf` succeeds (R2 gets the
file), but `THREE.GLTFLoader` then tries to fetch `…bin` **next to it on R2**
→ `Failed to load buffer "Cyclization_Catalyst_Vessel_A6000.bin"`. The
storage upload shows a green "uploaded to R2" toast, then a RED THREE error —
confusing because the first step looked fine.

**Fix: pack split glTF → single `.glb` in the browser before upload**
(`gltfToGlb()` in `src/lib/gltf-pack.ts`). No backend change. Algorithm:

1. From the selected `FileList`, find the sibling `.bin` (and any images) by
   basename. The user must multi-select the `.gltf` AND `.bin` together
   (hence G1 — `.bin` must be in `accept`).
2. Read `.gltf` text → `JSON.parse`. For each `buffers[].uri` that is a
   relative name (not `data:`), read the matching `.bin` File → base64 →
   replace `uri` with `data:application/octet-stream;base64,…`. Same for
   `images[].uri` (wrap in try/catch — missing texture is non-fatal).
3. Build the GLB container:
   - Header: `0x46546C67` ("glTF"), `version=2` (uint32 LE), `total length`.
   - JSON chunk: `length` (uint32 LE), `0x4E4F534A` ("JSON"), JSON bytes
     padded to 4 with spaces `0x20`.
   - BIN chunk: `length=0`, `0x004E4942` ("BIN\0") — valid empty BIN chunk
     since everything is inlined as data URIs.
4. Return `new File([out], base+".glb", { type: "model/gltf-binary" })`.
   `THREE.GLTFLoader` loads `.glb` natively, so the viewer needs no change.

Verified against a real 5.7 MB `.bin`: GLB header valid, 0 buffers left
external after packing. A standalone Node re-implementation of steps 2–3
(using `struct.pack`) is a good offline sanity check when you can't run the
browser `File`/`btoa` APIs.

**UX:** the model `<input>` already has `multiple`. Add a hint: "For a split
.gltf, select the .gltf AND its .bin together — auto-packed into one .glb."
If only the `.gltf` is picked, surface a clear "Missing companion file … .bin"
toast instead of the cryptic THREE error.

## Where these live in ss-rover-cloud
- `src/lib/gltf-pack.ts` — `gltfToGlb()`
- `src/lib/r2-upload.ts` — `uploadToR2()` (presigned PUT), `resizeImage()`
  (P16 client downscale, also keeps PNG alpha now)
- `supabase/functions/r2-presign/index.ts` — `ALLOWED_EXT` gate
- `src/components/ProjectWorkspace.tsx` — `handleFiles()` packs gltf→glb;
  model + texture `<input accept>` lists
