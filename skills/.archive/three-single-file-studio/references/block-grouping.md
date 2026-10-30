# Block Grouping — concrete code

Every generation becomes ONE `THREE.Group` ("block") so selection/transform/duplicate act on the whole model.

## JSON mode (buildFromSpec)
```js
let added = 0, skipped = 0;
const block = new THREE.Group();
block.name = 'generated-block';
for (const item of items) {
    const mesh = makePrimitiveMesh(item);
    if (mesh) { block.add(mesh); added++; }
    else skipped++;
}
if (added > 0) {
    aiGeneratedGroup.add(block);
    lastGeneratedBlock = block;
}
cleanupAndCenter(); // per-block, see below
```

## Curvature mode (sandboxed) — redirect helper.add into a block
`buildCurveHelpers().add` normally writes to `aiGeneratedGroup`. Override it:
```js
const block = new THREE.Group();
block.name = 'generated-block';
const helpers = buildCurveHelpers();
const realAdd = block.add.bind(block);
helpers.add = (geo, color, pos, rot) => {
    const m = new THREE.Mesh(geo, new THREE.MeshStandardMaterial({
        color: new THREE.Color((color && /^#[0-9a-fA-F]{6}$/.test(color)) ? color : '#0ea5e9'),
        roughness: 0.4, metalness: 0.3
    }));
    m.castShadow = true; m.receiveShadow = true;
    if (pos) m.position.set(pos[0] || 0, pos[1] || 0, pos[2] || 0);
    if (rot) m.rotation.set(deg(rot[0]), deg(rot[1]), deg(rot[2]));
    realAdd(m);
    return m;
};
runSandboxedCurveCode(rawText, helpers); // from safe-client-code-sandbox
aiGeneratedGroup.add(block);
lastGeneratedBlock = block;
cleanupAndCenter();
```

## cleanupAndCenter (per block, not whole group)
```js
function cleanupAndCenter() {
    const blocks = aiGeneratedGroup.children.filter(c => c instanceof THREE.Group || c instanceof THREE.Mesh);
    blocks.forEach((block) => {
        const toRemove = [];
        block.children.forEach((c) => {
            const p = new THREE.Vector3();
            c.getWorldPosition(p);
            if (p.length() > 15) toRemove.push(c);
        });
        toRemove.forEach((c) => { block.remove(c); disposeObj(c); });
        const box = new THREE.Box3().setFromObject(block);
        if (!box.isEmpty()) {
            const center = box.getCenter(new THREE.Vector3());
            block.children.forEach((c) => { if (c.isObject3D) c.position.sub(center); });
        }
    });
}
```
Operating on the whole `aiGeneratedGroup` instead mis-frames multi-model scenes (moves everything to one shared origin).
