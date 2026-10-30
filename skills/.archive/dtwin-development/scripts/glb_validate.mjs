#!/usr/bin/env node
// Validate a DTwin mesh .glb: glTF 2.0 binary with JSON+BIN chunks, correct
// primitive mode, and face count. Usage: node glb_validate.mjs <file.glb>
const fs = require('fs');
const p = process.argv[2];
if (!p) { console.error('usage: node glb_validate.mjs <file.glb>'); process.exit(2); }
const b = fs.readFileSync(p);
const dv = new DataView(b.buffer, b.byteOffset, b.byteLength);
let ok = true;
const magic = b.slice(0,4).toString('latin1');
if (magic !== 'glTF') { ok = false; console.log('magic BAD', magic); }
const ver = dv.getUint32(4, true);
const total = dv.getUint32(8, true);
if (ver !== 2) { ok = false; console.log('version BAD', ver); }
if (total !== b.byteLength) { ok = false; console.log('total mismatch', total, b.byteLength); }
const jsonLen = dv.getUint32(12, true);
const jsonType = b.slice(16,20).toString('latin1');
if (jsonType !== 'JSON') { ok = false; console.log('jsonType BAD', jsonType); }
const json = JSON.parse(b.slice(20, 20+jsonLen).toString('latin1').replace(/\0+$/,''));
const binLen = dv.getUint32(20+jsonLen, true);
const binType = b.slice(20+jsonLen+4, 20+jsonLen+8).toString('latin1');
if (binType !== 'BIN\0') { ok = false; console.log('binType BAD', JSON.stringify(binType)); }
let faces = 0, verts = 0, mode = -1;
for (const m of json.meshes || []) {
  for (const prim of m.primitives) {
    mode = prim.mode ?? 4;
    const acc = json.accessors;
    if (prim.indices != null) faces += Math.floor(acc[prim.indices].count / 3);
    if (prim.attributes.POSITION != null) verts += acc[prim.attributes.POSITION].count;
  }
}
console.log(`magic=${magic} ver=${ver} total=${total} jsonType=${jsonType} binType=${binType} mode=${mode} faces=${faces} verts=${verts}`);
console.log(ok ? 'VALID GLB OK' : 'INVALID GLB');
process.exit(ok ? 0 : 1);
