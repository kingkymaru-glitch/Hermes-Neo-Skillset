# Supabase remote migration recipe (SS Rover Cloud)

Applies SQL to the LIVE Supabase project from the CLI with NO local Postgres
container. Verified session 2026-07-25 (Phase 1.5).

## Why not `supabase sql -f`?
CLI 2.109.1 removed the top-level `supabase sql` subcommand. Running
`supabase sql --project-ref X -f file.sql` just prints global `--help`. The
remote-query capability moved under `db`:
- `supabase db query [--linked | --local | --db-url] [--file <path>] "<sql>"`

## Steps (per session)
```bash
cd /Users/kamarulhk/Documents/ss-rover-cloud

# 1. Confirm ACTIVE ref from the app's env (source of truth over stale notes)
grep NEXT_PUBLIC_SUPABASE_URL .env.local        # -> https://<REF>.supabase.co

# 2. Re-link to that ref
supabase link --project-ref <REF>

# 3. Apply the migration file
supabase db query --linked --file supabase/phase1_5.sql

# 4. Verify
supabase db query --linked --file /dev/stdin <<'SQL'
select table_name from information_schema.tables
 where table_schema='public' and table_name in ('documents','proxies') order by 1;
SQL

supabase db query --linked --file /dev/stdin <<'SQL'
select routine_name from information_schema.routines
 where routine_name='get_shared_project';
SQL
```

## Redeploy an Edge Function (when its source changed)
```bash
supabase functions deploy r2-presign --project-ref <REF>
```
Verified output: `Deployed Functions on project <REF>: r2-presign`.

## Phase 1.5 apply transcript (what was applied)
- New tables: `public.documents` (file_name, file_url, file_ext in
  pdf/jpg/jpeg/png/webp/gif, kind, file_size_bytes), `public.proxies`
  (label, shape box|plane, position_x/y/z, scale_x/y/z, rotation_x/y/z degrees,
  color, texture_url).
- RLS owner policies via `drop policy if exists … create policy` (idempotent —
  see SKILL.md pitfall: `CREATE POLICY IF NOT EXISTS` is invalid).
- `get_shared_project(uuid)` RPC REPLACED to also return `documents` + `proxies`
  arrays (so the read-only Client Share view shows proxies).
- `r2-presign` Edge Function extended: `ALLOWED_EXT` += `pdf`; `prefix` now
  handles `kind === "doc"` → `/docs/` path (same `ss-rover-models` bucket).

## Gotcha: ref selection
`.env.local` pointed at `okzmblyboudjffaifixa` (Sydney "rover-r-platform"). A
stale memory claimed live = `eobkcsxwwpszyzbwpqqy` (Seoul). The running app
dictates the target — applied to `okz…` and the feature then worked. When two
linked projects appear in `supabase projects list`, trust `.env.local`, not the
note.
