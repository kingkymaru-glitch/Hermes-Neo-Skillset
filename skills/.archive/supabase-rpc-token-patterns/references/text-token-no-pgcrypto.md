# Short TEXT token without pgcrypto (gen_random_bytes alternative)

`gen_random_bytes(n)` lives in the **pgcrypto** extension (NOT enabled by
default on Supabase), so an RPC body like
`v_token := encode(gen_random_bytes(6),'hex');` compiles fine but THROWS at
call time:

```
PostgrestException: function gen_random_bytes(integer) does not exist
code: 42883
details: not found
HINT: No function matches given name and argument types.
```

This is the same pgcrypto family as `hmac()` (see P42 in `supabase-backend`).
Two no-extension fixes:

1. **UUID token (core PG13+)** — `gen_random_uuid()`, bind by storing on a row.
   Use when the token can be a uuid. Preferred.

2. **Short human-friendly TEXT token** — when you want a compact share code
   (e.g. a 12-hex room token) rather than a uuid, generate one with pure SQL,
   no extension:
   ```sql
   v_token := left(encode(md5(random()::text || clock_timestamp()::text), 'hex'), 12);
   ```
   `md5` + `random()` + `clock_timestamp()` are all core Postgres. `left(...,12)`
   trims the 32-hex md5 to 12 chars. Collision risk for a 12-hex code across a
   small set of active rooms is negligible; the table PK / unique constraint on
   `token` will surface any collision.

**Apply when you can't reach the DB:** re-run the single `create or replace
function` body (same param list → no DROP needed) via the Supabase SQL Editor.
The function signature is unchanged, so `CREATE OR REPLACE` succeeds; only the
body swaps.

## Real session (SkyPin, 2026-08-31)
`create_room` used `gen_random_bytes(6)` for the room token; Summon failed with
`function gen_random_bytes(integer) does not exist, code 42883`. Swapped the
body to `left(encode(md5(random()::text||clock_timestamp()::text),'hex'),12)`,
re-ran the single function in the SQL Editor, and room creation worked.
