# Introspect a live Supabase schema when the SDK hides the error

## Problem
The JS SDK often returns an OPAQUE error on auth/DB writes:
`{ name: "AuthRetryableFetchError", message: "{}", status: 500 }`
or `error: {}` with no `message`. This masks the REAL Postgres cause
(e.g. a NOT NULL / FK violation). You cannot fix what you can't see.

## Fix — hit the raw REST endpoint
Supabase is just a PostgREST + GoTrue API. Call it directly with the
`apikey` header (the anon key is fine for reads/probes) to get the true
`code` + `message`.

Example — decode a failing signup:
```js
const https = require('https');
const URL = process.env.VITE_SUPABASE_URL;        // https://<ref>.supabase.co
const KEY = process.env.VITE_SUPABASE_ANON_KEY;
const body = JSON.stringify({ email, password });
const req = https.request(URL + '/auth/v1/signup', {
  method: 'POST',
  headers: { apikey: KEY, 'Content-Type': 'application/json', Authorization: 'Bearer ' + KEY },
}, res => {
  let d = ''; res.on('data', c => d += c);
  res.on('end', () => console.log('STATUS', res.statusCode, 'BODY', d));
});
req.write(body); req.end();
```
Real error surfaces as:
`{"code":"23502","message":"null value in column \"organization_id\" ... violates not-null constraint"}`
→ now you can fix the actual cause, not guess.

## Confirm a column exists when RLS blocks `select *`
Unauthenticated (anon) reads are blocked by RLS, so `select *` returns `[]`
with NO error — that does NOT prove columns exist. To verify a column name,
run a **non-destructive** `select <col>` as an authenticated (or anon) client.
A successful empty result (`data: []`, `error: null`) proves the column is
valid; a 404/"column does not exist" proves it is not. This is how we proved
`tasks.data` exists but `notifications.data` does NOT (both returned no error
on the column-specific select, yet the app's `insert { data: ... }` into
`notifications` threw at runtime).

## `.env.local` parsing pitfall (Node scripts)
When sourcing creds from `.env.local` for a throwaway Node script, the lines
may carry trailing CR / control chars that corrupt the URL and make
`createClient` throw `Invalid supabaseUrl: Provided URL is malformed.`
Sanitize: `val.replace(/[^ -~]/g,'').trim()` after the regex capture.

## Trigger / PK coherence pitfall
If you ALTER a table's PK to a composite `(id, org)` with the new column
NOT NULL, AUDIT every `on auth.user_created` / `on auth.users` trigger that
inserts into that table. A leftover branch that inserts `organization_id =
NULL` will throw on every signup (23502) once the NOT NULL lands. Triggers
must either carry the org id or be a no-op when there is no company context
(RPCs like `create_org`/`join_org` can own profile creation instead).
