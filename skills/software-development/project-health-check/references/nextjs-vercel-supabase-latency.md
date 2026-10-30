# Next.js App Router + Vercel + Supabase — Latency / Slow-Navigation Diagnosis

Use when a Next.js (App Router) app on Vercel is "live" but SLOW to open a page or
jump page-to-page, and the DB is Supabase (often in a different region).

## A SLOW hydrating page reads exactly like a BROKEN one (wait before you judge)
A client-rendered route behind a Suspense/`loading.tsx` boundary can sit on its spinner
for tens of seconds while the real content is ALREADY in the served HTML. A single early
check reports `len` in the ~100s + a visible "Loading…" + a tiny 300×150 canvas — which is
byte-for-byte indistinguishable from a dead page, and it is not.

```bash
# served HTML still carries the fallback + the streaming marker:
grep -oE '\$\?|<!--\$/--|template id="B:0"' page.html | sort | uniq -c   # Suspense boundary
# the fallback text matches the repo's loading.tsx -> timing question, not a crash
grep -c "Loading" page.html
```

- **Poll the body length every second for 30–60s** in a real browser; if it climbs past the
  placeholder the page is SLOW, not broken. Report the measured seconds-to-content as its
  own finding (a ~45s first paint on a LANDING page is a genuine first-impression defect
  worth its own line) — do not file it as an outage.
- **Give hydration ~45s before concluding anything**, then assert the settled state.
- **Use a sibling route as a control.** A different route that loads instantly proves the
  app + its backend are healthy and localises the fault to that one page's load path. Do
  not let one slow page colour the verdict on the whole project.

## Quick signal probe (run from a terminal)
```bash
# 1. Is Vercel co-located with the DB? (no vercel.json => defaults to iad1 / US-East)
ls vercel.json || echo "NO vercel.json -> Vercel on iad1 (US-East) by default"

# 2. Round-trip browser->Vercel and browser->Supabase (repeat 3x)
for i in 1 2 3; do curl -o /dev/null -s -w "vercel ttfb=%{time_starttransfer}s\n" https://<app>.vercel.app/; done
for i in 1 2 3; do curl -o /dev/null -s -w "supabase ttfb=%{time_starttransfer}s\n" https://<ref>.supabase.co/rest/v1/; done

# 3. Heavy client component?
du -h src/components/<Big>.tsx

# 4. Any route-level loading UI? (none => blank screen per nav)
find src -name "loading.tsx"
```

## Common root causes (in order of impact)
1. **Cross-region Vercel/Supabase.** No `vercel.json` ⇒ Vercel runs in iad1
   (US-East). If Supabase is e.g. Sydney (ap-southeast-1), every server-side call
   (middleware + page data fetches) crosses the Pacific, and a browser in Asia also
   hops to Virginia first. Fix: add `vercel.json` with `"regions": ["syd1"]`
   (or the DB's region) to co-locate. BIGGEST single win.
2. **Middleware fires 2 sequential DB calls per navigation** — e.g.
   `auth.getUser()` then `profiles.select('approved')`. Each is an edge→DB round-trip.
   Fix: read `approved` from the JWT claim, or cache it; don't hit the DB every nav.
3. **Sequential awaited DB queries in a server component** — e.g. 4–5
   `await`ed queries one after another stack latency (5× RTT instead of 1×).
   Fix: `await Promise.all([q1, q2, q3])`.
4. **No `loading.tsx` / route skeletons** ⇒ every navigation is a blank screen
   until the server finishes. Fix: add `loading.tsx` per heavy route.
5. **Heavy unsplit JS** — a large `"use client"` component (e.g. 160KB) that
   statically imports three.js + chart.js + gltf-pack ships all of it in the route
   chunk. Fix: `next/dynamic` (ssr:false) for the 3D viewer, and lazy-load
   chart.js/analytics only when that tab mounts.

## Auth-gate verification gotcha
When checking auth-gated routes, do NOT use `curl -L` — `-L` follows the 307
redirect to `/login` and reports login's 200, masking the gate. Probe WITHOUT
`-L` to see the true status + `Location`:
```bash
curl -s -o /dev/null -D - -w "FINAL=%{http_code}" https://<app>/dashboard
# expect: HTTP/... 307  +  location: /login
```

## Local-key probe gotcha
A local `.env.local` Supabase anon key that is a short placeholder (e.g. 34 chars,
not a JWT `eyJ…`) will 401 anon table probes even when the LIVE DB is fine — the
real key lives in Vercel env. Don't conclude "DB down" from a local-key probe;
check key shape with `awk -F= '/ANON_KEY/{print length($2)}' .env.local`
(valid JWT ≥ ~100 chars, starts `eyJ`).
