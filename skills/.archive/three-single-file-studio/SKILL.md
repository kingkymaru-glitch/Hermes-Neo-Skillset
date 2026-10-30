---
name: three-single-file-studio
description: Build a single-file HTML + Three.js "model studio" app where an AI (Gemini etc.) generates 3D models and the user can select, transform, group, ungroup, duplicate, and reset them. Covers the critical scene-structure rule (wrap each generation in ONE THREE.Group "block"), the click=leaf / double-click=block selection model, whole-block duplicate, deep clone with material clone, and per-block recenter. Pair with safe-client-code-sandbox (the AI code runs in a lockdown).
---

# Three.js Single-File Model Studio

## When to use
- You're building a single-file `index.html` (Three.js via importmap/module script) where an AI model generates 3D geometry and the user edits it afterward with on-screen tools (move/rotate/scale, color, group, ungroup, duplicate, reset).
- Recurring for this user's 3D SaaS (LunaV Studio, MARU, etc.). The model can return either JSON primitives or curvature code — see `frontend/safe-client-code-sandbox` for the execution lockdown. This skill is about the SCENE STRUCTURE that makes the editing tools work.

## USER UI PREFERENCE (this user, LunaV Studio)
- **Minimal toolbar.** Do NOT add a cluttered button row (Select All / Group / Ungroup / Duplicate Whole Model). The user explicitly rejected that layout as "so many bug and most button not working." Keep only: Reset Scene + the gizmo mode buttons (Move/Rotate/Scale) + Delete (shown on selection) + Color picker.
- **Transform path = gizmo, NOT sliders.** When an object is selected, transform it with the **gizmo** (Move/Rotate/Scale mode buttons + on-screen drag handles). Move/Rotate/Scale **sliders** were explicitly rejected by the user as "a dead function, useless" and REMOVED — do NOT re-add them. `references/visual-editor-sliders.md` is retained only as HISTORICAL reference; treat it as obsolete and do not reproduce it.
- Keep Duplicate as a feature only if the user asks; it was removed from the UI per this preference. The deep-clone machinery (`cloneObject`) still lives in `references/selection-and-duplicate.md` if it's ever re-added.

## THE RULE (most common bug here)
**Wrap every generated model in exactly one `THREE.Group` ("block") before adding it to the parent `aiGeneratedGroup`.** Do NOT add loose meshes directly to the parent.

If you add loose meshes:
- Clicking selects a single sub-part (a hull mesh), not the whole model.
- "Duplicate" copies only that sub-part.
- After a whole-model duplicate the code may detach selection → editing tools have nothing to attach to → "the surface can't be modified."

A block = one model = one user-editable unit. Set `block.name = 'generated-block'` and track it in `lastGeneratedBlock`.

## Selection model (click vs double-click)
A two-level selection is the cleanest UX:
- **Single click** → select the actual surface (leaf `Mesh`) so move/rotate/scale/color/delete act on it. `intersects[0].object` is already the leaf; do NOT climb to the parent.
- **Double click** → select the whole top-level block (`topBlock(obj)`) for whole-model transforms.
- **Shift+click** → add/remove a surface to a multi-selection (`selectedSet`).
- `intersectObjects(aiGeneratedGroup.children, true)` (recursive) so clicks hit nested meshes.

`topBlock(obj)`:
```js
function topBlock(obj) {
    while (obj && obj.parent && obj.parent !== aiGeneratedGroup) obj = obj.parent;
    return obj;
}
```
`dblclick` handler mirrors the click handler but calls `selectObject(topBlock(intersects[0].object))`. Both must early-return on `event.target.closest('.glass-panel')` so panel clicks don't raycast.

## Duplicate = clone the WHOLE block
Key fixes baked in (see `references/selection-and-duplicate.md` for full code):
- Resolve which top-level blocks to clone: if `selectedSet` has entries, map each to its `topBlock` (dedupe); else clone `lastGeneratedBlock`; else clone all.
- Use `cloneObject` (deep clone + **clone every material** so recoloring the copy doesn't change the original).
- Offset the copy (`c.position.x += 3`) so it sits beside the original.
- After cloning, **select the first clone** with `selectObject(clones[0])` and add all to `selectedSet`. Do NOT detach when there are multiple — that kills the tools. The earlier bug ("duplicated surface can't be modified") was exactly `if (clones.length===1) selectObject else detach`. Always re-attach.

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
```

## Wrapping each generation into a block
- **JSON mode**: build a `THREE.Group`, add each primitive mesh to it, then `aiGeneratedGroup.add(block); lastGeneratedBlock = block;`. See `references/block-grouping.md`.
- **Curvature mode** (sandboxed): `buildCurveHelpers().add` writes straight to `aiGeneratedGroup`. Redirect it to a per-generation block by overriding `helpers.add` to push into a fresh `block` (and mirror the material/castShadow setup), then add the block after running the code. See `references/block-grouping.md`.

## Per-block cleanup/recenter (`cleanupAndCenter`)
Drop stray orphans (parts >15 units from origin) **per block**, then recenter each block by subtracting its bounding-box center from each child's position. Operating on the whole `aiGeneratedGroup` instead mis-frames multi-model scenes. See `references/block-grouping.md`.

## 2D Parametric Builder (Add Rect / Circle / Sphere) — SAME block rule applies
The JSON and curvature paths are block-wrapped (above), but the **2D Builder** has its own `createParametricShape()` + `addShape()` path. If `addShape()` adds a loose mesh straight to `aiGeneratedGroup`, the 2D shape becomes non-blockable: Duplicate clones just that loose mesh, `topBlock()` returns the mesh itself, and Select-All / Group semantics break.
- `addShape(type)` MUST wrap the new mesh in a `THREE.Group` named `generated-block`, add the block to `aiGeneratedGroup`, set `lastGeneratedBlock = block`, then `selectObject(mesh)`.
- Both the JSON/curve-generated blocks and 2D-builder blocks must live in the same `aiGeneratedGroup` so Duplicate handles them identically.

## GPU memory-leak guards (prevents the "page goes unresponsive after a while" freeze)
This is a real, reproducible freeze, not a flake. Two leak sites:

**1. Slider-driven rebuild (`updateShapeMesh`)** — fires on every `input` tick while dragging. The original built a new `ExtrudeGeometry` each tick WITHOUT disposing the previous one. Dozens of geometries/sec → WebGL memory climbs → tab freezes.
Fix: dispose the old geometry + material before swapping:
```js
const parent = currentShapeMesh.parent || aiGeneratedGroup;
const newMesh = createParametricShape(currentShapeType, shapeParams);
// ...copy transform/color...
parent.remove(currentShapeMesh);
currentShapeMesh.geometry.dispose();   // <-- mandatory
currentShapeMesh.material.dispose();   // <-- mandatory
parent.add(newMesh);
currentShapeMesh = newMesh;
```

**2. Delete button — delete from `obj.parent`, NOT `aiGeneratedGroup`.** The `disposeObj` traverse-dispose helper is still correct for freeing GPU memory, BUT the removal line is the classic bug. Every generated model is wrapped in a per-model `THREE.Group` block; a single-clicked mesh's parent is that block (not `aiGeneratedGroup`), and a double-clicked block's parent IS `aiGeneratedGroup`. So `aiGeneratedGroup.remove(selectedObject)` finds no DIRECT child and **silently no-ops** — the Delete button looks dead. Correct handler:
```js
document.getElementById('delete-btn').addEventListener('click', () => {
    if (selectedObject) {
        let obj = selectedObject;
        let parent = obj.parent;
        if (parent) {
            parent.remove(obj);
            disposeObj(obj); // traverse + dispose ALL geometries/materials (block-safe)
            if (parent !== aiGeneratedGroup && parent.children.length === 0) {
                aiGeneratedGroup.remove(parent); // drop the now-empty block too
                disposeObj(parent);
            }
        }
        deselectObject();
    }
});
```
Rule of thumb: **any code path that replaces a mesh or removes a subtree must call `.dispose()` on the old geometry/material(s)** — sliders, Reset Scene, regenerate-swap, and Delete are the usual offenders. Full patterns in `references/gpu-leak-guards.md`.

## Verification before claiming done
- Extract `<script type="module">` and `node --check` (HTML linters don't catch embedded JS).
- Click-test in a browser: generate a model, single-click a surface (tools live), double-click (whole model selected), Duplicate (full copy offset + editable).
- Search the file for duplicate `id=` — a duplicate ID silently breaks `getElementById` listeners.

## See also
- `frontend/safe-client-code-sandbox` — the AI code-execution lockdown (token scan + strict-mode shadow + geometry-only helpers). This skill assumes generated code runs there.
- `references/gpu-leak-guards.md` — full dispose-before-rebuild / block-safe delete patterns, the 2D-builder block-wrap fix, and a post-edit leak audit checklist. READ THIS before touching sliders, Delete, Reset, or regenerate-swap.
- `references/embed-in-nextjs.md` — how to ship the studio as a `public/`-hosted iframe tab inside the Next.js host app, the 3-coordinate tab wiring, and the client-side only `.glb` export note.
- `references/visual-editor-sliders.md` — HISTORICAL ONLY (obsolete). Move/Rotate/Scale sliders were removed as dead; transform is done via the gizmo. Do NOT reproduce this pattern.

## PATCHING PITFALL (editing this single file with the `patch` tool)
The `patch` tool uses fuzzy matching and can silently leave a function with an EMPTY body or drop listeners when the `old_string` only partially spans the region. Live example this session: patching the 2D-builder section left `addShape(type) {` with no body and removed the slider `input` listeners, breaking the 2D builder until re-read + rebuilt.
- After ANY multi-line edit to this file, re-read the affected region with `read_file` and confirm what's actually there.
- Then extract `<script type="module">` and `node --check` it (catches empty-body functions / unclosed braces).
- Grep for duplicate listener wiring and for the IDs you removed (e.g. `pos-x`, `precision-controls`) to catch dangling `getElementById` calls.

## Integrating the studio into a Next.js / React host app
The single-file studio (CDN Tailwind + importmap three) is self-contained and iframe-safe. To surface it as a tab inside a Next.js app (this is how LunaV Studio shipped it):
- Copy the HTML into `public/studio/<name>.html` (Next serves `public/` at root → reachable at `/studio/<name>.html`). Do NOT import it as a module — it's plain HTML.
- Render with `<iframe src="/studio/<name>.html" className="h-full w-full border-0 bg-[#0b0e12]" />` inside a tab panel (`absolute inset-0` when active, `hidden` otherwise).
- Wire the tab in THREE places or it silently does nothing: (1) the `Tab` union type, (2) the nav `map()` entries, (3) the stage `div` (`className={tab === "studio" ? "absolute inset-0 z-10" : "hidden"}`). Concrete recipe in `references/embed-in-nextjs.md`.
- The studio pulls `cdn.tailwindcss.com` + `unpkg` three at runtime → needs network. For offline, inline the CSS / vendor the three module.

### Export is client-side — KEEP IT THAT WAY
The `Export to .GLB` button already writes to the USER'S DOWNLOAD FOLDER, not any backend (Blob + `link.download`). Verify a studio HTML is backend-free before embedding:
```
grep -ci "supabase\|r2-upload\|uploadToR2" <file>.html   # expect 0
```
If >0 the file was accidentally wired to a backend — revert. Do NOT "add Supabase export" to the studio; if a product wants the model persisted, upload the Blob from the HOST app (fetch the iframe blob / `postMessage` it), never by editing the studio's export to call R2.

### Pitfall: collapsed panel re-expands at desktop (sm: override)
A host panel whose collapsed class includes `sm:w-80` / `sm:rounded-2xl` will silently RE-EXPAND at ≥640px, and if the toggle is `sm:hidden` the collapse looks dead on desktop. Fix: the collapsed state must keep a thin width at ALL breakpoints (e.g. `w-10` with no `sm:w-*` override) and the toggle must NOT be `sm:hidden`. This was the real "3D Digital Twin right tab won't collapse" bug.

### Pitfall: collapsed panel still renders the full body (overflow-hidden clip ≠ unmount)
Even with the correct thin-width collapsed class, the panel can STILL look broken when collapsed if the body is only hidden by `overflow-hidden` clipping instead of being conditionally unmounted. Symptom: the collapsed state shows a thin rail, but the inspector controls / spatial toolbox / severity charts are still mounted *underneath* (clipped) — so it reads as a garbled/overlapping block, not a clean rail. That was the "3D Digital Twin collapse looks like a broken block" bug, confirmed by loading the user's screenshot through `vision_analyze` (the tool described a thin rail with content bleeding behind it). FIX: gate the ENTIRE panel body behind the open-state boolean, so the collapsed render path contains ONLY the thin reopen rail. A common error is wrapping only the FIRST sub-block (e.g. the model list) in `{open && (`, leaving the rest of the body mounted-but-clipped. Wrap from the first body element through the last (donut) in one fragment, or gate each top-level section with `open &&`.
```tsx
{open && (<>
  {/* models list, inspector controls, spatial toolbox, severity donut — ALL of it */}
</>)}
{/* thin reopen rail lives OUTSIDE the conditional = ONLY thing rendered when collapsed */}
{!open && (
  <button onClick={() => setOpen(true)} className="...thin rail...">Models ›</button>
)}
```
This matches the embedded single-file studio, which renders only its vertical `MODELS ›` handle when collapsed.

## Checklist
- [ ] Each generation wrapped in one `THREE.Group` named `generated-block`; `lastGeneratedBlock` tracked
- [ ] **2D Builder** `addShape()` also wraps in a block (do NOT add loose mesh to `aiGeneratedGroup`)
- [ ] Click selects leaf mesh; double-click selects whole block; shift-click multi-selects
- [ ] `cloneObject` clones materials (not shared)
- [ ] Duplicate clones whole block, offsets copy, re-selects first clone (never leaves tools detached)
- [ ] Curvature helper `.add` redirected into a per-generation block
- [ ] `cleanupAndCenter` runs per block, not on the whole group
- [ ] **Leak guards**: `updateShapeMesh` disposes old geometry+material before rebuild; Delete uses `disposeObj()` (traverse) for blocks
- [ ] **UI**: minimal toolbar (no Select All / Group / Ungroup / Duplicate Whole Model); transform via gizmo (Move/Rotate/Scale mode buttons + drag handles). Sliders were removed as dead — do NOT re-add. (Obsolete reference `references/visual-editor-sliders.md` — historical only.)
- [ ] `node --check` passes; no duplicate element IDs
- [ ] **Collapse sanity (when a collapse bug is reported)**: after fixing, confirm the COLLAPSED render path mounts ONLY the thin reopen rail — run `grep`/`search` for the body sections and verify they sit inside the open-state conditional, OR load a screenshot of the collapsed state through `vision_analyze` to confirm no content bleeds behind the rail. Two distinct collapse failure modes exist: (a) `sm:` override re-expands at desktop (see above), (b) body mounted-but-clipped by `overflow-hidden` (see "overflow-hidden clip ≠ unmount" above).
