# MindAR image-tracking WebAR — known bugs (learned 2026-08-22)

Browser marker-AR with MindAR (`mindar-image-aframe`) + A-Frame, for on-site
gazebo/structure overlay (LunaV `/ar/` pages).

## BUG — calling `startScanning()` after `start()` throws "is not functioning"
Symptom on the phone: `sceneEl.system.minder.image-system.startScanning is not functioning`.
Camera never opens; A-Frame reports "camera error".

Root cause: the official MindAR API is `arSystem.start()` ONLY. `start()` internally
begins scanning. If you ALSO call `arSystem.startScanning()` (or call it before `start()`
resolves), the controller isn't ready and throws. Seen in hand-rolled viewer/setup pages
that awaited `start()` then immediately called `startScanning()`.

FIX — call ONLY `start()`, never `startScanning()`:
```js
const sceneEl = document.querySelector('a-scene');
document.getElementById('startBtn').addEventListener('click', async () => {
  document.getElementById('startGate').style.display = 'none';
  try {
    await sceneEl.systems['mindar-image-system'].start(); // start() ALREADY scans
    // DO NOT call sceneEl.systems['mindar-image-system'].startScanning();
    setStatus('scanning — point at the marker');
  } catch (e) { setStatus('camera error: ' + e.message); }
});
```
The `startBtn` click IS the required user gesture (iOS Safari demands a tap before camera).

## BUG — `.mind` target 307-redirected to /login breaks loading
If the `.mind` target file is behind an auth gate (Next.js middleware, Vercel
Authentication), MindAR's fetch fails and the system never reaches a scannable state →
same "camera error". Verify every asset (including `.mind`) returns 200 with
`--max-redirs 0` (see vercel-prod-deploy-verification references/static-html-vercel-deploy.md
section 7). The HTML pages can load fine while the `.mind`/`.js` are gated — that's the
trap that produced the above error in the LunaV deploy.

## Notes
- MindAR `imageTargetSrc` accepts a relative path (`assets/card.mind`) — host the `.mind`
  locally, don't rely on a dead CDN (`@1.2.5/...card.mind` 404s; unversioned `gh/hiukim/mind-ar-js`
  works but pin a known-good copy).
- A-Frame + MindAR must be served over HTTPS for phone cameras (localhost excepted).
- `autoStart: false` is correct when you gate start behind a user tap; then call `start()`.
