# Read-only metrics + growth logging (health dashboard)

Pattern for charting app growth WITHOUT exposing PII and WITHOUT a server:
add **count-only `SECURITY DEFINER` SQL functions**, grant them to `anon`, then
poll them from a Node script that writes a dated Markdown table into an
Obsidian vault (or any text file) for tracking over time.

## Why this shape
- RLS hides row data from anon, so a plain `select` returns 0 rows — you can't
  count users via the client/anon key. A `SECURITY DEFINER` function runs as the
  table owner and returns only an aggregate, never column data. Grant to `anon`
  so a no-auth probe can call it.
- Counts are the growth signal: total users, pending approvals, models, markers.
  For apps with no "user" concept (e.g. a 3D viewer), count domain objects
  (models/markers) as a usage proxy.

## The functions (idempotent, safe to re-push)
```sql
create or replace function public.user_count()
returns bigint language sql stable security definer set search_path = public as $$
  select count(*) from public.user_profiles;
$$;
grant execute on function public.user_count() to anon, authenticated;

create or replace function public.pending_user_count()
returns bigint language sql stable security definer set search_path = public as $$
  select count(*) from public.user_profiles where approved = false;
$$;
grant execute on function public.pending_user_count() to anon, authenticated;
```
(For LUNAV-style apps: `model_count()`, `marker_count()` over `models`/`markers`.)
Deploy via `supabase db push --linked` (see P14/P15 — unique date prefix per file).

## The probe script (writes an Obsidian dated table)
Run `node healthcheck.mjs` from a dir that has `@supabase/supabase-js` installed
(ESM resolves from the script's dir, NOT cwd — put the script in the repo that
has the dependency, or `npm install` it there). Reads `.env.local` for the two
projects' URLs/keys (Vite uses `VITE_SUPABASE_`, Next uses `NEXT_PUBLIC_SUPABASE_`),
curls the live URLs for HTTP status, calls each RPC, and appends a row:

```
| Date | App | Live (HTTP) | Users / Usage | Pending | Build |
|------|-----|------------|---------------|---------|-------|
| 2026-07-27 | RINA | 200 | 2 | 0 | ✅ |
| 2026-07-27 | LUNAV | 200 | 6 (models) / 24 (markers) | — | ✅ |
```

Idempotent: re-running appends a NEW dated row each day (or each run) — gives a
time series you can read or paste into a sheet. Obsidian renders the table; for
actual sparkline/bar charts, switch the file to CSV or add a Mermaid block.

## Gotchas
- **Env var name differs by framework.** Vite = `VITE_SUPABASE_URL` /
  `VITE_SUPABASE_ANON_KEY`; Next.js = `NEXT_PUBLIC_SUPABASE_URL` /
  `NEXT_PUBLIC_SUPABASE_ANON_KEY`. The LUNAV probe failed first because it read
  `VITE_` against a Next app — match the prefix to the framework or the regex
  returns null and the script throws.
- **ESM module resolution** is from the script's own directory. A script in `~`
  can't find `@supabase/supabase-js` installed in `~/riina` — copy the script
  into the repo (absolute paths inside stay valid) or install the dep there.
- **Count-only is deliberate.** Never return rows/PII from these functions; keep
  them `security definer` + `stable` + single `count(*)`. That's what makes
  granting to `anon` safe.
- Pair with the 4-probe routine in this skill's main health-check reference for
  the full "app is alive" picture (build + live curl + REST/RLS probe + RPC).
