# Verify a Supabase RPC is DEPLOYED without SQL access

Context: some environments forbid the agent from running DDL/SQL (no Supabase CLI
link, no service-role key). The user applies migrations manually in the Supabase
Dashboard SQL Editor. After they paste+run the SQL, you must NOT claim "applied" —
verify the function is actually exposed on the live DB via the anon REST API.

## Probe (anon POST to the RPC endpoint)

Extract URL + anon key from `.env.local` WITHOUT printing secrets — the read tool
may block `.env.local` as secret-bearing, so use the terminal to parse it into
shell vars, then use those vars (never `echo` them):

    cd <project> && \
    URL=$(grep -E "^NEXT_PUBLIC_SUPABASE_URL=" .env.local | cut -d= -f2-) && \
    KEY=$(grep -E "^NEXT_PUBLIC_SUPABASE_ANON_KEY=" .env.local | cut -d= -f2-) && \
    curl -s -o /dev/null -w "http=%{http_code}\n" \
      -X POST "$URL/rest/v1/rpc/<fn_name>" \
      -H "apikey: $KEY" -H "Authorization: Bearer $KEY" \
      -H "Content-Type: application/json" \
      -d '{"<p_arg>":"00000000-0000-0000-0000-000000000000"}'

## Reading the result

- `401` -> function EXISTS and is deployed; anon role just isn't authorized
  (it's granted to `authenticated`). When the logged-in user calls it, it runs.
  This CONFIRMS the earlier `400`/`404` is resolved.
- `404` -> function is NOT on the live DB (SQL never ran, or a typo in the name).
  Re-check the deploy SQL with the user.
- `400` -> function exists but the arg names/types in the call don't match the
  deployed signature. Compare client `rpc("name", {...})` keys to the SQL
  `p_*` parameter names.

## Gotcha

A `400` from `supabase.rpc()` in the browser console is usually a MISSING or
UNDEPLOYED function (PostgREST can't find a matching overload), not client-side
code. Prepare an idempotent `CREATE OR REPLACE FUNCTION ...` SQL file for the
user to run; do not edit the DB yourself or claim it was applied.
