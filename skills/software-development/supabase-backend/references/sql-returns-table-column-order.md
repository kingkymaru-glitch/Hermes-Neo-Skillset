# PostgreSQL RETURN TYPE MISMATCH (42P13) — TWO DISTINCT CAUSES

There are two unrelated ways to hit `42P13`, with different errors and different fixes.

## CAUSE A — Column ORDER mismatch inside the function body

## Symptom
```
ERROR: 42P13: return type mismatch in function declared to return record
DETAIL: Final statement returns <type_a> instead of <type_b> at column N.
CONTEXT: SQL function "fn_name"
```

## Root cause
The column ORDER in `RETURNS TABLE(...)` does not match the CTE/SELECT column order inside the function body. Postgres matches by POSITION, not by name.

## Fix
Reorder the CTE select columns to match the `RETURNS TABLE(...)` declaration order exactly.

### Example (wrong)
```sql
returns table(
  id uuid,       -- pos 1
  name text,     -- pos 2
  created timestamptz,  -- pos 3
  updated timestamptz   -- pos 4
)

-- inside CTE:
select p.id, p.name, p.created, p.share_token, ... as updated
--                                       ^ pos 4 = uuid, expected timestamptz → ERROR
```

### Example (fixed)
```sql
-- inside CTE:
select p.id, p.name, p.created, ... as updated, p.share_token
--                                ^ pos 4 = timestamptz ✓
```

## CAUSE B — Changing the RETURN TYPE of an EXISTING function via `CREATE OR REPLACE`

## Symptom
```
ERROR:  42P13: cannot change return type of existing function
DETAIL: Row type defined by OUT parameters is different.
HINT:   Use DROP FUNCTION <fn>() first.
```

## Root cause
`CREATE OR REPLACE FUNCTION` can change a function's BODY and its `plpgsql`/`security definer` attrs, but it **cannot change the return type (the `RETURNS TABLE(...)` signature)** once the function already exists. Adding a column to an existing `RETURNS TABLE(...)` (e.g. to return extra fields from a company-control list) triggers this — NOT cause A. The error fires in the SQL Editor the moment you paste the new definition.

## Fix
DROP the old function FIRST, then `CREATE OR REPLACE` (or plain `CREATE`) with the new return shape. Put the `drop function if exists public.<fn>();` line above the `create` in the SAME SQL block so it runs top-to-bottom:
```sql
drop function if exists public.fetch_orgs_with_creator();
create or replace function public.fetch_orgs_with_creator()
returns table (id uuid, name text, approved boolean, created_at timestamptz, creator_name text, creator_email text, recent_actions jsonb) ...
```
- `drop ... if exists` keeps it idempotent (safe to re-run).
- After dropping, re-grant `execute ... to authenticated;` — the grant does NOT survive the drop, so include it in the same block.
- Real case (RINA 2026-08-17): `fetch_orgs_with_creator()` was extended to also return `recent_actions jsonb`; the user's `create or replace` paste failed with this exact 42P13. Added the `drop function if exists` line → ran clean.

## CAUSE C — Optional parameter AFTER a required one (default-value ordering)

## Symptom
```sql
ERROR:  42P13: input parameters after one with a default value must also have defaults
CONTEXT: SQL function "upsert_cctv_camera"
```
This fires when you paste a function whose parameter list has a parameter WITH a
default value followed by one WITHOUT a default.

## Root cause
PostgreSQL requires that once a parameter has a `DEFAULT`, every parameter that comes
AFTER it must ALSO have a default. You cannot put a required (no-default) param after an
optional one. Common trigger: a function that takes an optional `p_id uuid default null`
(upset key) FIRST, then required fields (`p_project_id uuid`, `p_name text`) after it.

## Fix
Order parameters required-first, optional-with-defaults-last. The function body and the
`grant execute` signature must match the new order.

### Wrong
```sql
create or replace function public.upsert_cctv_camera(
  p_id uuid default null,                 -- optional, has default
  p_project_id uuid,                      -- required, NO default → ERROR
  p_name text,
  p_lon double precision,
  p_lat double precision,
  p_comment text default null,
  p_status text default 'active'
) returns uuid language plpgsql security definer as $$
...
$$;
-- grant execute on function public.upsert_cctv_camera(uuid, uuid, text, double precision, double precision, text, text) to authenticated;
```

### Fixed
```sql
create or replace function public.upsert_cctv_camera(
  p_project_id uuid,                      -- required
  p_name text,                            -- required
  p_lon double precision,                 -- required
  p_lat double precision,                 -- required
  p_id uuid default null,                 -- optional (upsert key), last
  p_comment text default null,
  p_status text default 'active'
) returns uuid language plpgsql security definer as $$
...
$$;
-- grant execute on function public.upsert_cctv_camera(uuid, text, double precision, double precision, uuid, text, text) to authenticated;
```
- Front-end callers that use NAMED arguments (`supabase.rpc('upsert_cctv_camera', { p_project_id, p_name, ... })`)
  are unaffected by the reorder — named args bind by name, not position. So reordering is
  transparent to the client.
- When you reorder params, also update the `grant execute on function ...(types)` signature
  to match, or the grant silently no-ops and authenticated callers get "permission denied".

## Real case
ROVER-KIT `upsert_cctv_camera` (2026-08-25): first draft put `p_id uuid default null` first,
then required `p_project_id`/`p_name`/`p_lon`/`p_lat` → 42P13 in Supabase SQL Editor. Moved
required params first, optional `p_id`/`p_comment`/`p_status` last, updated the grant signature
→ ran clean.

## Idempotency
Use `CREATE OR REPLACE FUNCTION` so re-running the SQL is safe. Keep migration SQL in `supabase/migrations/`.

