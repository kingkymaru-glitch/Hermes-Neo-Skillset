# MindAR WebAR — Pitfalls & Exact Fixes

## Pitfall 1 — `imageTargetSrc` set AFTER init → iOS "stuck"
- SYMPTOM: HTML + libs load; user taps "start camera"; permission granted; then NOTHING
  (freeze) or "startScanning is not functioning". Camera never engages.
- CAUSE: `<a-scene mindar-image="autoStart:false;...">` had NO `imageTargetSrc`. The target
  was assigned only inside the start-click handler via `setAttribute`, i.e. AFTER MindAR
  read its config at init. iOS never loads the `.mind` → `start()` waits forever.
- FIX: put `imageTargetSrc: assets/card.mind;` on the `<a-scene>` tag itself (parse time).
  In the handler call ONLY `await sceneEl.systems['mindar-image-system'].start();`.
- Reproduced on: iPhone Safari, LunaV AR Sheet "Open phone alignment" (setup.html).

## Pitfall 2 — double start → "startScanning is not functioning"
- ERROR TEXT: `sceneEl.system.minder.image-system.startScanning is not functioning`
  (or `...image-system.startScanning is not functioning`).
- CAUSE: code calls BOTH `start()` AND `startScanning()`. MindAR's `start()` already scans.
- FIX: remove the `startScanning()` call entirely.

## Pitfall 3 — middleware / Vercel protection 307-redirects `.mind`/`.js` to /login
- SYMPTOM: HTML pages return 200 but the page "camera errors". Asset requests silently
  fail. Looks like a genuine camera bug but it's a 307→/login.
- DETECTION: `curl -L` lies (follows redirect → 200). Use `curl -s --max-redirs 0` →
  you'll see `HTTP/2 307` + `location: /login` on `card.mind`, `.js`, `.ico`.
- CAUSE A: `src/middleware.ts` matcher excludes `.html` + images but NOT `.js`/`.mind`/`.ico`.
- FIX A: add `ar/` and binary exts to the negative-lookahead:
  `matcher: ["/((?!_next/static|_next/image|favicon.ico|studio/|ar/|.*\\.(?:svg|png|jpg|jpeg|gif|webp|glb|obj|mind|ico|js|html?)$).*)"]`
- CAUSE B: Vercel project "Deployment Protection" (Vercel Authentication) on, gating all
  requests including static files.
- FIX B: disable it, or add a `/ar/**` path exception in dashboard → Deployment Protection.

## Verification trap
- NEVER verify AR assets with `curl -L` (follows 307 to /login, reports 200).
- Use `curl -s --max-redirs 0 <url>` per asset; expect `HTTP/2 200` and NO `location` header.
- Prefer grep over awk when parsing `npx vercel ls --prod` (column positions unreliable).

## Live status messages to add
Make the AR pages print real errors instead of dying silently:
- `setStatus('camera error: ' + e.message)` in the start try/catch.
- `setStatus('load error: ...')` when fetching the GLB bundle fails.
- `setStatus('save failed: ...')` when the pose upsert fails.
This turns "stuck" into an actionable string the user can report back.

## Pitfall 4 — black screen WITH the camera present (detection may still work)
- SYMPTOM: taps start, grants camera, but the screen is BLACK where the live feed should be.
  Status may flip between "marker lost" and a load error as you point away/at the sheet —
  i.e. MindAR IS tracking, but the video isn't painted.
- CAUSE (most common): a DATA-layer blocker, not a video bug. When the marker is first
  acquired the page fetches the model bundle; if that RPC 404s (Pitfall 5: `eq.` prefix) the
  model never loads, so there is nothing for A-Frame to render on top of the video — and the
  canvas clears to opaque black. Fix the data layer (Pitfall 5) FIRST.
- CAUSE (genuine video issue, rarer): the A-Frame canvas is not transparent, covering the
  MindAR video (zIndex:-2 behind the canvas). FIX: ensure the scene clears transparent —
  add `alpha:true` to the renderer:
  `renderer="colorManagement:true, physicallyCorrectLights, alpha:true"`.
- IMPORTANT: The `<a-camera>` element is NOT the cause of a black screen. Do NOT remove it
  (see Pitfall 6). The known-good scene KEEPS `<a-camera position="0 0 0"
  look-controls="enabled:false">` and still shows the feed once the data layer is healthy.

## Pitfall 6 — REMOVING `<a-camera>` → detection dies (the regression trap)
- SYMPTOM: after "fixing" a black screen by deleting `<a-camera>`, the page gets STUCK:
  permanent "scanning — point at the marker" / "marker lost", NEVER fires `targetFound`,
  no sliders, no model, NO error shown. Feels like the camera hangs.
- CAUSE: the explicit `<a-camera>` is MindAR's tracking reference camera. MindAR's aframe
  build REQUIRES it to be present in the scene at parse time. Deleting it leaves MindAR with
  no camera to project tracking onto → it never acquires the target → silent permanent scan.
- FIX: RESTORE the `<a-camera>` element:
  `<a-camera position="0 0 0" look-controls="enabled:false"></a-camera>` inside `<a-scene>`.
- LESSON (this session, 2026-08-23): a black screen was mis-attributed to the `<a-camera>`
  and removing it produced a worse, silent failure. The original black screen was actually
  Pitfall 5 (model RPC 404). Diagnose with the debug overlay (Pitfall 7) before editing the
  camera element.

## Pitfall 5 — Supabase RPC called with `?share_token=eq.<token>` → 404
- ERROR TEXT: `load error: get_shared_project failed 404` (or `get_ar_sheet failed 404`),
  shown when the marker is first acquired (the page tries to fetch the model bundle).
- CAUSE: calling a PostgREST RPC with the param as a FILTER operator:
  `?share_token=eq.<token>`. `eq.` is a table-filter operator and is INVALID for an RPC that
  takes a single uuid argument — PostgREST returns 404 (or 400). The function signature is
  `get_shared_project(share_token uuid)` returning ONE json object, NOT a filterable table.
- FIX: pass the param as a plain query value, not `eq.`:
  `await fetch(`${SUPABASE_URL}/rest/v1/rpc/get_shared_project?share_token=${encodeURIComponent(token)}`, {headers})`
  (same for `get_ar_sheet`). Do NOT prefix the token with `eq.`.
- REPRO: this is reproducible headlessly — any Supabase RPC invoked with `?arg=eq.value` 404s
  for a single-arg scalar/object function. Drop the `eq.` and it resolves.

## Pitfall 7 — debug blind (no on-device signal) → guess-fix-test loop
- SYMPTOM: iOS failures arrive as "it's stuck" / "app not responding" / "camera won't open"
  with NO error. The agent can't reproduce on a headless box (no camera), so it patches,
  redeploys, the user retests, and the same vague symptom returns. Loop.
- FIX (shipped this session, proven to work): add an on-PHONE debug surface to the AR pages
  so the user's next report carries the exact failing step instead of "stuck":
  1. A live log panel ("debug" button, top-right) appended with `dbg('step', cls)` lines
     (green=ok, red=err), plus `window.onerror` / `unhandledrejection` handlers that push
     the real error into the log. Log every milestone: script loaded, a-scene loaded,
     start clicked, `calling start()…`, `start() resolved`, `targetFound`, `load error`.
  2. A **raw-camera test** button that calls `getUserMedia({video:{facingMode:'environment'}})`
     on a plain `<video>` — BYPASSES MindAR. If raw camera shows → hardware/permission OK and
     the hang is inside MindAR's `start()` (the debug log shows where). If raw camera ALSO
     fails → it's iOS permission/HTTPS, not our code.
  3. Gate `start()` on `sceneEl.hasLoaded` (await the `loaded` event with an 8s safety
     timeout) — calling `start()` before the scene is ready is a silent-hang source.
- WHY THIS ENDS THE LOOP: each retest now yields a precise string ("start FAILED: …" or
 "raw camera OK — hardware works") instead of "stuck", so the next fix targets the real
 failure. Template scaffold: see references/debug-overlay.html (copy into any AR page).

 ## Pitfall 8 — marker entity missing `id="target"` → null crash, silent permanent "scanning"
 - SYMPTOM: after every other symptom is fixed, the page "works" (camera OK, model may even
 load) BUT `targetFound` never fires → no slider/alignment panel, permanent "scanning —
 point at the marker", even though the debug log shows detection is happening.
 - ERROR (from the Pitfall 7 debug overlay, the ONLY way this surfaced):
 `WINDOW ERROR: TypeError: null is not an object (evaluating 'targetEl.addEventListener')`
 at the line where the script does `const targetEl = document.getElementById('target');
 targetEl.addEventListener('targetFound', …)`.
 - CAUSE: the marker entity was rewritten as `<a-entity mindar-image-target="targetIndex: 0">`
 WITHOUT `id="target"`. The script's `getElementById('target')` returns `null`, the
 `targetEl.addEventListener` throws at LOAD, and the throw is a top-level error that kills
 the rest of the script (including the `targetFound`/`targetLost` bindings) → detection
 still runs inside MindAR, but OUR overlay logic (slider, model show/hide, save) never binds.
 Distinct from Pitfall 6 (removing `<a-camera>`): here the camera works and the model may
 even appear, but the UI is dead because the binding script threw.
 - FIX (two parts):
 1. Give the marker entity the id the script expects:
    `<a-entity id="target" mindar-image-target="targetIndex: 0">`
 2. Bind defensively so a null can NEVER silently kill the script:
    `const targetEl = document.getElementById('target');
     if (!targetEl) dbg('!! #target element missing', 'err');
     else { targetEl.addEventListener('targetFound', …); targetEl.addEventListener('targetLost', …); }`
 - LESSON: a thrown top-level error in the inline `<script>` produces NO visible failure on
 desktop (the rest of A-Frame still runs) and a silent dead UI on mobile. The Pitfall 7 debug
 overlay is the ONLY thing that makes it visible. Always wrap element lookups that feed
 `addEventListener` in a null-guard when the id might be absent.

 ## Pitfall 9 — opaque page background hides the MindAR camera ("model in a box")
 - SYMPTOM: the model LOADS fine and tracks the marker, but it sits in a dark/empty "box" /
 environment instead of being overlaid ON the live camera feed. Camera feed not visible
 behind the model. (Different from Pitfall 4's BLACK screen — here the model renders, the
 camera just isn't showing through behind it.)
 - CAUSE: MindAR appends its camera `<video>` at `zIndex:-2` (behind everything). An opaque
 page background — `html,body{background:#0b0e14}` or any non-transparent `background` on
 the body/html — paints OVER that video, so you never see the camera; you only see the dark
 body with the 3D model floating in front of it ("a box"). The A-Frame canvas itself may be
 transparent, but the body behind it isn't.
 - FIX (make BOTH transparent so the camera shows through behind the model):
 1. `html,body{ … background:transparent; … }` (was `background:#0b0e14`).
 2. Ensure the `<a-scene>` clears transparent:
    `background="transparent: true"` on `<a-scene>` (+ the renderer already has `alpha:true`).
 - VERIFY: after the fix, pointing at the marker shows the live camera as the background with
 the model overlaid on top. If still boxed, check there isn't ALSO an opaque element (a
 full-screen `<div>` with a background, or a sky/environment inside the GLB) between the
 video and the canvas.
 - LESSON: the camera feed visibility is governed by page-level CSS opacity, NOT by MindAR or
 A-Frame internals. A dark theme on the body is the usual culprit. This is the standard,
 well-established correction for exactly this symptom.

 ## STRATEGY — mobile web cameras CANNOT zoom; field AR is fragile for clients
 - HARD LIMIT: on iOS Safari and Android Chrome WebAR, `getUserMedia` delivers a FIXED-LENS
 stream and MindAR has NO digital-zoom control over it. A small marker 2m away is
 low-resolution in the stream → jitter, then track loss, sometimes unusable. NO code change
 fixes this — it is a platform constraint, not a bug. (Confirmed this session 2026-08-23:
 user on iPhone 15 Pro Max + Samsung S22 Ultra, web-based camera, could not hold a marker
 at standoff distance → jitter / non-usable.)
 - IMPLICATION for product design: don't make the CLIENT deliverable depend on field AR.
 Marker standoff, slider sensitivity on a small phone, and lighting all degrade the
 experience. The reliable client value — "see where the defects are on this structure" —
 is delivered far more robustly by a READ-ONLY 3D REPORT opened in a normal browser:
 orbit the twin, click a finding → camera flies to / highlights the node. No camera, no
 marker, no standoff, any device, any distance.
 - RECOMMENDED SHAPE: keep marker-anchored field AR as an INSPECTOR-only power tool (for the
 person who physically aligns + saves the pose at site), and ship a read-only client report
 as the client-facing deliverable. The report is the same data (GLB + node markers) rendered
 in an orbit viewer instead of a camera overlay. See templates/known-good-client-report.html
 for a working scaffold that reuses `LUNAV_AR.loadModel(mount, modelDef, setStatus)` (which
 spawns node markers as children of the model mount) with `aframe-extras` `orbit-controls`,
 THREE.Box3 autoframe on `model-loaded`, a clickable findings list, and a shareable QR.
 - The field AR "Open phone alignment" flow stays valid for the inspector who must align the
 model to the real structure at site (per the discuss-first decision: field AR = inspector,
 read-only report = client).
