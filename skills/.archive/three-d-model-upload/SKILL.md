---
name: three-d-model-upload
description: >-
  Browser upload + load of 3D models (glTF/GLB/OBJ) into a Three.js / react-three-fiber
  viewer, with the recurring failure modes that make a model "upload succeeds but won't
  render". Covers the #1 trap: a split .gltf references an external .bin (and textures)
  that a single-file upload leaves behind, so the viewer throws "Failed to load buffer
  .bin". Includes a verified client-side .gltf+.bin -> single .glb packer (no backend
  change). Trigger on: "model failed to load", "GLTFLoader Failed to load buffer .bin",
  "uploaded .gltf but it's blank", "glTF + .bin", "pack glTF to GLB", "Three.js model
  upload", or any 3D-viewer model-upload task.
category: frontend
---

# 3D Model Upload (glTF / GLB / OBJ)

Uploading a 3D model to object storage and rendering it in Three.js has ONE trap that
bites almost every time: **the split glTF format.** Everything else (GLB, OBJ) is
self-contained and "just works."

## The split-glTF trap (read this first)

A `.gltf` file is **JSON text** that *references* external binary data:
- `buffers[].uri` points at a sibling `.bin` (geometry, skinning, animation).
- `images[].uri` may point at sibling texture files (`.png`/`.jpg`).

When the user picks **only the `.gltf`** in a file picker, your uploader pushes that one
`File` to storage. The viewer then does `new GLTFLoader().load(file_url)` and tries to
fetch `Cyclization_Catalyst_Vessel_A6000.bin` **next to the .gltf URL on the storage
host** — which isn't there. Result: the blue "uploaded to R2" toast shows, then a red
`THREE.GLTFLoader: Failed to load buffer "....bin".` The model never renders.

**Two symptoms that look identical but differ:**
- Storage/upload toast succeeded + viewer error → split-glTF missing `.bin` (this trap).
- Upload toast failed → real storage/auth/CORS error (different problem; check R2 creds +
  bucket CORS, not this skill).

## Fix options (recommended = C)

- **(A) Tell the user to upload a different format.** If a `.obj` or `.glb` sibling exists
  on disk, upload that instead — both are self-contained. Quickest, zero code.
- **(B) Upload both files, rewrite the .gltf's `buffer.uri` to the storage URL of the
  `.bin`.** Works but leaves TWO files in storage and the viewer must fetch both; textures
  still need handling. More moving parts.
- **(C) PACK to a single .glb client-side before upload (recommended).** Inline the `.bin`
  (and any referenced textures) as base64 data URIs into the glTF JSON, then wrap it in a
  GLB container. Result: ONE self-contained file the viewer already loads natively. No
  companion-file problem, matches how `.glb` already works, no backend change.

## Implementing (C) — the packer

Full reusable implementation: `scripts/gltf-to-glb.mjs` (hand-rolled, NO dependency — uses
only `File`/`TextEncoder`/`btoa`/`DataView`, all available in the browser). Adapt it into
your framework's `handleFiles`:

```ts
// In the model-upload handler:
const allFiles = Array.from(files);
for (const file of allFiles) {
  let ext = file.name.split(".").pop()?.toLowerCase() ?? "";
  if (!["glb","gltf","obj"].includes(ext)) { toast(`Skipped ${file.name}: unsupported`); continue; }
  let uploadFile = file;
  if (ext === "gltf") {
    const siblings = allFiles.filter((f) => f !== file);   // the .bin (+ textures) user also selected
    uploadFile = await gltfToGlb(file, siblings);           // -> single .glb File
    ext = "glb";
  }
  const { publicUrl } = await uploadToR2(uploadFile, projectId, "model");
  // insert model row with file_ext: ext (now "glb"), file_url: publicUrl
}
```

Critical UX detail: **the file `<input>` MUST be `multiple`**, and you must tell the user
to select the `.gltf` AND its `.bin` together. If they select only the `.gltf`, you CANNOT
silently read the sibling `.bin` (browsers forbid reading arbitrary files). So:
- If a `.gltf` is picked but no `.bin` sibling is in the selection → throw a CLEAR error
  ("Missing companion file \"...bin\" — select the .gltf AND its .bin together"), NOT the
  cryptic THREE error.
- Show a hint under the input: "For a split .GLTF, select the .gltf AND its .bin — they are
  auto-packed into one .glb."

### The GLB container (so the packer is correct)
GLB = 12-byte header + JSON chunk + BIN chunk:
- Header: `0x46546C67` ("glTF"), version `2` (uint32 LE), total length (uint32 LE).
- JSON chunk: length (uint32 LE, padded to 4 with spaces `0x20`), type `0x4E4F534A`
  ("JSON"), then the UTF-8 glTF JSON bytes.
- BIN chunk: length (uint32 LE, can be `0` for an empty chunk), type `0x004E4942` ("BIN\0").
When you inline all buffers/images as `data:` URIs, the BIN chunk is empty (length 0) — that
is valid and GLTFLoader reads the data URIs fine. No byte-offset bookkeeping needed.

## Verification (prove it before claiming done)
Do NOT trust `npm run build` alone for this — the packer is browser-API code. Validate the
algorithm against the real files in Node with `Buffer`/`TextEncoder`/`btoa` polyfills:
1. Parse the `.gltf` JSON; assert the only external `buffers[].uri` is the `.bin` name.
2. Inline it; re-serialize; assert `external buffers still external == []` after packing.
3. Build the GLB bytes; assert header magic `0x46546C67`, version `2`, and `length == total`.
This exact check (run on a real 5.7 MB `.bin`) confirmed a clean pack — see
`references/split-gltf-case.md`.

## Pitfalls
- **OBJ is self-contained; GLB is self-contained; only split glTF needs packing.** Don't
  force-pack `.obj`/`.glb`.
- **Don't try to fetch the missing `.bin` from the user's disk at upload time** if they only
  selected the `.gltf` — browser security blocks it. Surface the clear error + hint instead.
- **Large models**: inlining as base64 inflates ~33% and uses temp memory (hundreds of MB
  for big assets) — fine for inspection-scale models; flag if you ever handle GB-class CAD.
- **GLTFLoader resolves relative URIs against the model's URL.** That's WHY the missing
  sibling fails — the loader looks on the storage host, not the user's disk.
- **`<input accept>` greys out non-listed files — a SILENT second cause of "can't select the
  .bin".** The packer (option C) is useless if the picker won't let the user pick the `.bin`.
  If the model `<input accept=".glb,.gltf,.obj">` omits `.bin`, macOS/Windows GREYS the `.bin`
  out — the user can SEE it in the dialog but cannot select it (⌘-click does nothing). Fix:
  include every companion/alternative extension the handler needs, e.g.
  `accept=".glb,.gltf,.obj,.bin"`. Symptom signature: user says "I can see the bin but I
  cannot select it" → check `accept`, NOT the packer. Same trap hit a texture picker:
  `accept="image/jpeg,image/jpg"` blocked PNG (greyed out) — widened to
  `image/jpeg,image/jpg,image/png`.
- **PNG textures: preserve alpha in a format-aware resize.** A canvas `toBlob` that always
  emits `image/jpeg` flattens PNG transparency to white. When resizing images client-side
  (P16 in supabase-backend), detect the source: if `file.type === "image/png"` emit
  `image/png` (and skip the opaque white `fillRect`), else `image/jpeg`. This keeps proxy/box
  textures with transparency. Also confirm the storage presign `ALLOWED_EXT` includes `png`
  (R2 presign already allowed it here) — a backend allow-list can independently reject it.
- **P51 — Swappable center model on a hero landing page (procedural default + admin GLB upload).**
  When the 3D centerpiece is a marketing showcase (not a file-upload workflow), the pattern is:
  (a) procedural Three.js geometry as the DEFAULT (e.g. a lure, a boat silhouette) — instant
  load, no file fetch, works offline; (b) admin-uploaded `.glb` replaces it when present,
  fetched from Supabase Storage and auto-fit to a target bounding size (compute Box3, scale
  to `TARGET_SIZE / maxDim`, recenter); (c) upload UI is GATED behind an admin-only panel
  (check `profiles.role === 'admin'`) — visitors see only the rotating model, not the upload
  button. The swap happens client-side: read `landing_content` table for `center_model.url`,
  if `null` render procedural, if set load via `GLTFLoader.parse()` on the fetched arraybuffer
  (for `.glb`) or text (for `.gltf`). Dynamic-import Three.js inside `useEffect` (not
  `next/dynamic`) so it stays client-only and avoids SSR window errors. Dispose the previous
  model's geometry/material on swap to prevent memory leaks. Real case (Trip.Pancing hero
  landing, 2026-09-22): Rapala lure as default center stage, admin uploads `.glb` via
  `/admin` page → `center_model.url` updates → hero re-renders with new model, auto-framed.
- **P52 — Three.js inside Next.js must be client-only.** Never import Three.js at module top
  level in a server component or `next/dynamic({ ssr: false })` at the page level for the
  canvas itself — the renderer touches `window`/`document`. Correct pattern: client component
  (`'use client'`), `useEffect` with `import('three')` + `import('three/addons/...')` inside
  the effect body (dynamic await, not static import), so Three.js loads only after mount.
  Cesium is the exception — it loads via `<Script src="..." strategy="beforeInteractive">`
  from CDN, attached to `window.Cesium`, then read inside a `useEffect` that polls for the
  global to appear. Never bundle Cesium through webpack.

## Support files
- `scripts/gltf-to-glb.mjs` — the verified packer (browser APIs; copy into your
  `src/lib/` as a `.ts` and adjust `File`/import style). Takes `(gltfFile, siblings[])`.
- `references/split-gltf-case.md` — reproduction recipe on a real FreeCAD export
  (`Cyclization_Catalyst_Vessel_A6000.gltf` + `.bin`), the exact error string, and the
  Node validation that proved the fix.
