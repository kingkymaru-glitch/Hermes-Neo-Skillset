---
name: supabase-rpc-token-patterns
description: Mint Supabase RPC tokens without pgcrypto (no hmac 404).
---

# Supabase RPC token minting (no pgcrypto)

## When to use
- Writing Postgres RPCs (SECURITY DEFINER) that mint or verify a handoff/share
  token — e.g. a "Link to X" button that proves project ownership across two apps.
- Symptom: client calls `supabase.rpc("mint_handoff_token", ...)` →
  `Failed to load resource: 404` + popup error
  `function hmac(text, text, unknown) does not exist`.

## Root cause
`hmac()`, `encode()`, and `gen_random_bytes()` live in the **`pgcrypto`**
extension, which is NOT enabled by default on many Supabase projects. Calling
them → `function hmac does not exist` → the RPC body errors → the client sees a
**404** for the rpc call (the function "exists" but its body throws).

## Fix — no extension required
`gen_random_uuid()` is built into core Postgres 13+ (Supabase runs PG15+). Use it:

**Mint** (store the token on the row so the consumer can verify binding):
```sql
create or replace function public.mint_handoff_token(p_project_id uuid)
returns text language plpgsql security definer set search_path = public as $$
declare
  v_owner uuid;
  v_token uuid := gen_random_uuid();
begin
  select owner_id into v_owner from public.projects where id = p_project_id;
  if v_owner is null then raise exception 'Unknown project'; end if;
  if v_owner <> auth.uid() then raise exception 'Not project owner'; end if;
  update public.projects set handoff_token = v_token where id = p_project_id;
  return v_token::text;
end; $$;
grant execute on function public.mint_handoff_token(uuid) to authenticated;
```

**Verify** (in the consumer RPC — binds token ↔ project, no pgcrypto):
```sql
select owner_id, handoff_token::text into v_owner, v_stored
from public.projects where id = p_lunav_project_id;
if v_owner is null then raise exception 'Unknown project'; end if;
if v_stored is null or v_stored <> p_handoff_token then
  raise exception 'Invalid handoff token';
end if;
```
Also need `alter table public.projects add column if not exists handoff_token uuid;`
(full corrective SQL in `references/handoff-token-sql.md`).

## Applying when you can't reach the DB from the agent
1. Write a corrective migration file (e.g. `supabase/migrations/20260808b_*.sql`).
2. Have the user paste it into the Supabase **SQL Editor** and Run it.
3. **Probe to confirm** (agent CAN use the anon key via node/`@supabase/supabase-js`):
   call the rpc with a dummy uuid. Expect `'Unknown project'` (proves the
   function now runs) — NOT `'function does not exist'` (proves pgcrypto/hmac
   is gone). Also confirm `projects.handoff_token` column is readable.

## Pitfall — duplicate `create or replace` line
Patching an existing `create or replace function` block with find/replace can
accidentally duplicate the `create or replace function ...` header line, which
breaks the SQL. Always re-read the file after a patch and remove the dup.

## Pitfall — Postgres 42P13: params with DEFAULT must come LAST
When you write `create or replace function`, **once a parameter has a DEFAULT,
every parameter declared after it must ALSO have a DEFAULT.** Declaring a
required (no-default) param after a defaulted one throws
`ERROR: 42P13: input parameters after one with a default value must also have defaults`.
This bit twice in one ROVER-KIT session. The rule is POSITIONAL, not named —
`supabase.rpc("fn", {obj})` calls by name, but Postgres parses the DDL positionally.

Correct shape — all required params FIRST, optional-defaulted LAST:
```sql
create or replace function public.upsert_cctv_camera(
  p_project_id uuid,                 -- required, first
  p_name text,                       -- required
  p_lon double precision,            -- required
  p_lat double precision,            -- required
  p_id uuid default null,            -- optional, after all required
  p_comm text default '',
  p_status text default 'active'
)
```
Wrong (throws 42P13): `p_id uuid default null` followed by `p_name text` (no default),
or `p_comm text default ''` followed by `p_lon double precision` (no default).
Even `p_project_id uuid default null` first violates it because the next three
required params follow it.

Client-side safety: when the caller uses NAMED args —
`supabase.rpc('upsert_cctv_camera', { p_project_id, p_name, ... })` — reordering the
signature is transparent to the frontend, so you can freely reshuffle params to
satisfy the rule WITHOUT touching app code. Also keep the
`grant execute on function public.fn(<types>) ...` arg-TYPE list in the same order
as the params (types only, no names), or the grant won't match and the RPC call
fails with "function does not exist".

## Pitfall — Postgres 42P13: cannot CHANGE the NAME of an existing parameter
`CREATE OR REPLACE FUNCTION` can add a new param or change a body, but it
CANNOT rename an existing parameter. If the live function has `p_stream text`
and your migration re-creates it with `p_stream_url text`, PostgREST's schema
cache lookup (which matches RPCs by PARAMETER NAME) fails with:
```
ERROR: 42P13: cannot change name of input parameter "p_stream"
HINT: Use DROP FUNCTION upsert_cctv_camera(uuid,text,double precision,
      double precision,uuid,text,text,text) first.
```
The HINT is literal — you must DROP the function using its EXACT CURRENT arg
signature (types only, in order), then CREATE it fresh with the renamed param:
```sql
DROP FUNCTION IF EXISTS public.upsert_cctv_camera(
  uuid, text, double precision, double precision, uuid, text, text, text);
CREATE FUNCTION public.upsert_cctv_camera(
  p_project_id uuid, p_name text, p_lat double precision, p_lon double precision,
  p_comm text, p_status text, p_stream_url text, p_id uuid default null)
returns ... language plpgsql security definer set search_path = public as $$ ... $$;
grant execute on function public.upsert_cctv_camera(
  uuid, text, double precision, double precision, uuid, text, text, text)
  to anon, authenticated;
notify pgrst, 'reload schema';   -- MUST reload cache after DDL
```
Real hit: a migration authored `p_stream` while the app called `p_stream_url`;
PostgREST matched by name → "Could not find the function
public.upsert_cctv_camera(...,p_stream_url) in the schema cache". Renaming via
`CREATE OR REPLACE` threw 42P13; the DROP + CREATE fixed it. Always
`notify pgrst,'reload schema'` after any RPC DDL so the anon client sees it.

## Writable/shared table consumed by another app (CCTV registry variant)
`mint_handoff_token` is ONE-WAY: it mints a link token. When the OTHER app (R-Tessera)
needs to READ a table you own, do NOT grant anon SELECT on the table (it's denied by
default and that's correct) — expose a **SECURITY DEFINER view** (`grant select … to anon,
authenticated`) so the consumer reads only whitelisted columns. When the other app or an
edge device needs to WRITE, give it a **SECURITY DEFINER upsert RPC that re-checks
`auth.uid()` ownership of the parent project** — the exact same `select owner_id …; if
v_owner <> auth.uid() then raise` shape as `mint_handoff_token`. Never allow a direct anon
INSERT. Full worked example (cctv_cameras + cctv_events + upsert_cctv_camera +
cctv_cameras_public view) in `references/rover-kit-cctv-integration.md` (under the
`ss-rover-cloud-dev` skill).

## See also
- `references/handoff-token-sql.md` — full corrective migration (paste into Supabase SQL Editor).
- `references/hardcoded-anon-key-vercel.md` — hardcode the anon key to bypass Vercel env-vars entirely.
- `references/geo-link-architecture.md` — full cross-app linking architecture (R-Tessera CesiumJS ↔ LunaV Next.js via shared Supabase). Tables, flow, pitfalls, two-token design.

For Cesium CDN loading + race-condition fixes in Next.js, see the `cesium-resium-react` skill `references/cesium-nextjs-cdn-load.md`.
Storing the token on the row + verifying on use is sufficient when only the
owner can mint (RLS/SECURITY DEFINER checks `auth.uid()`). Don't ship a
hardcoded secret in `current_setting('app.settings.*')` — it won't exist
without manual extension/config and reintroduces the failure.
