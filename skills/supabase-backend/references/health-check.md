# App health-check routine (two Supabase-backed apps)

Reusable 4-probe pattern used to produce a "simple health report" for a
deployed app. Runs from the repo root (Vite/Vercel build) + a Node one-liner
(backend reachability). No new dependencies beyond `@supabase/supabase-js`
already in the repo.

## Probes (run in order)

1. **Client build** — `npm run build` (or `next build`). Green exit = TS/TSX
   compiles. This is the baseline; it does NOT prove the backend.
2. **Live site HTTP** — `curl -s -o /dev/null -w "http_code=%{http_code} time=%{time_total}s\n" <url>`.
   Expect `200`. A non-2xx means the deploy failed or the route is wrong.
3. **Supabase REST reachability + RLS** (Node, anon key from `.env.local`):
   ```js
   import("@supabase/supabase-js").then(async ({createClient})=>{
     const fs=await import("fs");
     const env=fs.readFileSync(".env.local","utf8");
     // Vite app: VITE_SUPABASE_URL / VITE_SUPABASE_ANON_KEY
     // Next app: NEXT_PUBLIC_SUPABASE_URL / NEXT_PUBLIC_SUPABASE_ANON_KEY
     const url=env.match(/_(SUPABASE_URL|PUBLIC_SUPABASE_URL)=(.*)/)[2].trim();
     const anon=env.match(/_(SUPABASE_ANON_KEY|PUBLIC_SUPABASE_ANON_KEY)=(.*)/)[2].trim();
     const sb=createClient(url,anon);
     const r=await sb.from("user_profiles").select("id").limit(1); // or "models"/"markers"
     console.log("REST reachable:", r.error?("ERR "+r.error.message):("ok anon_rows="+r.data.length));
   });
   ```
   - `anon_rows = 0` with no error => RLS is enforcing (anon can't read) — GOOD.
   - An error here usually means wrong table name or the anon key can't reach
     the project (network/region).
4. **RPC existence (if relevant)** — e.g. for an approval gate:
   `await sb.rpc("approve_user",{target:"00000000-0000-0000-0000-000000000000",approve:true})`
   Expect a *rejection* ("Only a Super Admin can approve users.") when called
   unauthenticated — that proves the RPC exists and is access-controlled.

## Reading the report

- All 4 probes pass => HEALTHY (live, builds, backend reachable, auth/RLS on).
- Build green but live HTTP != 200 => deploy/bundle problem (check Vercel).
- REST probe errors or `anon_rows > 0` => RLS misconfigured (data leak risk).
- RPC probe returns "unexpected-ok" (no error) when unauthenticated => the RPC
  lacks its admin SECURITY DEFINER guard — fix it.

## Notes
- The anon key is public; reading it from `.env.local` is fine. Never log the
  service_role key.
- This routine verifies *reachability + RLS shape*, not business logic. For
  gate/trigger logic, prefer the owner-level `select` in the SQL Editor (P23).
- Vercel project names differ from the repo: RINA -> `riina-eight.vercel.app`
  (project `rina-platform`); LUNAV -> `ss-rover-cloud.vercel.app`. The live URL
  is NOT stored in the repo — confirm via the Vercel dashboard if unsure.
