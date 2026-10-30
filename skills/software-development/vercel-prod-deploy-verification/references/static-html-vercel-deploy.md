# Static HTML → Vercel deploy (no framework) — full transcript

Context: deploy `~/webarr-screen` (plain `index.html` + `viewer.html` + `server.js` + `vercel.json`, zero build step) to real HTTPS so random phone visitors can open a WebAR viewer. Validated 2026-08-22.

## 1. Login — device code, NOT a popup
```
$ cd ~/webarr-screen && npx --yes vercel@latest login --github
Vercel CLI 59.3.0 (Node.js 24.18.0)
WARNING! The following flags are deprecated: --github
> Visit https://vercel.com/oauth/device?user_code=PCLQ-SCCZ
Waiting for authentication...
  Congratulations! You are now signed in.
```
Hand `https://vercel.com/oauth/device?user_code=PCLQ-SCCZ` + code `PCLQ-SCCZ` to user; they approve in browser; CLI auto-detects.

## 2. FIRST deploy FAILS — `framework:"static"` is invalid
Initial `vercel.json` had `"framework": "static"`. Deploy error:
```
"status": "error", "reason": "deploy_failed",
"message": "Invalid request: `projectSettings.framework` should be equal to one of the allowed values
\"container, blitzjs, nextjs, gatsby, ... vite, ... node, go, services, mastra, \"."
```
Note `"static"` is NOT in the allowed enum. FIX — drop `framework` (and the deprecated `name` prop), keep only:
```json
{ "outputDirectory": ".", "rewrites": [{ "source": "/(.*)", "destination": "/$1" }] }
```
Also remove `"name"` from `package.json` (the `--name` flag is deprecated too).

## 3. Deploy succeeds → build URL
```
$ npx --yes vercel@latest deploy --prod --yes
...
"message": "Deployment webarr-screen-4op1p4psi-rover-r-3d.vercel.app ready."
```
Project auto-named under team `rover-r-3d` (from `innovatedmaru-2409` account).

## 4. Verify on the DEPLOYMENT URL (NOT a guessed slug)
```
$ curl -sL -o /dev/null -w "viewer.html HTTP %{http_code}\n" \
    https://webarr-screen-4op1p4psi-rover-r-3d.vercel.app/viewer.html
viewer.html HTTP 200
$ curl -sL -o /dev/null -w "index.html  HTTP %{http_code}\n" \
    https://webarr-screen-4op1p4psi-rover-r-3d.vercel.app/index.html
index.html  HTTP 200
```
★ GOTCHA — `https://webarr-screen.vercel.app` 404'd on `viewer.html`. That slug belongs to a STALE project on ANOTHER team (`innovatedmaru-2409`), NOT our `rover-r-3d` deploy. Symptom: `webarr-screen.vercel.app/index.html` → 200 (cached old index) but `/viewer.html` → 404. Don't chase this — always verify against the deployment URL from `vercel ls --prod`.
★ `vercel domains add webarr-screen.vercel.app` → `invalid_domain` (held by other team). `vercel domains add webarr-screen.rover-r-3d.vercel.app` → also `invalid_domain` (team default region alias isn't manually addable). SKIP domain aliasing; the deployment URL is stable + public.

## 5. Re-deploy after edits
```
$ npx --yes vercel@latest deploy --prod --yes | grep -oE "https://[a-z0-9-]+\.vercel\.app"
https://webarr-screen-bxj2flzie-rover-r-3d.vercel.app
```
Deployment URL hash increments each deploy (`...-4op1p4psi-...` → `...-bxj2flzie-...`); old URL may later 404. Get current via `npx vercel ls --prod`. No Git integration, no webhook, no build step — every `npx vercel deploy --prod --yes` is live within seconds.

## 6. iOS Safari video-paint gotcha (WebAR side)
If you add any `<video>` that paints a MediaStream: set `playsinline muted webkit-playsinline` or iOS Safari shows a black/flashing box. Prefer DOM overlays (scrollable report panels) over video compositing on iOS. MindAR/A-Frame manage their own camera element, so this only bites custom video elements.

## 7. VERIFY WITH `--max-redirs 0`, NOT `curl -L` (in-app static assets behind auth)
When the static app lives UNDER a Next.js app (e.g. LunaV's `/ar/` WebAR pages served from `public/ar/`), a Next.js `middleware.ts` can 307-redirect any asset it isn't told to exclude to `/login`. `card.mind`, `.js`, `.ico` get gated; the `.html` pages (often excluded) load fine. If you verify with `curl -sL`, the 307→`/login`→200 chain prints `200` and you FALSELY report "all assets serve." Seen 2026-08-22: phone threw `sceneEl.system.minder.image-system.startScanning is not functioning` while CLI said green, because `aframe.min.js`/`card.mind` were 307→`/login`.
**Fix the check — never use `-L` for asset verification:**
```bash
base=https://lunavsolution.vercel.app
for f in ar/viewer.html ar/assets/card.mind ar/assets/aframe.min.js ar/assets/qrcode.min.js ar/assets/favicon.ico; do
  out=$(curl -s -o /dev/null -w "%{http_code}" --max-redirs 0 "$base/$f")
  loc=$(curl -sI --max-redirs 0 "$base/$f" | grep -i "^location" | tr -d '\r')
  echo "$out  ${loc:-}  $f"
done
# PASS = every line "200  " (no location). 307 + location:/login = asset is gated.
```
**Fix the gate** — broaden the middleware matcher so the asset subtree is public (Gotcha 5 below), redeploy, re-run the `--max-redirs 0` check. Phone/testing on a real device is ground truth.

## 8. Next.js `middleware.ts` matcher swallows static-asset subpaths (Gotcha 5)
The default matcher only negates `_next/...` + a few image extensions. It WILL run middleware on `.js`, `.mind`, `.ico`, fonts under `/ar/`, `/studio/`, etc., and 307-redirect them to `/login` for anonymous visitors → HTML loads, scripts/models 404-or-redirect.
```ts
// BEFORE (ar/ assets 307→/login):
matcher: ["/((?!_next/static|_next/image|favicon.ico|studio/|.*\\.(?:svg|png|jpg|jpeg|gif|webp|glb|obj|html?)$).*)"]
// AFTER (whole /ar subtree public + .js/.mind/.ico excluded from middleware):
matcher: ["/((?!_next/static|_next/image|favicon.ico|studio/|ar/|.*\\.(?:svg|png|jpg|jpeg|gif|webp|glb|obj|mind|ico|js|html?)$).*)"]
```
Redeploy, then verify with section 7's `--max-redirs 0` loop.

## Verification checklist (use BEFORE claiming "live")
- [ ] `npx vercel login` completed (device code approved by user)
- [ ] `vercel.json` has NO `framework`/`name` keys
- [ ] `npx vercel deploy --prod --yes` returns a `Deployment <url> ready.`
- [ ] **Every referenced asset (html, js, css, `.mind`, images, favicon) returns 200 with `--max-redirs 0` and NO `location:/login`** (use section 7 loop, NOT `curl -L`)
- [ ] `curl -s <DEPLOYMENT_URL>/<page> | grep -oE "<title>[^<]*</title>"` == YOUR app title (proves not a Vercel 404 shell)
- [ ] Verified against the `vercel ls --prod` URL, NOT a guessed `<slug>.vercel.app`
- [ ] If assets sit under a Next.js app, confirm `middleware.ts` matcher excludes that subtree (section 8)
