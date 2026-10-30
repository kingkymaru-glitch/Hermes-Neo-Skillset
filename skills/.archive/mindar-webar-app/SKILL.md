---
name: mindar-webar-app
description: MindAR WebAR on Next.js/Vercel. Fixes iPhone camera stuck.
---

# MindAR WebAR App (marker-anchored, A-Frame, Next.js/Vercel)

Use when building a WebAR feature where a phone scans a printed marker and sees a 3D
model (GLB) overlaid on the real structure, with optional pose baking (align model to
site, save transform). Typical for inspection / digital-twin site overlays (e.g. LunaV
gazebo AR). Also use when an AR page loads but the camera "won't open" / "stuck" / throws
"startScanning is not functioning" on iOS.

## Architecture (proven pattern)
- Host AR pages as static HTML under `public/ar/` (viewer.html, setup.html, sheet.html)
  on the SAME domain as the app. Keep the app open as the "fresh browser"; open AR in a
  new tab so the app stays live.
- Vendor libs locally in `public/ar/assets/`: `aframe.min.js`, `mindar-image-aframe.prod.js`,
  `card.mind` (sample target), `card.png` (marker), `qrcode.min.js`. Never rely on a CDN that
  serves the `.mind` with the wrong MIME — the jsdelivr `/gh/` path 404s/breaks MindAR.
- MindAR `start()` already begins scanning — do NOT also call `startScanning()`.

## CRITICAL RULE 1 — imageTargetSrc MUST be on the <a-scene> tag at PARSE time
Assigning the target via `sceneEl.setAttribute('mindar-image', 'imageTargetSrc: ...')` INSIDE the
"start camera" click handler (after the system initialized) makes iOS never load the `.mind`.
Symptom: camera permission granted, then FREEZE / "stuck" / "startScanning is not functioning".
FIX: put it on the tag:
  `<a-scene mindar-image="imageTargetSrc: assets/card.mind; autoStart:false; uiScanning:no; uiLoading:no; uiError:no;">`
and in the start handler call ONLY `await sceneEl.systems['mindar-image-system'].start();`.
(See templates/known-good-ar.html.)

## CRITICAL RULE 2 — Never call startScanning() after start()
MindAR aframe's `start()` internally starts scanning. A second `startScanning()` throws
"sceneEl.system.minder.image-system.startScanning is not functioning". Remove it.

## CRITICAL RULE 4 — ALWAYS KEEP the `<a-camera>` element; NEVER remove it
The MindAR aframe samples REQUIRE an explicit `<a-camera>` inside `<a-scene>`:
  `<a-camera position="0 0 0" look-controls="enabled:false"></a-camera>`
This is MindAR's tracking reference camera. Removing it (a tempting "fix" for a black
screen) breaks detection entirely: the page shows a permanent "scanning" / "marker lost",
never fires `targetFound`, no model, no error — looks frozen. The KNOWN-GOOD template
(templates/known-good-ar.html) keeps it. If the screen is black WITH the camera present,
the real cause is almost always a DATA-layer blocker (Pitfall 5: the model RPC 404s), not
the camera element. (See references/mindar-pitfalls.md Pitfall 4 + the new Pitfall 6 on the
remove-`<a-camera>` regression.)

## CRITICAL RULE 5 — Supabase RPC: NO `eq.` prefix on the param
Calling a PostgREST RPC with `?share_token=*** — `eq.` is a table-filter operator, invalid for a
single-arg RPC, and 404s it (symptom: "load error: get_shared_project failed 404"). Pass the
token as a plain value: `?share_token=*** See references/mindar-pitfalls.md Pitfall 5.
If the app has `src/middleware.ts` gating auth, its matcher often excludes `.html` + images but
NOT `.js` / `.mind` / `.ico`. Those get 307-redirected to `/login`, so MindAR can't fetch the
`.mind` → camera error / stuck. The HTML pages still load (excluded), hiding the bug.
FIX: add the AR path + binary extensions to the matcher exclusion:
  matcher: ["/((?!_next/static|_next/image|favicon.ico|studio/|ar/|.*\\.(?:svg|png|jpg|jpeg|gif|webp|glb|obj|mind|ico|js|html?)$).*)"]
Also check the Vercel project "Deployment Protection" (Vercel Authentication) — it gates EVERY
request including static assets; disable it or add a `/ar/**` path exception.

## VERIFICATION — never trust `curl -L`
`curl -L` follows 307→/login→200 and reports 200 for a BLOCKED asset. Always verify with:
  curl -s --max-redirs 0 "https://host/ar/assets/card.mind"   # expect 200, NO "location: /login"
Use scripts/verify_ar_assets.sh (checks every /ar asset for redirect). Prefer grep over
awk when parsing `npx vercel ls --prod` output (field positions are unreliable).

## DEPLOY (Vercel auto-deploy)
- For this user's LunaV repo, the deploy webhook only fires when the commit author is
  kingkymaru@gmail.com. Commit with:
  git -c user.name=maru -c user.email=kingkymaru@gmail.com commit -m "..." && git push origin main
- After push, poll `npx vercel ls --prod` until status "Ready", then re-run the
  --max-redirs 0 check on the live URL.

## References
- references/mindar-pitfalls.md — exact error strings + fixes, with reproduction (Pitfalls 1-9 + the mobile-web-can't-zoom client-report strategy). Read this BEFORE each AR debugging session — most failures map to a known pitfall.
- templates/known-good-ar.html — minimal correct a-scene + start handler scaffold (KEEPS `<a-camera>`).
- templates/known-good-client-report.html — read-only 3D report scaffold (orbit viewer + clickable findings + QR); the CLIENT deliverable when field AR is too fragile (Pitfall/Strategy: mobile cameras can't zoom).
- references/debug-overlay.html — copy-in on-phone debug log + raw-camera test (ends the blind guess-fix loop; see Pitfall 7). Essential for surfacing Pitfall 8 (null-crash silent dead UI).
- scripts/verify_ar_assets.sh — assert all /ar assets serve 200 with no redirect.
