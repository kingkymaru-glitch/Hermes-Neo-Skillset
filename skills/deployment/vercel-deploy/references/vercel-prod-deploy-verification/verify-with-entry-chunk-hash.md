# Prove a Vercel deploy is actually LIVE (browser-free)

The build can succeed and the webhook can fire, but the production domain may
still serve a STALE bundle, or the deploy may not have finished building yet.
Verify with curl only — no screenshots, no headless browser (which also risks
orphaned Chrome procs on the founder's Mac).

## Loop
1. Push to the git branch Vercel watches (commit with the founder identity so
   the webhook fires — see the deploy skill).
2. Wait ~40–60s for the build + alias swap.
3. `code=$(curl -s -o /dev/null -w "%{http_code}" --max-time 10 https://<domain>)`
   → expect `200`. A `404`/`000` means wrong domain or not built yet.
4. **Entry-chunk hash match (the real proof):** Vite names the entry bundle
   `assets/index-<hash>.js`. Compare what the LIVE server serves against your
   local build:
   ```bash
   echo "served : $(curl -s --max-time 10 https://<domain> | grep -o '/assets/index-[A-Za-z0-9_]*\.js' | head -1)"
   echo "local  : $(grep -o '/assets/index-[A-Za-z0-9_]*\.js' dist/index.html | head -1)"
   ```
   If the two hashes are identical, the new build is definitively live (not a
   cached/old alias). If they differ, the deploy is still in flight — wait and
   re-check.

## Notes
- `vercel.json` SPA fallback rewrites `/(.*) -> /index.html`, so `/` returns
  200 even for a blank app — HTTP 200 ALONE is not proof. The hash match is.
- If you have no DOMAIN, get it from `vercel.json` or ask; do not guess
  `rina.vercel.app` (third-party) when the project is `rina-m.vercel.app`.
- The same hash-compare trick works for any Vite/React project: the entry
  script name is deterministic per build, so a matching hash == same bundle.
