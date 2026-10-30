# AR subsystem — MindAR + A-Frame pose stabilization

## Where it lives
- Repo: `~/Documents/ss-rover-cloud` (= GitHub `kingkymaru-glitch/lunavsolution`; the
  local folder name is unchanged from the old "ss-rover-cloud" name).
- Files: `public/ar/ar-core.js` (shared core), `public/ar/viewer.html` (client/visitor
  AR), `public/ar/setup.html` (owner on-site alignment), `public/ar/report.html`
  (non-AR report page). Served at `https://lunavsolution.vercel.app/ar/...`.
- Stack: A-Frame (`assets/aframe.min.js`) + MindAR (`assets/mindar-image-aframe.prod.js`),
  vanilla JS. **No build step** — these are static files; `npm run build` does NOT
  typecheck them. Verification is manual/served (see bottom).

## Shared DOM contract (after stabilization)
```
<a-scene>
  <a-entity id="target" mindar-image-target="targetIndex: 0"></a-entity>   <!-- bare sensor; MindAR drives this raw -->
  <a-entity id="modelAnchor">                                               <!-- scene-level display root; stabilizer owns it -->
    <a-entity id="modelMarkerLocal"></a-entity>                             <!-- marker-relative wrapper; carries stored pose offset -->
  </a-entity>
  <a-camera position="0 0 0" look-controls="enabled: false"></a-camera>
</a-scene>
```
- GLB + node markers load into `#modelMarkerLocal` (call `LUNAV_AR.loadModel(modelLocal, ...)`).
- `#modelAnchor` is a SIBLING of `#target`, never a child — this is the whole fix.

## Root cause of jitter + vanish (and why decoupling fixes it)
Originally `#modelAnchor` was a CHILD of `#target`. MindAR hard-sets `#target`'s
object3D pose every frame (raw, noisy → visible shake) and HIDES `#target` on
`targetLost` (→ the model instantly vanishes when the marker leaves frame).
Fix = decouple: `#target` stays a bare sensor; a separate `#modelAnchor` is smoothed
toward it.

## `API.enableStabilizer(opts)` — added to ar-core.js
```
opts = { sceneEl, targetEl, anchorEl,
         posSmooth=0.25, rotSmooth=0.30, holdMs=800,
         maxJumpPos=0.4, maxJumpAng=0.6 }
```
Per `tick`:
1. Read `#target` world matrix → target pos/quat. (In these pages `#target` is a direct
   child of `<a-scene>`, so world == local — no parent transform to worry about.)
2. If not lost: first accepted frame SNAPS (don't lerp from a stale pose); afterwards
   accept the target pose only if `pos.distanceTo(accepted) <= maxJumpPos` AND
   `quat.angleTo(accepted) <= maxJumpAng` — this is the **confidence gate** (see below).
3. Lerp `anchorEl.position` toward accepted (factor `posSmooth`),
   slerp `anchorEl.quaternion` (factor `rotSmooth`) → frame noise averages out.
4. `targetLost`: set `lost=true`, record `lostAt`; keep `#modelAnchor` VISIBLE until
   `now - lostAt > holdMs`, THEN hide. So brief loss = freeze + hold, not vanish.
5. `targetFound`: re-acquire → `firstFrame=true` (snap next tick), `lost=false`, show.

## KEY FACT — MindAR exposes NO confidence value
Verified: `grep -o -i "confidence" assets/mindar-image-aframe.prod.js` → **0 hits**.
So the brief's "confidence gate" is implemented as **motion-consistency gating**
(reject pose spikes/detection flips), NOT a real field. Do NOT gate on a `.confidence`
property — it doesn't exist. If you later see a `confidence` arg, re-grep the actual
bundle before trusting it.

## setup.html DOES use the stabilizer — in "exact tracking" mode
PITFALL (found 2026-08-24): when the display root `#modelAnchor` was decoupled from
`#target` for viewer smoothing, `setup.html` was left with NO driver on `#modelAnchor` —
so the model stopped tracking the printed marker and floated at a fixed screen spot.
That made the owner's sliders feel disconnected from the real structure.

FIX: enable the stabilizer in `setup.html` too, but at factor **1.0 / holdMs 0** with the
confidence gate DISABLED (`maxJumpPos: 999, maxJumpAng: 999`). At factor 1.0 the anchor
snaps to the raw marker pose every frame (exact follow, no lag), and `holdMs:0` hides on
loss instead of freezing. This restores 1:1 marker tracking for alignment. The smoothing
(0.25/0.30/800) stays viewer-only.

```js
// setup.html — exact tracking (no smoothing, no gate)
LUNAV_AR.enableStabilizer({
  sceneEl, targetEl, anchorEl: modelAnchor,
  posSmooth: 1.0, rotSmooth: 1.0, holdMs: 0,
  maxJumpPos: 999, maxJumpAng: 999
});
```
- `loadModel` targets `#modelMarkerLocal` in BOTH pages (unchanged).
- Sliders still write `#modelMarkerLocal.object3D` directly via `applyPose()` (marker-relative
  offsets). The stabilizer drives `#modelAnchor` (the world transform from the marker);
  the two compose, so slider offsets sit relative to the live marker — correct.

## `API.enableManipulator(opts)` — multi-touch alignment (SETUP ONLY)
Added to `ar-core.js` 2026-08-24. Lets the owner align the model on a phone/tablet by hand
instead of fiddling sliders:
- **1-finger drag** → move the model on the marker's ground plane (X/Z offsets)
- **2-finger pinch** → uniform scale (clamped `minScale`..`maxScale`, default 0.02..50)
- **2-finger twist** → yaw (heading) in degrees
```js
LUNAV_AR.enableManipulator({
  sceneEl, markerEl: modelAnchor, modelLocal,
  getPose: () => pose, applyPose, syncUI, active: () => true
});
```
Mechanics:
- Uses Pointer Events on the A-Frame `<canvas>` with `touch-action:none` + `preventDefault`
  so iOS/Android don't scroll/zoom the page instead of moving the model.
- Drag: raycast the touch point onto a horizontal plane at the model's current world Y;
  delta in world space → rotated by the marker's inverse world-quaternion → marker-relative
  X/Z. So movement is intuitive regardless of how the phone is held.
- `gesture` baseline resets whenever finger count changes (down/up) — avoids jumps when a
  second finger lands.
- Writes the SAME `pose` object the sliders use; pass `syncUI` to push gesture results back
  into the slider thumbs (two-way sync). Saved alignment is identical either way — no schema
  change. Height (Y), pitch, roll stay slider-only (twist covers the main rotation).
- **Vertical-wall sheets:** NOT implemented. Drag maps to a horizontal plane only (the
  gazebo-on-ground case). The `planeSeg` horizontal/vertical toggle exists in the UI but the
  manipulator ignores it. Add a vertical-plane branch in `groundUnder` when needed.
- **Viewer stays read-only:** manipulator is wired in `setup.html` ONLY. `viewer.html` gets no
  touch input — visitors see the smoothed, hold-on-lost model with no editing.

## Slider toggle (touch-first)
`setup.html` hides `#panel` by default (`style="display:none"`) and shows a "Sliders" button
(top-right) that toggles it. Touch is the primary alignment input; sliders are fine-control.
To flip defaults: remove `display:none` on `#panel` and set `slidersOpen=true` initially.

## Verification (no headless browser on MARU's Mac — no playwright/puppeteer)
- `node --check public/ar/ar-core.js` for JS syntax.
- Serve: `python3 -m http.server 8753 --directory public/ar` (background), `curl`
  files for HTTP 200.
- Static invariant grep:
  - bare `#target` (no `modelAnchor` child) in both pages
  - `loadModel(modelLocal, ...)` in both
  - `enableStabilizer` present ONLY in viewer.html
  - NO `modelAnchor.object3D` writes in setup.html
- Confirm LIVE after push (Vercel deploy lags ~30–60s):
  `curl -s https://lunavsolution.vercel.app/ar/ar-core.js | grep enableStabilizer`
  and `.../ar/viewer.html | grep modelMarkerLocal` → both non-zero.
- CANNOT verify on-device feel (model not shaking when phone is still; hold-then-fade on
  marker loss) from CLI — that needs a phone scan. Tune `posSmooth`/`rotSmooth`/`holdMs`
  if the hold window feels too short/long.

## Deploy
`git push origin main` auto-deploys to Vercel (`public/ar/` → `/ar/`). Commit as
`kingkymaru <kingkymaru@gmail.com>` (webhook expects that author).
