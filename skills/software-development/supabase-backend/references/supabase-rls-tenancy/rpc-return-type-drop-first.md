# PITFALL #9 — `42P13 cannot change return type of existing function`

When an RPC that returns a TABLE (e.g. `fetch_orgs_with_creator() RETURNS TABLE(id,name,...)`)
needs to grow extra output columns (say, add `recent_actions jsonb`), `create or replace
function` FAILS with:

```
ERROR: 42P13: cannot change return type of existing function
DETAIL: Row type defined by OUT parameters is different.
HINT: Use DROP FUNCTION fetch_orgs_with_creator() first.
```

## Cause
`CREATE OR REPLACE FUNCTION` may change a function's BODY but NOT its signature
(input parameters or the `RETURNS TABLE(...)` row shape). Adding/removing an OUT
column changes the signature, so Postgres refuses to replace it.

## Fix
`drop function if exists public.<name>();` immediately before the `create or replace`
in the SAME script. `if exists` makes it idempotent, so the script is safe to re-run.

```sql
-- Must DROP first: the old function returns a different row shape.
drop function if exists public.fetch_orgs_with_creator();

create or replace function public.fetch_orgs_with_creator()
returns table ( id uuid, name text, approved boolean, created_at timestamptz,
                creator_name text, creator_email text, recent_actions jsonb )
language plpgsql security definer set search_path = public as $$ ... $$;
grant execute on function public.fetch_orgs_with_creator() to authenticated;
```

## Live case (RINA 2026-08-17)
`fetch_orgs_with_creator()` already returned `(id,name,approved,created_at,creator_name,creator_email)`.
Adding `recent_actions jsonb` (to show each company's last 3 audit actions in the Master
Admin Company Control) made `create or replace` fail with 42P13. Prefixing a
`drop function if exists` fixed it on the first re-run.

## General rule for Supabase RPC evolution
- **BODY-only change** (same params, same return): `create or replace` is fine.
- **Signature change** (new param OR new/removed OUT column): `drop function if exists` first.
- The Supabase client caches RPC metadata; after a drop+recreate with a new signature,
  hard-refresh the app so it picks up the new shape.
