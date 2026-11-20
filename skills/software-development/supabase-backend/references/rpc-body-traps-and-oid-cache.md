# RPC body traps (pgcrypto, encode/md5, RETURNING ambiguity) + PostgREST OID cache

Three adjacent traps that bit SkyPin (Flutter AR app, shared rina-platform project,
~2026-08-31) while debugging "Summon SkyPin fails". They all produce `42883` or
`42702`, which makes sequential bugs look like "the same error" — the REAL
technique is to reproduce the **authenticated** RPC flow via REST to surface the
actual live body error (see "THE technique" below), not to re-run the app each time.

> NOTE: this file SUPERSEDES `references/rpc-body-pgcrypto-and-oid-cache.md`,
> which documented `encode(md5(...),'hex')` as the fix — that form is itself
> broken (Trap 1b). The correct fix is `left(md5(...), 12)`, no `encode()`.

## Trap 1 — `gen_random_bytes(integer)` does not exist (42883)

**Symptom (Flutter):**
```
Summon failed: PostgrestException (message: function gen_random_bytes(integer)
does not exist, code 42883, details: not found, Hint: No function matches given
name and argument types...)
```

**Root cause:** the RPC body calls `gen_random_bytes(6)`. `gen_random_bytes()` is
provided by the `pgcrypto` extension, which Supabase projects do NOT enable by
default. `gen_random_uuid()` is core Postgres 13+ and IS available; the
`gen_random_bytes()` variant is pgcrypto-only. Same family as P42 (`hmac`/`crypt`).

## Trap 1b — "Fix it" with `encode(md5(...),'hex')` is ITSELF broken (42883)

**DO NOT use `encode(md5(...), 'hex')`.** `md5()` returns `text`; `encode(text, 'hex')`
is invalid because `encode()` requires a `bytea` first argument. The SQL Editor
accepts it (CREATE succeeds — the body is never validated), but calling the RPC
throws `function encode(text, unknown) does not exist` (42883). **Same error code
as Trap 1**, so the app keeps showing "same failure" and you think the original fix
never landed.

**Correct, dependency-free token (md5 already returns a 32-char lowercase hex
string — no `encode()` needed):**
```sql
v_token := left(md5(random()::text || clock_timestamp()::text), 12);
```
`md5()` is core; `random()::text || clock_timestamp()::text` gives high-cardinality
entropy; `left(..., 12)` yields a 12-char hex room token. Works on every Postgres.

## Trap 1c — `RETURNING id, expires_at` is AMBIGUOUS if `expires_at` is also a PL/pgSQL variable (42702)

If the function has `declare v_exp timestamptz;` AND does
`returning id, expires_at into v_id, v_exp`, Postgres throws
`column reference "expires_at" is ambiguous` (42702) because `expires_at` names
BOTH a variable (in scope) and a table column. **Fix: qualify the column with the
table name in the RETURNING clause:**
```sql
returning id, rooms.expires_at into v_id, v_exp;
```
Any column name that collides with a DECLARE variable MUST be qualified. (Bare
`v_exp` in the final `return query select` is fine — that's a local, unambiguous.)

## Trap 2 — PostgREST serves the STALE body even after `CREATE OR REPLACE` + `notify pgrst, 'reload schema'`

**This is the time-waster.** You fix the body (Trap 1b), re-apply, `notify pgrst,
'reload schema';`, the SQL Editor even confirms `prosrc` is now the md5 version —
yet the app STILL throws the old error.

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
  v_token := left(md5(random()::text || clock_timestamp()::text), 12);
  insert into public.rooms (token, creator_id, room_skin, all_app)
  values (v_token, auth.uid(), p_room_skin, p_all_app)
  returning id, rooms.expires_at into v_id, v_exp;
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

## THE technique — reproduce the AUTHENTICATED flow via REST to get the REAL body error

An unauthenticated `curl .../rpc/create_room` returns `auth_required` (HTTP 400)
REGARDLESS of whether the body is fixed — so it's a FALSE PASS that tells you
nothing about the body. The definitive move is to replay the app's exact two-step
flow: anonymous sign-in, THEN call the RPC WITH the returned access token. That
surfaces the actual live body error (e.g. `encode(text,unknown)` or the 42702
ambiguity) that the app reports only as an opaque code. Do this in `execute_code`
(Python stdlib, no deps):

```python
import json, urllib.request
URL = "https://<ref>.supabase.co"; KEY = "<publishable_key>"
def req(path, data, token=None):
    r = urllib.request.Request(URL+path, data=json.dumps(data).encode(),
        headers={"apikey":KEY,"Content-Type":"application/json",
                 "Authorization":f"Bearer {token or KEY}"})
    try:
        with urllib.request.urlopen(r) as resp: return resp.status, resp.read().decode()
    except urllib.error.HTTPError as e: return e.code, e.read().decode()
s, body = req("/auth/v1/signup", {})                       # step 1: anon sign-in
tok = json.loads(body).get("access_token","")
s, body = req("/rest/v1/rpc/create_room", {"p_room_skin":"arrow","p_all_app":False}, tok)
print(s); print(body[:500])                                 # step 2: real body error
```
- HTTP 200 + a JSON token row = function WORKS end-to-end. Done.
- `function encode(text, unknown) does not exist` = Trap 1b still present.
- `column reference "expires_at" is ambiguous` = Trap 1c still present.
- `gen_random_bytes does not exist` = Trap 1 (or a stale OID, Trap 2).

Anonymous sign-in returns HTTP 200 + `"is_anonymous":true` when enabled.
Keep this probe script handy; after every SQL paste, re-run it BEFORE the user taps
the button to catch the next sequential bug instantly.

## Diagnostic that separates "server wrong" from "app hitting wrong project"
1. **Test the RPC directly in the SQL Editor** (bypasses the app):
   `select * from public.create_room('arrow', false);`
   A `P0001: auth_required` proves the CURRENT db body reached the `auth.uid()` guard
   (so no extension error) — but is NOT proof PostgREST serves it (OID cache, Trap 2).
2. **Check which database you're actually in:** `select current_database();`
   (always returns `postgres` — the project's primary DB name is `postgres` for every
   project, so this does NOT identify the project; it's the project REF/URL that does).
3. **List every `create_room` (proves no second/stale copy):**
   ```sql
   select oid, pg_get_function_identity_arguments(oid) as args, prosrc
   from pg_proc where proname = 'create_room' and pronamespace = 'public'::regnamespace;
   ```
   ONE row, `prosrc` = md5 = DB clean. Two rows = one stale copy is being resolved.
4. **Confirm the app hits the project you edited** — the URL/key in the client must
   match the ref you pasted SQL into. A clean DB + an app still throwing the old body
   error usually means a wrong-project/URL/key mismatch OR the OID cache (Trap 2).

## Why "reinstall the APK" is NOT the answer here
The DB/SQL lives server-side, so a fresh client build cannot change a function
body. If the server is proven correct (authenticated probe above) and the client
code points at the right URL, a "stale app" is almost never the cause of a body
error — the function body is served by PostgREST, not bundled in the APK. Suspect
the OID cache (Trap 2), a body bug (Trap 1b/1c), or a wrong-project URL before the
client build.

## Real session (SkyPin, ~2026-08-31) — three sequential bugs, all "same code"
- `create_room` used `gen_random_bytes(6)` → 42883 (Trap 1).
- "Fix" `encode(md5(...),'hex')` → STILL 42883, but now `encode(text,unknown)`
  (Trap 1b). Same code hid the difference.
- Authenticated probe surfaced `column "expires_at" is ambiguous` 42702 (Trap 1c).
- Applied DROP+CREATE with `left(md5(...),12)` + `rooms.expires_at` + reload →
  authenticated probe returned HTTP 200 with a real token row. Verified working.
- PostgREST OID-cache behavior confirmed: `CREATE OR REPLACE` + reload did NOT
  clear a stale body; DROP+CREATE did (Trap 2).
