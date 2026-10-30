# Visual Editor: Move / Rotate / Scale Sliders (LunaV-style)

User preference for LunaV Studio: transform editing is done with **range sliders that appear on selection**, not numeric `<input type="number">` boxes. Direct-manipulation feel matching LunaV's own editor.

## HTML (one panel, hidden until an object is selected)

```html
<!-- drops in place of the old numeric "precision-controls" block -->
<div id="slider-controls" class="hidden space-y-3 bg-slate-900/50 p-3 rounded mb-3">
    <div>
        <p class="text-xs text-cyan-300 font-semibold mb-1">Move</p>
        <div class="flex items-center gap-2 mb-1"><label class="w-3 text-slate-500 text-xs">X</label><input type="range" id="mov-x" min="-15" max="15" step="0.1" value="0" class="flex-1 accent-cyan-400"><span id="mov-x-v" class="text-[10px] text-slate-400 w-10 text-right">0.0</span></div>
        <div class="flex items-center gap-2 mb-1"><label class="w-3 text-slate-500 text-xs">Y</label><input type="range" id="mov-y" min="-15" max="15" step="0.1" value="0" class="flex-1 accent-cyan-400"><span id="mov-y-v" class="text-[10px] text-slate-400 w-10 text-right">0.0</span></div>
        <div class="flex items-center gap-2 mb-1"><label class="w-3 text-slate-500 text-xs">Z</label><input type="range" id="mov-z" min="-15" max="15" step="0.1" value="0" class="flex-1 accent-cyan-400"><span id="mov-z-v" class="text-[10px] text-slate-400 w-10 text-right">0.0</span></div>
    </div>
    <div>
        <p class="text-xs text-cyan-300 font-semibold mb-1">Rotate (°)</p>
        <div class="flex items-center gap-2 mb-1"><label class="w-3 text-slate-500 text-xs">X</label><input type="range" id="rot-x" min="-180" max="180" step="1" value="0" class="flex-1 accent-cyan-400"><span id="rot-x-v" class="text-[10px] text-slate-400 w-10 text-right">0</span></div>
        <div class="flex items-center gap-2 mb-1"><label class="w-3 text-slate-500 text-xs">Y</label><input type="range" id="rot-y" min="-180" max="180" step="1" value="0" class="flex-1 accent-cyan-400"><span id="rot-y-v" class="text-[10px] text-slate-400 w-10 text-right">0</span></div>
        <div class="flex items-center gap-2 mb-1"><label class="w-3 text-slate-500 text-xs">Z</label><input type="range" id="rot-z" min="-180" max="180" step="1" value="0" class="flex-1 accent-cyan-400"><span id="rot-z-v" class="text-[10px] text-slate-400 w-10 text-right">0</span></div>
    </div>
    <div>
        <p class="text-xs text-cyan-300 font-semibold mb-1">Scale</p>
        <div class="flex items-center gap-2 mb-1"><label class="w-3 text-slate-500 text-xs">X</label><input type="range" id="scl-x" min="0.1" max="5" step="0.1" value="1" class="flex-1 accent-cyan-400"><span id="scl-x-v" class="text-[10px] text-slate-400 w-10 text-right">1.0</span></div>
        <div class="flex items-center gap-2 mb-1"><label class="w-3 text-slate-500 text-xs">Y</label><input type="range" id="scl-y" min="0.1" max="5" step="0.1" value="1" class="flex-1 accent-cyan-400"><span id="scl-y-v" class="text-[10px] text-slate-400 w-10 text-right">1.0</span></div>
        <div class="flex items-center gap-2 mb-1"><label class="w-3 text-slate-500 text-xs">Z</label><input type="range" id="scl-z" min="0.1" max="5" step="0.1" value="1" class="flex-1 accent-cyan-400"><span id="scl-z-v" class="text-[10px] text-slate-400 w-10 text-right">1.0</span></div>
    </div>
</div>
```

## JS

### Show / hide on selection
```js
// in selectObject():
document.getElementById('slider-controls').classList.remove('hidden');
// in deselectObject():
document.getElementById('slider-controls').classList.add('hidden');
```

### Push current transform into sliders (gizmo <-> slider sync)
Keep the function name `updatePrecisionInputs()` for minimal churn:
```js
function updatePrecisionInputs() {
    if (!selectedObject) return;
    const setMov = (id, v) => { document.getElementById(id).value = v.toFixed(1); document.getElementById(id + '-v').textContent = v.toFixed(1); };
    const setRot = (id, v) => { const d = THREE.MathUtils.radToDeg(v); document.getElementById(id).value = Math.round(d); document.getElementById(id + '-v').textContent = Math.round(d); };
    const setScl = (id, v) => { document.getElementById(id).value = v.toFixed(1); document.getElementById(id + '-v').textContent = v.toFixed(1); };
    setMov('mov-x', selectedObject.position.x);
    setMov('mov-y', selectedObject.position.y);
    setMov('mov-z', selectedObject.position.z);
    setRot('rot-x', selectedObject.rotation.x);
    setRot('rot-y', selectedObject.rotation.y);
    setRot('rot-z', selectedObject.rotation.z);
    setScl('scl-x', selectedObject.scale.x);
    setScl('scl-y', selectedObject.scale.y);
    setScl('scl-z', selectedObject.scale.z);
}
// keep sliders live while dragging the gizmo:
transformControls.addEventListener('change', updatePrecisionInputs);
```

### Slider listeners (use 'input' for live drag)
```js
['mov-x', 'mov-y', 'mov-z'].forEach((id, idx) => {
    document.getElementById(id).addEventListener('input', (e) => {
        if (selectedObject) { selectedObject.position[idx] = parseFloat(e.target.value); document.getElementById(id + '-v').textContent = parseFloat(e.target.value).toFixed(1); }
    });
});
['rot-x', 'rot-y', 'rot-z'].forEach((id, idx) => {
    document.getElementById(id).addEventListener('input', (e) => {
        if (selectedObject) { selectedObject.rotation[idx] = THREE.MathUtils.degToRad(parseFloat(e.target.value)); document.getElementById(id + '-v').textContent = Math.round(parseFloat(e.target.value)); }
    });
});
['scl-x', 'scl-y', 'scl-z'].forEach((id, idx) => {
    document.getElementById(id).addEventListener('input', (e) => {
        if (selectedObject) { selectedObject.scale[idx] = parseFloat(e.target.value); document.getElementById(id + '-v').textContent = parseFloat(e.target.value).toFixed(1); }
    });
});
```

## Conventions
- Readout span id = slider id + `'-v'` (e.g. `mov-x-v`). Update it in the same handler.
- Ranges are tuned for ~unit-scale models: Move ±15, Rotate ±180°, Scale 0.1–5. Widen if models are large.
- Wire `transformControls` `change` -> `updatePrecisionInputs` so gizmo drags move the sliders too (two-way sync).
- Remove the old `precision-controls` number-box ID **everywhere** (show/hide + listeners) so no `getElementById('pos-x')` is left dangling.
