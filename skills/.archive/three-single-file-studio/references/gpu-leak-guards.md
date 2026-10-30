# GPU leak guards — LunaV Studio / Three.js single-file studio

Three.js does NOT garbage-collect GPU resources (geometries, materials) for you.
`mesh`/`geometry` JS objects going out of scope does NOT free the VRAM buffer.
If you rebuild or remove meshes without `.dispose()`, WebGL memory climbs every
frame and the tab freezes "after a while" — classic symptom in this studio.

## Symptom that triggered this note
User: "after a while it makes the whole page not responsive." Root cause was
`updateShapeMesh()` building a new `ExtrudeGeometry` on every slider `input`
tick without disposing the old one. Dragging a slider = dozens of leaked
geometries/sec. Fix: dispose before rebuild.

## Rule
ANY code path that replaces a mesh, swaps geometry, or removes a subtree MUST
dispose the old geometry + material(s) first. Offenders in this file:
slider-driven rebuild, Delete button, Reset Scene, regenerate-swap.

---

## Fix 1 — slider rebuild (`updateShapeMesh`)
```js
function updateShapeMesh() {
    if (!currentShapeMesh || !currentShapeType) return;
    const parent = currentShapeMesh.parent || aiGeneratedGroup;
    const newMesh = createParametricShape(currentShapeType, shapeParams);
    newMesh.position.copy(currentShapeMesh.position);
    newMesh.rotation.copy(currentShapeMesh.rotation);
    newMesh.scale.copy(currentShapeMesh.scale);
    newMesh.material.color.copy(currentShapeMesh.material.color);
    // MANDATORY: free the old GPU resources before dropping the reference
    parent.remove(currentShapeMesh);
    currentShapeMesh.geometry.dispose();
    currentShapeMesh.material.dispose();
    parent.add(newMesh);
    currentShapeMesh = newMesh;
    selectObject(newMesh);
}
// Wire the sliders ONCE (do not re-bind in addShape):
document.getElementById('ctrl-width').addEventListener('input', (e) => {
    shapeParams.width = parseFloat(e.target.value);
    document.getElementById('val-width').textContent = shapeParams.width.toFixed(1);
    updateShapeMesh();
});
// ... same for ctrl-depth, ctrl-height
```

## Fix 2 — Delete button (block-safe traverse-dispose)
`disposeObj` already exists in the file and recurses the subtree:
```js
function disposeObj(obj) {
    obj.traverse(o => {
        if (o.geometry) o.geometry.dispose();
        if (o.material) (Array.isArray(o.material) ? o.material : [o.material]).forEach(m => m.dispose());
    });
}
// Delete handler — use disposeObj, but REMOVE FROM obj.parent (NOT aiGeneratedGroup):
document.getElementById('delete-btn').addEventListener('click', () => {
    if (selectedObject) {
        let obj = selectedObject;
        let parent = obj.parent;
        if (parent) {
            parent.remove(obj);
            disposeObj(obj); // frees EVERY child mesh/material of a multi-part block
            if (parent !== aiGeneratedGroup && parent.children.length === 0) {
                aiGeneratedGroup.remove(parent); // drop the now-empty block
                disposeObj(parent);
            }
        }
        deselectObject();
    }
});
```
> BUG WARNING: `aiGeneratedGroup.remove(selectedObject)` is the trap. Models live inside
> `generated-block` groups, so the selected object is NEVER a direct child of `aiGeneratedGroup`
> and that call silently no-ops — the Delete button appears dead. Always remove from `obj.parent`.

## Fix 3 — 2D Builder must produce a block too
`addShape()` originally added a loose mesh to `aiGeneratedGroup`. That breaks
Duplicate (`topBlock` returns the loose mesh → only that shape clones) and
whole-model selection. Correct version:
```js
function addShape(type) {
    const mesh = createParametricShape(type, shapeParams);
    const block = new THREE.Group();
    block.name = 'generated-block';
    block.add(mesh);
    aiGeneratedGroup.add(block);
    lastGeneratedBlock = block;
    currentShapeMesh = mesh;
    currentShapeType = type;
    selectObject(mesh);
}
document.getElementById('add-rect').addEventListener('click', () => addShape('rect'));
document.getElementById('add-circle').addEventListener('click', () => addShape('circle'));
document.getElementById('add-sphere').addEventListener('click', () => addShape('sphere'));
```
NOTE: bind the `add-rect/circle/sphere` click listeners exactly ONCE. Re-binding
them (e.g. in a stale copy still sitting below the new handler) adds two meshes
per click. After editing, grep for `addShape(` / `addEventListener('click', () => { const mesh = createParametricShape`
and confirm the old inline form is GONE (count should be 0).

## Quick leak audit (run after edits)
Search the file for `.geometry =` / `.clone(` / `new THREE.*Geometry` and verify
every replaced mesh's previous geometry/material is disposed. Also confirm
`resetScene()` and the regenerate-swap loop call `disposeObj` on removed children
(the existing code already does — don't regress it).
