---
name: webar-image-target-streaming
description: WebAR image-target streaming via MindAR + WebRTC in browser.
---

# WebAR image-target streaming (browser-only, no app install)

## When to use
Any "point phone at a marker and see live <source> floating in AR, no app install"
build. Triggers: WebAR, MindAR, image target, marker AR in browser, stream Mac
screen to phone AR, PeerJS broadcaster + QR, getDisplayMedia to AR plane,
A-Frame video texture.

## Architecture (proven shape)
1. `index.html` (desktop broadcaster): `getDisplayMedia({video:true,audio:false})`
   → PeerJS instance → on `open`, render QR encoding
   `https://<host>/viewer.html?peer=<PEER_ID>` → on incoming `call`, `call.answer(stream)`.
2. `viewer.html` (mobile): parse `?peer=`, call the peer, bind `call.on('stream')`
   to a hidden `<video id="mac-screen" autoplay playsinline muted>`.
3. A-Frame + `mindar-image-aframe`; inside `<a-entity mindar-image-target="targetIndex:0">`
   an `<a-plane width="1" height="0.5625" material="src:#mac-screen; shader:flat">`.
4. One static server (Express `server.js` or `python3 -m http.server 8080`) serving both pages.
5. HTTPS mandatory for camera + WebRTC on mobile: `ngrok http 8080` (single URL,
   same origin for both pages) or `mkcert` local certs.

## Pitfalls (raise these BEFORE coding)
- MindAR needs a COMPILED `.mind` target file, not a raw image. Start with MindAR's
  official example target so it works out of the box; swap a custom compiled target later.
- iOS Safari won't paint a video texture without a user gesture. Add a "Tap to start"
  overlay in `viewer.html` that calls `video.play()`.
- `playsinline` + `muted` are non-optional on iOS.
- Peer ID changes per session → QR must be regenerated per session, never hardcoded.
- PeerJS defaults to the public cloud broker: fine locally, but NOT offline-capable.
  Self-host the `peer` server for field builds (see founder-workflow offline-first rule).
- Serve broadcaster and viewer from the SAME origin/tunnel, or the QR points at an
  http host and media permissions die.

## Workflow rule for MARU
He pastes a full spec and says "no code yet, confirm you know my narrative".
Reply with: (1) the story in user terms, (2) the numbered mechanical chain,
(3) the constraints held, (4) the 2–3 real decisions (target file, iOS tap gate,
PeerJS broker). Then STOP and wait. Do not scaffold.

## DEPLOYMENT / SCRIPT HOSTING — MindAR CDN is broken, host locally (burned 2026-08-22)
The MindAR script CDN paths that tutorials cite are DEAD or serve a wrong MIME type:
- `https://cdn.jsdelivr.net/gh/hiukim/mind-ar@1.2.5/dist/mindar-image-aframe.prod.js`
  → 404, AND the `@1.2.5`-pinned `cdn.jsdelivr.net/gh/hiukim/...` path serves
  `Content-Type: text/plain` with `X-Content-Type-Options: nosniff` → the browser
  REFUSES to execute it ("Failed to load resource: 404" + "Refused to execute …
  because X-Content-Type-Options: nosniff was given and its Content-Type is not a
  script MIME type"). This is the #1 WebAR gotcha.
- FIX: host aframe + mindar locally. From the npm tarball
  (`registry.npmjs.org/mind-ar/-/mind-ar-1.2.5.tgz`) extract
  `dist/mindar-image-aframe.prod.js` (1.76MB, self-contained incl. compiler) and use
  any `aframe.min.js` (1.3MB) → drop both in `assets/` and reference
  `assets/mindar-image-aframe.prod.js` + `assets/aframe.min.js` in the HTML. Zero CDN.
- The SAMPLE `.mind` target (`card.mind` 257KB) and `card.png` ARE still fetchable:
  `raw.githubusercontent.com/hiukim/mind-ar-js/master/examples/image-tracking/assets/card-example/`
  (the unversioned `cdn.jsdelivr.net/gh/hiukim/mind-ar-js/...` also works — only the
  pinned `@1.2.5` path is dead). Grab both, host locally as `assets/card.mind` +
  `assets/card.png`, and point the default `imageTargetSrc` / `TARGET_SRC` at
  `assets/card.mind`. Good enough for a first field test; compile a per-project target later.
- COMPILING a custom `.mind`: the public API is
  `MINDAR.IMAGE.ImageTargets.compile([dataUrl], {printCompilationProgress:()=>{}})`
  (returns an ArrayBuffer) — runs in a REAL BROWSER, not Node (Node eval exposes
  `MINDAR.IMAGE.Compiler` but not `ImageTargets`; and `Compiler.compileTrack` needs
  canvas/WebGL). You CANNOT drive the compile from the agent's cloud browser tool
  because that tool BLOCKS private/localhost URLs, so it can't reach a local
  `python3 -m http.server` page. Practical path for a custom marker: host a tiny
  compiler page on a PUBLIC Vercel temp deploy, run it there, capture the base64
  output, then tear the temp project down. (See `references/mindar-deploy.md`.)
- Full asset-fetch recipes + the verified-good raw URLs + the custom-compile walkthrough
  are in `references/mindar-deploy.md` (read it before any MindAR deploy).
- Any other third-party script (e.g. qrcodejs) — also host locally in `assets/` to
  stay fully offline/field-ready. Add a local `favicon.ico` + `<link rel=icon>` to
  kill the harmless `favicon.ico 404`.
- Same-domain rule: ship WebAR pages under the host app's `public/ar/` so they deploy
  on the SAME domain (one deploy, no second project). Deep-link via relative
  `/ar/viewer.html?...` opening a new tab. See lunav-family-frontend.
- VERIFY AFTER BUILD IS READY: right after a `vercel --prod` push, the new static files
  (HTML/PNG) can 404 for ~30s while the deploy is in `Building` state — re-curl after
  `npx vercel ls --prod` shows the latest deploy `● Ready` before declaring success.
- LUNAV DEPLOY WEBHOOK: the rover-r-3d/lunavsolution auto-deploy only fires when the git
  commit AUTHOR is `maru <kingkymaru@gmail.com>`. Commit with
  `git -c user.name=maru -c user.email=kingkymaru@gmail.com commit …` (or set locally)
  or the push will land without triggering a deploy.
