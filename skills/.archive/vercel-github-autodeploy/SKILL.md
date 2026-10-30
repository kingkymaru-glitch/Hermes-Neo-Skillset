---
name: vercel-github-autodeploy
description: "Vercel push-to-deploy; author gates webhook, verify live."
---

# Vercel GitHub Auto-Deploy (push-to-deploy)

For Vercel projects connected via the **Git integration**, deployment is triggered by
`git push` to the production branch (usually `main`) — no CLI needed.

## Mechanism (explain plainly before acting)
- Vercel watches the linked repo/branch; on push it builds and replaces production.
- The local `vercel` CLI is NOT required. Only use it for a preview or a repo that isn't Git-connected.

## GOTCHA — commit author gates the webhook (real, observed this session)
A push whose tip commit author does NOT match the GitHub account linked to the Vercel
project may NOT trigger a rebuild. Concrete case:
- Tip authored `Hermes <hermes@local>` → pushed → **live stayed on old build**.
- Re-authored as `kingkymaru@gmail.com` (the repo's git identity that owns the GH↔Vercel link)
  + re-pushed → **deploy fired, live updated**.

Rule: **commit/push with the repo's configured git identity** (owner of the GH↔Vercel link).
Override author with `git -c user.name=maru -c user.email=kingkymaru@gmail.com commit ...`
then `git push`; for an already-pushed tip use `git commit --amend --author=...` +
`git push --force-with-lease` (acceptable here — tip is unpublished by others; user approved).

## VERIFY the deploy actually happened (don't assume push = deployed)
A green `git push` does NOT prove the live site changed. After pushing:
1. Wait ~20–30 s for build.
2. Curl a known static asset, compare byte size to local `dist/<asset>`:
   `curl -s -o /dev/null -w "%{size_download}" https://<site>/<asset>`
3. Grep the build hash in `/`: `curl -s https://<site>/ | grep -o 'assets/index-[A-Za-z0-9]*\.js'`
   — new hash = new deploy.
4. If size/hash unchanged → webhook didn't fire; check author, re-push, or check dashboard.

## When the CLI is unavoidable
Global `npm i -g vercel` is often **permission-blocked** on macOS (`/usr/local/lib/node_modules`).
Install locally: `npm i -D vercel`, run `./node_modules/.bin/vercel deploy --prod --token <TOKEN>`.
But for Git-connected projects prefer the push — that's what "push it through GH" means.

## Pitfalls
- Don't declare "deployed" from a green push alone — verify via asset/hash curl.
- A `<title>`/old build served live = STALE deploy, not a push failure.
- SPA rewrite: a missing static asset on Vercel returns `index.html` (200, ~500 B), NOT 404 —
  so "HTTP 200" on an asset URL isn't proof it exists; check byte size.
- Don't waste time on global CLI install when a plain `git push` is the mechanism.
- **Trust the served bundle, not the README, for "is the backend wired".** A repo's
  README/ARCHITECTURE can claim "frontend-only, no backend" while the live build
  actually talks to Supabase (seen on RINA: docs said mock, live bundle contained
  `https://<REF>.supabase.co`). To confirm a Vite/React SPA deploy actually CARRIED its
  backend env vars — vs. silently falling back to a "Backend not configured" message —
  fetch the live bundle and grep it:
  ```bash
  curl -s https://<site>/ > /tmp/idx.html
  # extract the entry <script type=module src="..."> asset name from /tmp/idx.html
  curl -s https://<site>/assets/<entry>.js > /tmp/app.js
  grep -c "supabase.co" /tmp/app.js        # or your project REF / anon key
  ```
  Present => the build had `VITE_SUPABASE_URL`/`ANON_KEY` => backend IS wired (not the
  placeholder fallback). Absent => env vars missing at build => the app serves the
  "Backend not configured" screen / white screen. This is stronger proof than reading
  source, because Vite inlines `import.meta.env` into the bundle at build time — if it's
  in the bundle, it shipped. (Also: a stale README is a doc bug to fix, not evidence the
  deploy is broken.)

See `references/this-users-vercel-projects.md` for this user's projects + author convention.
