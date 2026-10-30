# Webapp blank-canvas pitfall (three.js, localhost)

## Symptom
Open the page in a real browser → canvas is blank, no 3D, no errors in the
visible UI. (Do NOT dismiss as "headless GL flake" — that was a wrong excuse
in DTwin 2026-08-14; the user saw it blank in a LIVE browser.)

## Root cause found (DTwin 2026-08-14)
main.js referenced DOM ids that did NOT exist in index.html:
  JS used:  'card-title', 'card-body', 'card-close'
  HTML had: 'c-title',    'c-body',    'c-close'
`document.getElementById('card-close').onclick = ...` threw `TypeError:
cannot set onclick of null` at MODULE LOAD — before the animate() render loop
was ever scheduled. One null-ref before the loop = permanently blank canvas.

## Fix pattern
1. Make id references consistent HTML↔JS (search both for getElementById +
   id="..."). Guard any optional element: `const x = getElementById('x'); if (x) x.onclick = ...`.
2. Start the render loop (animate()) as early as possible, and keep DOM/touch
   binding AFTER it (or in try/catch) so a UI typo can never blank the 3D scene.
3. Hide the info card by default (class `hidden`) — only show on pin tap.
4. Add a `#status` pipeline line and ensure every getElementById target exists
   (a missing `#status` silently kills the panel too).

## Verify the fix is real
Headless Chrome on macOS reliably FAILS to create a WebGL context (swiftshader
→ "Cannot read properties of null (reading 'width')" in three.module.js). So:
- Do NOT use headless screenshots as proof of a WebGL app.
- Prove data wiring in Node (parse tags.json, compute pin positions).
- Ask the user to eyeball the REAL browser. "Done" = they see it on screen.
