# LunaV Studio — reproduced bug recipes (condensed)

File: `~/Downloads/lunav_studio_safe.html` (single-file Three.js + Tailwind-CDN 3D studio, inline `<script type="module">`, no build step).

## Bug 1 — Module abort when a removed control is still referenced (load-time crash)
- **Trigger:** Remove the `Generation Mode` `<select id="gen-mode">` from the HTML, but leave these JS lines:
  - `document.getElementById('gen-mode').addEventListener('change', ...)` (top level)
  - `const modeRaw = document.getElementById('gen-mode').value;` (inside generate handler)
- **Symptom:** `getElementById('gen-mode')` returns `null`; calling `.addEventListener` on null THROWS at module load. Because it's top-level, the exception aborts the entire `<script type="module">`, so every listener defined afterward (Generate, Reset, Rect/Circle/Sphere Draw, Delete) silently never attaches. User reports "all buttons dead / can't draw anything."
- **Fix:** Remove the `gen-mode` listener block AND replace the `.value` read with `const mode = autoDetectMode(prompt);` (mode is now chosen automatically by the AI from prompt keywords).
- **Detection:** `python3 scripts/verify_inline_js.py <file>` now auto-reports `DANGLING_DOM_IDS` for `gen-mode` because no `id="gen-mode"` exists in HTML.

## Bug 2 — Button rename/replace mismatch (drawing broken)
- **Trigger:** Swap a Polygon button for a Sphere button in HTML only:
  - HTML changed to `<button id="add-sphere">Sphere</button>`, but
  - the listener still read `document.getElementById('add-poly').addEventListener('click', () => addShape('poly'))`, and
  - `createParametricShape(type, params)` had no `sphere` branch (only rect/circle/poly).
- **Symptom:** Clicking Sphere does nothing (listener targets a non-existent id; even if fixed, the branch is missing so it falls through to extrude logic / no mesh).
- **Fix (matched edit — three parts):** (1) HTML id `add-sphere`; (2) listener `getElementById('add-sphere')` → `addShape('sphere')`; (3) add a `sphere` branch in `createParametricShape` returning a `THREE.SphereGeometry(radius, 32, 24)` mesh with `userData = { isParametric: true, shapeType: 'sphere', params }`.
- **Note:** Bug 2 was masked by Bug 1 until the module-abort was fixed; then Bug 2 surfaced independently.

## Lesson pattern (apply on every UI removal/edit in this file)
- Removing a control = delete markup AND every JS reference (listener + any `.value`/`.textContent` read). Run `verify_inline_js.py` after.
- Renaming/replacing a button = change markup id + listener id + handler branch as ONE matched edit.
- If MANY unrelated buttons die at once, suspect a top-level load-time throw (module abort), not per-button bugs.
