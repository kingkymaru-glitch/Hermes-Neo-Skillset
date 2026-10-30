# Selection & Duplicate — concrete code

## Click = leaf surface, Double-click = whole block
```js
function onMouseClick(event) {
    if (event.target.closest('.glass-panel')) return;
    mouse.x = (event.clientX / window.innerWidth) * 2 - 1;
    mouse.y = -(event.clientY / window.innerHeight) * 2 + 1;
    raycaster.setFromCamera(mouse, camera);
    const intersects = raycaster.intersectObjects(aiGeneratedGroup.children, true);
    if (intersects.length > 0) {
        let target = intersects[0].object; // leaf mesh — DO NOT climb to parent
        if (event.shiftKey) {
            if (selectedSet.has(target)) selectedSet.delete(target);
            else selectedSet.add(target);
            if (selectedSet.size === 1) selectObject([...selectedSet][0]);
            else { transformControls.detach(); selectedObject = null; updateSelCount(); }
        } else {
            selectedSet.clear();
            selectedSet.add(target);
            selectObject(target);
        }
    } else {
        if (!event.shiftKey) { deselectObject(); selectedSet.clear(); }
    }
    updateSelCount();
}
function topBlock(obj) {
    while (obj && obj.parent && obj.parent !== aiGeneratedGroup) obj = obj.parent;
    return obj;
}
window.addEventListener('dblclick', (event) => {
    if (event.target.closest('.glass-panel')) return;
    mouse.x = (event.clientX / window.innerWidth) * 2 - 1;
    mouse.y = -(event.clientY / window.innerHeight) * 2 + 1;
    raycaster.setFromCamera(mouse, camera);
    const intersects = raycaster.intersectObjects(aiGeneratedGroup.children, true);
    if (intersects.length > 0) selectObject(topBlock(intersects[0].object));
});
```

## Duplicate = clone the WHOLE block (the fix)
Earlier bug: `if (clones.length===1) selectObject else detach` left tools dead on the copy. Always re-attach.
```js
function cloneObject(src) {
    const dst = src.clone(true);
    dst.traverse(o => {
        if (o.material) {
            o.material = (Array.isArray(o.material) ? o.material : [o.material]).map(m => m.clone());
        }
    });
    return dst;
}
function duplicateSelected() {
    let blocks = [];
    if (selectedSet.size) {
        const seen = new Set();
        [...selectedSet].forEach(o => {
            const b = topBlock(o);
            if (b && !seen.has(b)) { seen.add(b); blocks.push(b); }
        });
    } else if (lastGeneratedBlock && aiGeneratedGroup.children.includes(lastGeneratedBlock)) {
        blocks = [lastGeneratedBlock];
    } else {
        blocks = aiGeneratedGroup.children.slice();
    }
    if (!blocks.length) {
        document.getElementById('status-log').innerHTML = 'Nothing to duplicate — generate or select first.';
        return;
    }
    const clones = [];
    blocks.forEach(b => {
        const c = cloneObject(b);
        c.position.x += 3; // offset beside the original
        aiGeneratedGroup.add(c);
        clones.push(c);
    });
    deselectObject();
    selectedSet.clear();
    clones.forEach(c => selectedSet.add(c));
    selectObject(clones[0]); // keep tools live
    updateSelCount();
    document.getElementById('status-log').innerHTML =
        `Duplicated ${clones.length} block(s) (whole model) → offset to the right. Edit with the tools.`;
}
```

Button: `<button id="duplicate-btn" class="... col-span-2 ...">⧉ Duplicate Whole Model</button>`
Listener: `document.getElementById('duplicate-btn').addEventListener('click', duplicateSelected);`
