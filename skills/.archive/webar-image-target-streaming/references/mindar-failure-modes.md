# MindAR + A-Frame runtime failure modes (field-tested 2026-08-23, LunaV AR Sheet)

Symptoms below were each hit live on iPhone Safari and root-caused. Each entry:
SYMPTOM -> ROOT CAUSE -> FIX. Apply in order when an AR page "renders but is broken".

## 0. On-phone debug overlay FIRST (do this before guessing)
Add a `dbg(msg, cls)` logger that writes a timestamped, color-coded line to a
fixed panel, call it at every lifecycle step (script loaded, scene loaded, start
clicked, start() resolved/rejected, targetFound, targetLost, bundle fetched,
model loaded, any catch). Add a `raw camera test` button that calls
`getUserMedia` DIRECTLY (bypassing MindAR) and paints a `<video>`. This isolates
"camera hardware/permission dead" from "MindAR init hangs". A WINDOW ERROR with no
on-screen error = a top-level throw in the inline script; the overlay catches it.
See `references/ar-debug-overlay.md` for the snippet. This ended a 6-round blind
fix loop in one test.

## 1. Permanent "scanning", no model, no slider, no error
SYMPTOM: status says scanning; pointing at the marker never fires targetFound;
sliders never appear; nothing in the console except maybe a WINDOW ERROR.
ROOT CAUSE (the one that actually bit): the `mindar-image-target` entity had NO
`id="target"`. The inline script did `getElementById('target')` -> `null`, then
`null.addEventListener('targetFound', …)` threw a WINDOW ERROR at load, killing
the rest of the script (slider bindings, model load) silently.
FIX: give the entity `id="target"`:
  <a-entity id="target" mindar-image-target="targetIndex: 0">
Wrap the two `addEventListener` calls in `if (targetEl) { … }` so a missing id can
never silently kill the script again.

## 2. Black screen where the camera should be (but marker detection "works")
SYMPTOM: top-right shows "marker lost / point camera at the sheet" (so MindAR is
running) but the screen is black, no camera image.
ROOT CAUSE: a rogue explicit `<a-camera>` in the page made A-Frame draw an opaque
black scene OVER the MindAR video. MindAR injects its own camera and renders the
video behind the A-Frame canvas; an explicit `<a-camera>` competes and paints black.
FIX: REMOVE the explicit `<a-camera>`. If you DO keep one (official example uses
`<a-camera position="0 0 0" look-controls="enabled: false">`), never combine it
with an opaque background. NOTE: removing `<a-camera>` is NOT what fixed the later
"model in a box" — see #4. Don't remove it to chase a black screen unless you've
confirmed the scene is otherwise transparent.

## 3. 404 on get_shared_project / get_ar_sheet (or any RPC) at runtime
SYMPTOM: "load error: get_shared_project failed 404" when the marker is found.
ROOT CAUSE: calling the RPC with a PostgREST TABLE-FILTER operator:
  ?share_token=eq.<UUID>   <- WRONG
`eq.` is a table-row filter, invalid for an RPC that takes a single uuid argument.
Returns 404, which blocks the model from ever loading.
FIX: call the RPC with a plain param:
  ?share_token=<UUID>
(Build the URL with `?share_token=${encodeURIComponent(token)}`, no `eq.`.)

## 4. Model loads but sits "in a box" — camera feed NOT visible behind it
SYMPTOM: the GLB appears, but over a dark/empty background, not over the live camera.
ROOT CAUSE: an OPAQUE page background (`html,body{background:#0b0e14}`) paints over
MindAR's camera `<video>`, which it appends at `zIndex:-2` (behind everything).
The opaque body hides the video, so you see the model floating on a dark "box".
FIX: make the page transparent AND the A-Frame canvas transparent:
  html,body{ … background:transparent; … }
  <a-scene … renderer="colorManagement:true, physicallyCorrectLights, alpha:true"
           background="transparent: true">
`alpha:true` on the renderer is required; `background="transparent:true"` forces the
clear alpha to 0. Without BOTH the camera stays hidden.

## 5. Scene init hangs / start() never resolves
SYMPTOM: tap start, button does nothing, status stuck on "starting camera…".
ROOT CAUSE: `imageTargetSrc: assets/card.mind` was injected AFTER the scene started,
or `start()` was called before `sceneEl.hasLoaded`. MindAR needs the target src at
PARSE time and a loaded scene before `start()`.
FIX: declare `imageTargetSrc` on `<a-scene>` in the static HTML. Gate the start
button: `if (!sceneEl.hasLoaded) await new Promise(r => sceneEl.addEventListener('loaded', r));`
then `await mindarSystem.start()`.

## 6. Bundle (RPC) re-fetched on every jittery targetFound
SYMPTOM: debug log shows fetchBundle called 20x/min during marker jitter.
ROOT CAUSE: `targetFound` handler re-fetched the Supabase bundle on every fire.
FIX: hoist to once-per-session with a `let bundleLoaded = false;` guard (reset it to
false only on load error so a retry is possible). If `!MODEL_ID` this is a test-only
build — skip fetch and set the flag so the handler is a no-op thereafter.

## Verifying a fix is live (Vercel static)
`npx vercel inspect --wait <url>` was BLOCKED this session. Instead: after `git push`,
poll `curl -s --max-redirs 0 -H "Cache-Control: no-cache" "<url>?c=$i"` in a loop and
grep for the fix string (e.g. `id="target"`). Vercel shows the deploy "Ready" but static
HTML can lag ~30s; a `?c=<n>` query-string busts the CDN cache. Only declare success when
the served bytes contain the change.
