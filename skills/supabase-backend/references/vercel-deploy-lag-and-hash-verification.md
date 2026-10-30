# Vercel deploy lag + built-asset verification

## Symptom
GitHub shows a fresh push, but the Vercel dashboard still lists the last
successful deployment as N minutes ago and the live site appears unchanged.

## Quick verification via built asset hash
Vercel mints a new chunk hash per deploy. In the live HTML, extract:
```sh
curl -s https://<app>.vercel.app/ | grep -o 'assets/index-[^"]*\.js'
```
Compare the hash to the locally built `dist/assets/index-*.js` path names.
Matching hashes confirm the live site is serving the new build even when the
dashboard UI lags or batches multiple pushes into one deploy.

## Why Vercel “missing deploy” happens
- Two pushes within ~2 minutes may merge into one deployment.
- Vercel dashboard “Last deployment” age can lag a minute or two while build
  queuing is happening.
- `npx vercel deploy` / `vercel alias` may fail if Vercel cannot map the
  local git ref to GitHub; the supported deploy path from Hermes is
  `git push origin main` → Vercel auto-build + promote.

## Decisive checks
1. `git log origin/main --oneline -5` — confirm your commit is on remote.
2. Built asset hash from local `dist/` vs live HTML from `curl`.
3. If the hashes diverge after 3+ minutes, re-push; Vercel will expose the
   failure in the dashboard UI within a minute.
