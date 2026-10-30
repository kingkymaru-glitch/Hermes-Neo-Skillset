# LunaV Studio iframe — middleware 307 blocker (2026-08-10)

## Symptom
The "LunaV Studio" tab button in the project workspace (`ProjectWorkspace.tsx`, the
`studio` tab → `<iframe src="/studio/lunav_studio_safe.html">`) appears to do
nothing when clicked: the panel stays blank / shows the login screen.

## Root cause
`src/middleware.ts` `config.matcher` did NOT exclude `.html` files:

```ts
// BEFORE (broken) — .html falls through to the auth middleware
matcher: ["/((?!_next/static|_next/image|favicon.ico|.*\\.(?:svg|png|jpg|jpeg|gif|webp|glb|obj)$).*)"],
```

So a request for a static HTML page under `public/` is processed by the middleware.
With no session cookie, the middleware 307-redirects to `/login`. The iframe then
loads `/login` (or the login page HTML) instead of the builder → "button not working."

This is DISTINCT from the `isPublic` route allow-list: that governs *App Router
routes*; the matcher governs *which request paths middleware even runs on*. A
static `.html` is neither an excluded asset nor in `isPublic`, so it gets gated.

## The fix (commit `96e5efa`)
```ts
// AFTER (fixed) — exclude .html AND the whole /studio/ dir
matcher: ["/((?!_next/static|_next/image|favicon.ico|studio/|.*\\.(?:svg|png|jpg|jpeg|gif|webp|glb|obj|html?)$).*)"],
```

## How to verify (run against `next dev` on :3000)
```bash
# Before: 307 -> /login  (BROKEN)
curl -sI http://localhost:3000/studio/lunav_studio_safe.html | grep -iE "HTTP/|location"
#   HTTP/1.1 307 Temporary Redirect
#   location: /login

# After: 200, body is the studio HTML
curl -sI http://localhost:3000/studio/lunav_studio_safe.html | head -1   # HTTP/1.1 200 OK
curl -s http://localhost:3000/studio/lunav_studio_safe.html | grep -c "LunaV Studio"   # > 0
```

## Hardening note (optional, not done)
`public/studio/lunav_studio_safe.html` imports Three.js from `https://unpkg.com`
via an ES-module importmap. On Vercel this needs outbound egress to unpkg. To make
the studio self-contained + CSP-safe, vendor Three.js into
`public/studio/vendor/` and rewrite the importmap to local paths. This also removes
the runtime dependency on a third-party CDN.

## Related
- `lunav-studio` SKILL.md → "Middleware `matcher` regex — static `.html` is ALSO gated"
- The `isPublic` route allow-list pitfall (separate mechanism) is covered just above it.
