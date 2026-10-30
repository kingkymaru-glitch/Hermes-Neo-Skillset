# Pitfall: Vercel auto-deploy does NOT apply Supabase migrations

## The trap
A Next.js app on Vercel with `git push` → auto build+promote. The repo has
`supabase/migrations/*.sql` (schema + RPC fixes). You assume the live DB is
current. It is NOT. Vercel runs `next build` only — it never connects to
Postgres and never executes SQL. So:

- New columns (e.g. `proxies.model_id`), RPC body changes (e.g.
  `get_shared_project` now returning `kind/geometry_json/photos_json`), RLS
  policy edits — NONE of it reaches the live database on deploy.
- Symptom: frontend code is correct, types match, build is green, yet the live
  feature is broken (e.g. client share portal shows no defect markers / evidence
  photos because the live RPC still omits those fields).
- The repo migration files existing is NOT evidence they were applied. Check the
  live DB before concluding the code is at fault.

## How to detect (fast, no secrets)
1. `supabase status` / `supabase db lint` needs the project linked
   (`supabase/config.toml`). If `supabase` CLI reports "no config.toml" the
   project is NOT linked locally — migrations were likely never pushed.
2. Confirm the fix SQL is in repo `supabase/migrations/` and that it is NOT
   reflected by querying the live RPC/table from the app, OR ask the user to
   confirm in the dashboard.
3. `.env.local` for a Vercel project typically has ONLY
   `NEXT_PUBLIC_SUPABASE_URL` + `NEXT_PUBLIC_SUPABASE_ANON_KEY` — there is no
   DB/pooler string and usually no `SUPABASE_ACCESS_TOKEN`. So the agent cannot
   push DB changes itself; this is a privilege the user holds.

## The fix (user runs, agent supplies the SQL)
- Build ONE idempotent SQL file that combines ALL unapplied migrations in order.
  Use `if not exists`, `do $$ ... end $$` blocks for conditional `alter table ...
  set not null`, and `create or replace function` for RPCs. Idempotent = safe to
  re-run; the user may run it twice.
- Hand the user the exact file path. Two run paths:
  - **Dashboard (preferred, no CLI):** Supabase Dashboard → SQL Editor → New
    query → paste file → Run → "Success. No rows returned."
  - **CLI:** `supabase link --project-ref <REF>` then
    `supabase db push` (or `psql "$DATABASE_URL" -f <file>`). Requires an access
    token + pooler string the agent usually lacks.
- Find the project REF from `NEXT_PUBLIC_SUPABASE_URL`:
  `https://<REF>.supabase.co` → REF is the subdomain.
- Verify after: re-run the RPC from the app, or `select count(*) from <table>
  where <new_col> is not null;` then exercise the live feature.

## Why this belongs in workflow, not memory
This is a recurring class of bug for any Supabase+Vercel app: DB schema and app
code deploy through DIFFERENT pipelines. Every "feature works locally / in code
but not in prod" with a Supabase backend should FIRST check whether the relevant
migration was actually applied to live — before touching frontend code.

## Reference fix (real example from ss-rover-cloud / LunaV)
`supabase/migrations/20260801_apply_live_bug2_fix.sql` combined
`20260731_proxies_model_id.sql` + `20260801_fix_markers_rpc.sql` into one
idempotent script because Vercel had shipped the frontend but never the DB
changes. That is the canonical shape to copy: ordered, idempotent, single file,
run in dashboard SQL Editor.
