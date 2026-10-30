# DTwin web viewer — blank canvas root-cause checklist

Owner symptom: user says "I see nothing" / localhost is blank. The HTML
text overlays (top bar, "Placeholder hologram", status pill) still render —
only the 3D `<canvas>` is empty. That separation is the diagnostic key: the
overlays are plain HTML/CSS, so if THEY show, the JS module at least loaded
far enough to not hard-abort; if even overlays are missing, the module aborted
before first paint.

## Four distinct blank causes (all hit in one session)
1. **Canvas element missing from DOM (THE usual real-browser blank).**
   main.js does `getElementById('view')` and passes it to `new THREE.WebGLRenderer`.
   If `index.html` has no `<canvas id="view">`, that returns `null` → three.js
   creates a DETACHED canvas and renders to it → nothing visible, no error.
   FIX: add `<canvas id="view"></canvas>` and CSS `position:fixed; inset:0;
   width:100%; height:100%; z-index:1;` (UI overlays sit at z-index 10).

2. **getElementById returns null → throw before render loop.**
   Any top-level `document.getElementById('WRONG-ID').onclick = ...` or
   `.textContent = ...` throws → module aborts → render loop (scheduled at
   the very end) never runs → blank. IDs must match exactly between HTML and JS.
   FIX: align ids; guard every DOM write (`const el = getElementById('x'); if(el) el.textContent=...`).
   Start the render loop BEFORE any DOM-binding code so a typo can't blank the scene.

3. **CDN module 404 / network-block silently aborts the ES module.**
   main.js `import * as THREE from 'three'` resolves via an <importmap>. If the
   importmap points at a wrong CDN path (e.g. typo `gaussian-splat-3d` vs
   `gaussian-splats-3d`) or the network blocks jsdelivr, the WHOLE module fails
   to load → blank, often with no obvious console error unless you look.
   FIX: vendor deps locally. Copy three.module.js, OrbitControls.js, and the
   gaussian-splat viewer module into web/vendor/ and point the importmap at
   `./vendor/...`. Now the app is 100% offline/local-first and CDN flake can't
   blank it. (Verified: three@0.160.0 module + OrbitControls import only `three`.)

4. **WebGL-catch re-throw (env, not app).**
   `new THREE.WebGLRenderer` throws when no GL context exists (e.g. headless).
   The catch block at the time did `getElementById('card-body')` (wrong id,
   should be `c-body`) → second throw hid the real error. FIX: guard the catch
   DOM write too. This is environmental in headless; on a real browser GL exists
   so it won't fire.

## Verification reality (IMPORTANT — do not fake this)
- **Headless Chrome on this Mac CANNOT init WebGL** (tried `--use-gl=angle
  --use-angle=swiftshader`, `--use-gl=swiftshader`, `--use-angle=gl/vulkan`,
  `--enable-unsafe-swiftshader` — all yield a null GL context → three throws
  `reading 'width' of null`). So headless screenshots cannot prove a splat
  renders. Do NOT claim "verified" from a headless screenshot of a WebGL app.
- **Rule (MARU): "done" = visibly on screen in a REAL browser, not built.**
  Prove WebGL apps by: (a) static checks — served HTML contains the canvas,
  served JS has no null-DOM writes, module files return HTTP 200; (b) add an
  on-screen error overlay (window 'error' + 'unhandledrejection' listeners that
  paint the message into a fixed div) so any runtime failure shows as TEXT the
  user can read back; (c) ask the user to hard-refresh (Cmd+Shift+R) and report
  what they see. A red error box on their screen is the real diagnostic.
- Useful non-GL checks that DO work headless: confirm the module graph loads
  with zero `Uncaught`/import errors (`--enable-logging=stderr` + grep), confirm
  served files return 200 via curl, and validate the .ply schema (vertex count,
  property names f_dc_0/opacity/scale_*/rot_*).

## On-screen error overlay (copy into index.html)
```html
<script>
  function showErr(msg){
    let d=document.getElementById('err');
    if(!d){d=document.createElement('div');d.id='err';
      d.style.cssText='position:fixed;left:12px;bottom:12px;max-width:90vw;z-index:9999;background:#3a0d0d;color:#ffb4b4;font:12px/1.4 monospace;padding:10px 12px;border:1px solid #ff6b6b;border-radius:8px;white-space:pre-wrap';
      document.body.appendChild(d);}
    d.textContent='ERROR: '+msg;
  }
  addEventListener('error',e=>showErr((e.message||e.error||'script error')+(e.filename?(' @ '+e.filename+':'+e.lineno):'')));
  addEventListener('unhandledrejection',e=>showErr((e.reason&&e.reason.message)||e.reason||'promise rejection'));
</script>
```
