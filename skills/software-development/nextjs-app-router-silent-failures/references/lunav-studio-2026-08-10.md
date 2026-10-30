# Reference — LunaV session 2026-08-10 (concrete reproduction)

## Symptom reported
"LunaV Studio button in the workspace tab row does nothing — inspector should reach the 3D model builder."

## Two independent bugs found (both fixed same session)
1. `/studio/lunav_studio_safe.html` iframe → 307 redirect to /login.
   - Probe that confirmed it: `curl -sI http://localhost:3000/studio/lunav_studio_safe.html`
     → `HTTP/1.1 307` + `location: /login`. After fix → `200`.
   - Root cause: `middleware.ts` matcher excluded svg/png/jpg/jpeg/gif/webp/glb/obj
     but NOT `.html`, so the static html ran through auth middleware.
   - Fix applied (committed): added `html?` and explicit `studio/` to the negative-lookahead.

2. Console `Minified React error #418` on the workspace page.
   - Root cause: `ProjectWorkspace.tsx` rendered
     `new Date(x).toLocaleDateString()` / `.toLocaleString()` during SSR (data from
     server-component props). Server (Node/UTC) vs browser (local TZ) → mismatch.
   - Fix: added `formatDate`/`formatDateTime` using
     `Intl.DateTimeFormat("en-CA", {... timeZone:"UTC"})`.

## Unrelated console noise (do NOT conflate)
- `Failed to load resource: 400 (update_project_branding)` — PostgREST 400 = RPC
  not deployed on LIVE DB (DDL applied manually in Supabase Dashboard per env rule).
  Prepared `supabase/deploy_branding_rpc.sql` (idempotent CREATE OR REPLACE) for MARU to run.
  Could not verify/applied from agent (no SQL access).

## Verify sequence that closed it
- `npm run build` (type-check gate, exit 0)
- `npx eslint <changed file>` (confirm 0 NEW errors; pre-existing warnings ignored)
- `curl -sI <static route>` (307 = still gated, 200 = fixed)
