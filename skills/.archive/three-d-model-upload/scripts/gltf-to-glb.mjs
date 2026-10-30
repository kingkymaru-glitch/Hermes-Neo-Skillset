// gltf-to-glb.mjs — pack a split glTF (.gltf + .bin, optional sibling images)
// into a single self-contained .glb File, entirely client-side.
//
// Drop into your app (rename to .ts; types for File/DataView are global in the
// browser). Usage:
//   const glb = await gltfToGlb(gltfFile, siblingsWhereBinLives);
//   uploadToR2(glb, projectId, "model");
//
// Verified against a real 5.7 MB .bin (see references/split-gltf-case.md).

/**
 * @param {File} gltfFile  the .gltf text file
 * @param {File[]} siblings  other files the user selected (the .bin, textures)
 * @returns {Promise<File>}  a single .glb File
 */
export async function gltfToGlb(gltfFile, siblings) {
  const byBase = new Map();
  for (const f of siblings) byBase.set(f.name.toLowerCase(), f);
  byBase.set(gltfFile.name.toLowerCase(), gltfFile);

  const text = await gltfFile.text();
  const gltf = JSON.parse(text);

  const toDataUri = async (file, mime) => {
    const buf = new Uint8Array(await file.arrayBuffer());
    let binary = "";
    const chunk = 0x8000;
    for (let i = 0; i < buf.length; i += chunk) {
      binary += String.fromCharCode(...buf.subarray(i, i + chunk));
    }
    return `data:${mime};base64,${btoa(binary)}`;
  };

  const resolve = async (uri, mime) => {
    if (!uri) return "";
    if (uri.startsWith("data:")) return uri;
    const name = uri.split("/").pop().split("?")[0];
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

  const pad = (n) => (4 - (n % 4)) % 4;
  const jsonPad = pad(jsonBuf.length);
  const jsonChunkLen = jsonBuf.length + jsonPad;
  const total = 12 + 8 + jsonChunkLen + 8 + 0; // header + JSON chunk + empty BIN chunk

  const out = new ArrayBuffer(total);
  const dv = new DataView(out);
  const u8 = new Uint8Array(out);

  dv.setUint32(0, 0x46546c67, true); // "glTF"
  dv.setUint32(4, 2, true);           // version
  dv.setUint32(8, total, true);       // total length

  let off = 12;
  dv.setUint32(off, jsonChunkLen, true);
  dv.setUint32(off + 4, 0x4e4f534a, true); // "JSON"
  off += 8;
  u8.set(jsonBuf, off);
  off += jsonBuf.length;
  for (let i = 0; i < jsonPad; i++) u8[off + i] = 0x20; // pad with spaces
  off += jsonPad;

  dv.setUint32(off, 0, true);          // BIN chunk length = 0
  dv.setUint32(off + 4, 0x004e4942, true); // "BIN\0"

  const glbName = gltfFile.name.replace(/\.[^.]+$/, "") + ".glb";
  return new File([out], glbName, { type: "model/gltf-binary" });
}
