# PostgREST function-OID cache + PL/pgSQL traps (real SkyPin debugging session)

Three non-obvious traps that each caused multi-round "DB is correct but app still fails"
confusion. All three appeared in ONE session while fixing a single `create_room` RPC.

## 1. PostgREST caches functions BY OID — `CREATE OR REPLACE` won't go live
`CREATE OR REPLACE FUNCTION` keeps the SAME function OID. PostgREST caches function
bodies keyed by OID, so after replacing a body you can keep getting the OLD behavior
even after `notify pgrst, 'reload schema';` (reload only rebuilds for NEW/changed OIDs).

- `select prosrc from pg_proc where proname=...` showed the NEW body.
- SQL Editor confirmed the new body, `reload schema` ran, yet the app STILL threw the OLD error.
- Root cause: same OID → PostgREST cache not invalidated.

FIX — DROP + CREATE (new OID forces PostgREST to rebuild):
```sql
drop function if exists public.create_room(text, boolean);
create function public.create_room(...) returns ... as $$ ... $$;
notify pgrst, 'reload schema';
```
`drop function if exists public.<fn>(<exact current arg types>)` + a FRESH `create
function` (NOT `create or replace`).

CRITICAL VALIDATION: prove the fix at the API layer the app actually uses, NOT the DB.
Call the RPC through an authenticated anon-key session and read the response. A
`prosrc`/`pg_proc` check proves the DB, not what PostgREST serves. Reproduce the app's
exact request (anon sign-in → RPC) and read the real error — that ends the loop.

## 2. `encode(md5(...), 'hex')` fails: md5() already returns hex text
`md5(...)` returns type `text` (32-char lowercase hex). `encode(md5(...),'hex')` throws
at RUNTIME `function encode(text, unknown) does not exist` (42883) because `encode()`
needs a `bytea` first arg and text can't auto-cast. Looks identical to a
`gen_random_bytes` failure (both 42883) but is a DIFFERENT cause.

FIX — no encode needed; md5 already yields hex:
```sql
v_token := left(md5(random()::text || clock_timestamp()::text), 12);
```

## 3. PL/pgSQL RETURNING variable/column ambiguity (42702)
A DECLARE variable sharing a name with a table column used in INSERT ... RETURNING is
ambiguous: `ERROR: 42702: column reference "expires_at" is ambiguous`. Qualify the column:
```sql
insert into public.rooms (...) values (...) returning id, rooms.expires_at into v_id, v_exp;
```

## Debugging pattern that finally worked
1. Confirmed DB function body via `pg_proc` (clean) — but DB-correct ≠ API-correct.
2. Reproduced the app's exact flow from the CLI: `POST /auth/v1/signup {}` to get an
   anonymous `access_token`, then `POST /rest/v1/rpc/create_room` with
   `Authorization: Bearer <token>`. This surfaced the REAL runtime error (42702/42883)
   that the app was masking, and proved once the fix landed (HTTP 200 + token row).
3. Iterated: each SQL paste → re-probe from CLI before telling the user to retest.

This is the FastLane-skill version of "validate from the client, not the DB" — see the
`supabase-migration-verify` skill's live RPC probe recipes for the curl/anon-key forms.
