# Split glTF → single .glb packer (client-side, before R2 upload)

## Problem
A `.gltf` is a JSON file that references an external `.bin` (geometry/buffers)
and sometimes sibling image files. If you upload ONLY the `.gltf` to R2, the
viewer (`THREE.GLTFLoader`) looks for `<name>.bin` next to it on R2, can't find
it, and throws `Failed to load buffer "<name>.bin"`. The model never renders.

Two fixes required:
1. File picker `accept` must include `.bin` (and image exts) or macOS greys the
   `.bin` out and the user can see but not select it.
2. Pack `.gltf` + `.bin` (+ textures) into ONE `.glb` in-browser, then upload that.

## Helper — `src/lib/gltf-pack.ts`

```ts
/**
 * gltfToGlb — pack a split glTF (.gltf + .bin, optional sibling images) into a
 * single self-contained .glb File, entirely client-side. Inlines the companion
 * .bin (and any textures) as data URIs, then wraps the modified glTF JSON in the
 * GLB container (JSON chunk + empty BIN chunk). GLTFLoader reads data URIs fine.
 */
export async function gltfToGlb(gltfFile: File, siblings: File[]): Promise<File> {
  const byBase = new Map<string, File>();
  for (const f of siblings) byBase.set(f.name.toLowerCase(), f);
  byBase.set(gltfFile.name.toLowerCase(), gltfFile);

  const text = await gltfFile.text();
  const gltf = JSON.parse(text) as Record<string, unknown> & {
    buffers?: { uri?: string }[];
    images?: { uri?: string }[];
  };

  const toDataUri = async (file: File, mime: string) => {
    const buf = new Uint8Array(await file.arrayBuffer());
    let binary = "";
    const chunk = 0x8000;
    for (let i = 0; i < buf.length; i += chunk) {
      binary += String.fromCharCode(...buf.subarray(i, i + chunk));
    }
    return `data:${mime};base64,${btoa(binary)}`;
  };

  const resolve = async (uri: string | undefined, mime: string): Promise<string> => {
    if (!uri) return "";
    if (uri.startsWith("data:")) return uri;
    const name = uri.split("/").pop()!.split("?")[0];
    const file = byBase.get(name.toLowerCase());
    if (!file) throw new Error(`Missing companion file "${name}" for ${gltfFile.name}`);
    return toDataUri(file, mime);
  };

  if (Array.isArray(gltf.buffers)) {
    for (const b of gltf.buffers) {
      if (b.uri && !b.uri.startsWith("data:")) {
        b.uri = await resolve(b.uri, "application/octet-stream");
      }
    }
  }
  if (Array.isArray(gltf.images)) {
    for (const img of gltf.images) {
      if (img.uri && !img.uri.startsWith("data:")) {
        const ext = (img.uri.split(".").pop() ?? "png").toLowerCase();
        const mime = ext === "jpg" || ext === "jpeg" ? "image/jpeg" : `image/${ext}`;
        try { img.uri = await resolve(img.uri, mime); } catch { /* texture optional */ }
      }
    }
  }

  const json = JSON.stringify(gltf);
  const enc = new TextEncoder();
  const jsonBuf = enc.encode(json);
  const pad = (n: number) => (4 - (n % 4)) % 4;
  const jsonPad = pad(jsonBuf.length);
  const jsonChunkLen = jsonBuf.length + jsonPad;
  const total = 12 + 8 + jsonChunkLen + 8 + 0; // header + JSON chunk + empty BIN chunk

  const out = new ArrayBuffer(total);
  const dv = new DataView(out);
  const u8 = new Uint8Array(out);
  dv.setUint32(0, 0x46546c67, true); // "glTF"
  dv.setUint32(4, 2, true);          // version
  dv.setUint32(8, total, true);      // total length
  let off = 12;
  dv.setUint32(off, jsonChunkLen, true);
  dv.setUint32(off + 4, 0x4e4f534a, true); // "JSON"
  off += 8;
  u8.set(jsonBuf, off);
  off += jsonBuf.length;
  for (let i = 0; i < jsonPad; i++) u8[off + i] = 0x20; // space padding
  off += jsonPad;
  dv.setUint32(off, 0, true);                  // BIN chunk length = 0
  dv.setUint32(off + 4, 0x004e4942, true);    // "BIN\0"

  const glbName = gltfFile.name.replace(/\.[^.]+$/, "") + ".glb";
  return new File([out], glbName, { type: "model/gltf-binary" });
}
```

## Wire-up in the model-upload handler (`ProjectWorkspace.tsx` → `handleFiles`)

```ts
if (ext === "gltf") {
  const siblings = allFiles.filter((f) => f !== file);
  uploadFile = await gltfToGlb(file, siblings);
  ext = "glb"; // store as .glb so the viewer loads one self-contained file
}
```

The picker `<input accept=".glb,.gltf,.obj,.bin" multiple>`. If the user only
selects the `.gltf` (no `.bin`), `gltfToGlb` throws a clear
`Missing companion file "<name>.bin"` instead of the cryptic THREE error.

## Verification recipe (Node, against real files — no browser needed)

The packer uses browser APIs (`File`, `btoa`, `TextEncoder`), but the GLB
container logic is plain ArrayBuffer math. To verify without a browser,
re-implement the same algorithm in Node against the real files and assert:
- GLB magic `0x46546C67`, version `2`, `total` equals the written length.
- After packing, `buffers[].uri` that were external are now `data:` URIs
  (zero external buffers remain).

This was run against a real `Cyclization_Catalyst_Vessel_A6000.gltf` + `.bin`
(5.7 MB): header valid, 0 buffers external after pack. The viewer then loads
the `.glb` with no "Failed to load buffer" error.

## Presign note
The R2 presign Edge Function `ALLOWED_EXT` already includes `glb`/`gltf`/`bin`,
so no backend change is needed for the packed `.glb` (or the `.bin` if uploaded
raw). If you restrict extensions, add `glb` and `bin`.
