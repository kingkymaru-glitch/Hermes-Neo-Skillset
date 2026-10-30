# RPC body depends on pgcrypto AND PostgREST caches the function body by OID

Two adjacent traps that bit SkyPin (Flutter AR app, shared rina-platform project,
~2026-08-31) while debugging "Summon SkyPin fails". The first is a one-line
symptom fix; the second is the non-obvious one that eats a whole debugging session.

## Trap 1 — `gen_random_bytes(integer)` does not exist (code 42883)

**Symptom (Flutter):**
```
Summon failed: PostgrestException (message: function gen_random_bytes(integer)
does not exist, code 42883, details: not found, Hint: No function matches given
name and argument types...)
```

**Root cause:** the RPC body calls `gen_random_bytes(6)`. `gen_random_bytes()`
is provided by the `pgcrypto` extension, which Supabase projects do NOT enable
by default. `gen_random_uuid()` is core Postgres 13+ and IS available; the
`gen_random_bytes()` variant is pgcrypto-only. Same family as P42 (`hmac`/`crypt`).

**Fix — replace with a pure-SQL token, no extension:**
```sql
v_token := left(encode(md5(random()::text || clock_timestamp()::text), 'hex'), 12);
```
`md5()` is core; `random()::text || clock_timestamp()::text` gives high-cardinality
entropy; `left(..., 12)` yields a 12-char hex room token. Works on every Postgres.

**Verification that the fix is applied** (run in SQL Editor, returns the live body):
```sql
select oid, pg_get_function_identity_arguments(oid) as args, prosrc
from pg_proc
where proname = 'create_room' and pronamespace = 'public'::regnamespace;
```
If `prosrc` still shows `gen_random_bytes`, the body did not persist.

## Trap 2 — PostgREST serves the STALE body even after `CREATE OR REPLACE` + `notify pgrst, 'reload schema'`

**This is the time-waster.** You fix the body (Trap 1), re-apply, `notify pgrst,
'reload schema';`, the SQL Editor even confirms `prosrc` is now the md5 version —
yet the app STILL throws the original `gen_random_bytes does not exist` error.

**Why:** PostgREST caches function definitions **by the function OID**.
`CREATE OR REPLACE FUNCTION` keeps the SAME OID, so PostgREST keeps serving the
body it first loaded for that OID. `notify pgrst, 'reload schema'` does NOT force
it to re-read a body whose OID is unchanged. The diagnostic `select ... from pg_proc`
shows the CURRENT db body (correct), but PostgREST is executing a cached OLD body.

**Fix that actually works — DROP + CREATE (new OID), then reload:**
```sql
drop function if exists public.create_room(text, boolean);
create function public.create_room(
  p_room_skin text default 'arrow',
  p_all_app boolean default false
) returns table (token text, room_id uuid, expires_at timestamptz)
language plpgsql security definer set search_path = public as $$
declare
  v_token text;
  v_id    uuid;
  v_exp   timestamptz;
begin
  if auth.uid() is null then
    raise exception 'auth_required';
  end if;
  v_token := left(encode(md5(random()::text || clock_timestamp()::text), 'hex'), 12);
  insert into public.rooms (token, creator_id, room_skin, all_app)
  values (v_token, auth.uid(), p_room_skin, p_all_app)
  returning id, expires_at into v_id, v_exp;
  insert into public.participants (room_id, user_id, display_name, lat, lng, is_creator, pin_skin)
  values (v_id, auth.uid(), 'Host', 0, 0, true, p_room_skin);
  return query select v_token, v_id, v_exp;
end;
$$;
notify pgrst, 'reload schema';
```
`drop` assigns a brand-new OID to the re-created function → PostgREST MUST rebuild
its cache against the current body. This is the missing step when "the DB is right
but the API keeps throwing the old error."

**Rule:** to change a function's BODY such that PostgREST reliably serves it,
prefer `DROP FUNCTION` + `CREATE FUNCTION` (not `CREATE OR REPLACE`) and reload.
`CREATE OR REPLACE` is fine for FIRST definition / additive signature changes, but
is unreliable for body swaps on an already-cached OID.

## Diagnostic that separates "server wrong" from "app hitting wrong project"

If you've fixed + reloaded + DROP/CREATE and the app STILL throws the old error,
prove where the stale copy lives:

1. **Test the RPC directly in the SQL Editor** (bypasses the app):
   ```sql
   select * from public.create_room('arrow', false);
   ```
   A `P0001: auth_required` (unauthenticated direct call) proves the CORRECT md5
   body is live (it reached the `auth.uid() is null` guard). If it instead threw
   `gen_random_bytes`, the DB you ran it in is not the fixed one.

2. **Probe the app's EXACT project URL with curl** (simulates what the app does):
   ```bash
   curl -s -X POST "https://<ref>.supabase.co/rest/v1/rpc/create_room" \
     -H "apikey: <publishable_key>" -H "Authorization: Bearer <publishable_key>" \
     -H "Content-Type: application/json" \
     -d '{"p_room_skin":"arrow","p_all_app":false}' -w "\nHTTP %{http_code}\n"
   ```
   `{"message":"auth_required"}` HTTP 400 = the RPC on THAT project is the fixed
   md5 version. If curl shows `gen_random_bytes`, the app is connecting to a
   DIFFERENT project (URL/key mismatch) than the one you edited.

3. **Isolate anonymous sign-in too**:
   ```bash
   curl -s -X POST "https://<ref>.supabase.co/auth/v1/signup" \
     -H "apikey: <publishable_key>" -H "Content-Type: application/json" \
     -d '{}' -w "\nHTTP %{http_code}\n"
   ```
   HTTP 200 + `"is_anonymous":true` = anonymous sign-in enabled and working on
   that project (see P51 for enabling it).

## Why "reinstall the APK" is NOT the answer here
The DB/SQL lives server-side, so a fresh client build cannot change a function
body. If the server is proven correct (steps above) and the client code points at
the right URL, a "stale app" is almost never the cause of a `gen_random_bytes`
error — the function body is served by PostgREST, not bundled in the APK. Suspect
a stale OID cache (Trap 2) or a wrong-project URL before suspecting the client build.

## Real session (SkyPin, ~2026-08-31)
- `create_room` used `gen_random_bytes(6)` → 42883 on Summon.
- Replaced with the pure-SQL md5 token → SQL Editor confirmed correct `prosrc`.
- `notify pgrst, 'reload schema'` → app STILL threw `gen_random_bytes`.
- curl on the exact project URL returned `auth_required` (fixed body IS live).
- Conclusion: PostgREST cached the OLD body by unchanged OID; the fix is DROP + CREATE.
