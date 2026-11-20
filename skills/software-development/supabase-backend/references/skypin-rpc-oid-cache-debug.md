# PostgREST function OID cache + PL/pgSQL body traps (SkyPin, 2026-08-31)

A Flutter+Supabase app ("create a room" RPC) hit three sequential call-time
failures that all "looked like the same error" but were different bugs. This is
the reproduction + triage recipe. Class-level lessons at the bottom.

## Symptom chain

The app called `create_room` (a SECURITY DEFINER plpgsql function that mints a
room token). Every attempt threw a PostgREST error with code **42883**
("function ... does not exist"), even after the SQL Editor reported "success".
Triage repeatedly concluded "the DB fix didn't land" when actually the DB was
fine — PostgREST was serving a stale body, and later, a NEW 42883/42702 body bug.

## Bug 1 — `gen_random_bytes` needs pgcrypto (not enabled by default)

Original body used `encode(gen_random_bytes(6), 'hex')`. Supabase projects do NOT
enable `pgcrypto` by default, so at call time: `function gen_random_bytes(integer)
does not exist` (42883). Compiles fine (CREATE OR REPLACE is syntax-only).

## Bug 2 — `encode(md5(...), 'hex')` is invalid: md5() returns text, encode() needs bytea

Replaced Bug 1 with `left(encode(md5(random()::text || clock_timestamp()::text),
'hex'), 12)`. That STILL threw 42883:
`function encode(text, unknown) does not exist`.
Cause: `md5()` returns `text`; `encode(text, 'hex')` requires `bytea`; Postgres
won't auto-cast text→bytea. `md5()` ALREADY returns a 32-char lowercase hex
string. The correct, dependency-free form:
```sql
v_token := left(md5(random()::text || clock_timestamp()::text), 12);
```
No `encode`, no extension.

## Bug 3 — PL/pgSQL variable name collides with a column in RETURNING (42702)

`returning id, expires_at into v_id, v_exp` where `expires_at` is BOTH a declared
PL/pgSQL variable and a column of `rooms` → `column reference "expires_at" is
ambiguous` (42702). Fix: qualify the column:
```sql
returning id, rooms.expires_at into v_id, v_exp;
```

## Triage technique — reproduce the app's exact call against the LIVE API

The SQL Editor "ran successfully" is NOT proof the function works at call time:
- `CREATE OR REPLACE` only syntax-checks; body bugs surface when the client calls it.
- A direct `select * from public.create_room('arrow', false)` in the SQL Editor
  runs as **postgres** with NO `auth.uid()`, so it raises `auth_required` and
  never exercises the token-generation body — a misleading pass/fail.

The only way to see the real call-time error is to call the RPC exactly as the
app does: anon sign-in to get a token, then the RPC with that Bearer token. This
works with NO CLI link and NO service-role key — just the public publishable key:
```bash
# 1) anonymous sign-in -> returns access_token
curl -s -X POST "https://<ref>.supabase.co/auth/v1/signup" \
  -H "apikey: <publishable_key>" -H "Content-Type: application/json" -d '{}'
# 2) call the RPC with that token (this is what surfaces 42883/42702)
curl -s -X POST "https://<ref>.supabase.co/rest/v1/rpc/create_room" \
  -H "apikey: <key>" -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{"p_room_skin":"arrow","p_all_app":false}'
```
A 200 with a token row = the fix is LIVE. A 400 with `auth_required` = the
function RAN (correct path, caller just isn't authed). A 42883/42702 body error =
the LIVE body is still buggy (see Bug 2/3) — go read it:
```sql
select oid, pg_get_function_identity_arguments(oid) as args, prosrc
from pg_proc where proname='create_room' and pronamespace='public'::regnamespace;
```
Re-run this after every paste to confirm the body actually changed.

## Triage technique — PostgREST caches functions by OID

`CREATE OR REPLACE` keeps the SAME function OID, and PostgREST caches by OID —
so even after `notify pgrst, 'reload schema'`, the API can keep executing the OLD
body. Signature: the DB body is correct (`select prosrc`), `notify` was run, yet
the client still throws the ORIGINAL error. Fix: **DROP then CREATE** (assigns a
brand-new OID, forcing PostgREST to rebuild):
```sql
drop function if exists public.create_room(text, boolean);
create function public.create_room(...) ...;
notify pgrst, 'reload schema';
```
Rule: for a live-behavior fix to a function the API already called, prefer
DROP+CREATE over CREATE OR REPLACE. (Note: a pure re-DROP+CREATE also forces the
rebuild; you don't strictly need the extra `notify` after a drop, but it's cheap
and harmless.)

## Anonymous sign-in is OFF by default

`signInAnonymously()` / the `/auth/v1/signup` endpoint fails with 422
`anonymous_provider_disabled` unless enabled in the dashboard: **Authentication →
Sign In / Providers → Anonymous Sign-Ins** (toggle + a session-expiration field).
Server-side only — no app rebuild needed. Anonymous users DO get a real
`auth.uid()`, so a server `auth.uid() is null` guard (`raise auth_required`) still
passes; they just have no email/identity. Useful for a dev-only "skip login and
test the loop" gate.

## Class-level lessons
- Read the rpc error MESSAGE, not just the code. 42883 = "function does not
  exist" — could be missing extension (pgcrypto), a bad call-type (encode
  text/bytea), or a stale OID cache. Distinguish by checking the LIVE `prosrc`
  and calling the RPC with a real token.
- `md5()` is a zero-dependency hex generator; don't wrap it in `encode`.
- Name PL/pgSQL variables to avoid colliding with table columns you use in
  `RETURNING`; qualify the column (`rooms.expires_at`) if you can't.
- After ANY change to a function the app calls, verify by reproducing the app's
  call (anon sign-in → rpc), not by "SQL Editor said success".
