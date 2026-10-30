# Vercel push-to-deploy verification + the silent author-email no-fire (G31 / G31-ADDENDUM)

## Why this exists
`git push` updating GitHub does NOT guarantee the live Vercel site shows your
code. Two distinct failures, both ending with "user sees the old site":

1. **Integration not connected** — Vercel was never linked to the repo/branch.
   Fix: dashboard Git connect, or `vercel deploy --prod --token <TOKEN>`.
2. **Connected but SILENT webhook no-fire** — the integration IS wired, but the
   commit author email isn't one Vercel recognizes, so the build never starts.
   This session: a R-Tessera commit authored `Hermes <hermes@local>` (via
   `git -c user.email=...`) pushed fine, but `r-tessera.vercel.app` stayed on the
   pre-fresh-start build. The vault (GEMINI R-TESSERA CEO.md) states commit SHAs
   with `kingkymaru@gmail.com` trigger the auto-deploy — the `hermes@local`
   author silently broke the webhook. Re-authoring the tip as
   `kingkymaru@gmail.com` + re-pushing fired the deploy within ~1 min.

## Diagnose the silent no-fire
```bash
git log -1 --format='%an <%ae>' HEAD      # what the latest commit was authored as
git config user.email                      # what the repo expects
# if they differ → that's the webhook no-fire cause
```

## Fix
```bash
git commit --amend --author="$(git config user.name) <$(git config user.email)>" --no-edit
git push --force-with-lease origin main   # force-with-lease, never blind --force
```
Wait ~60s, then verify the live site (below).

## Verify the deploy actually happened (don't trust the push)
The ONLY ground truth is the live site. Probe it:

```bash
# 1) app is served (not a Vercel 404 page that still returns 200)
curl -s https://<project>.vercel.app/ | grep -ioE "<title>[^<]*</title>"

# 2) a file you added — size proves it's the NEW build, not the SPA fallback
#    (a 569-byte "cables.geojson" response is actually index.html fallback)
curl -s -o /dev/null -w "%{http_code} bytes=%{size_download}\n" \
  https://<project>.vercel.app/cables.geojson
#    expect the real size (e.g. 736516 for the 718-cable bundle), not 569

# 3) compare the served bundle hash vs your build
A=$(curl -s https://<project>.vercel.app/ | grep -oE "assets/index-[a-zA-Z0-9_-]+\.js" | head -1)
echo "live bundle: $A"
```

R-Tessera concrete signature: before fix `cables.geojson` -> 569 bytes (SPA
fallback) and `index.html` referenced `/cesium/Cesium.js` (old build); after fix
-> 736516 bytes and the fresh Vite-bundled app. The user's "yes, it's deployed,
I can see it" + the 736516-byte probe confirmed live.

## Habit to prevent the miss
For any Vercel-Git project, commit with the repo's configured identity:
- Prefer plain `git commit` over `git -c user.name=... -c user.email=... commit`.
- Never author as `hermes@local` / `HERMES` / a throwaway — it breaks the webhook.
- This is SEPARATE from vercel-prod-deploy-verification's "Variant B" (Vercel
  account-email mismatch = a red "Blocked" alert). The author-email no-fire is
  silent: no alert, deploy just never starts. The stale-build + no-new-Deployments-row
  signature is the only tell.
