# Live Supabase RPC probe recipe (curl, anon key)

Probe deployed RPCs WITHOUT the Supabase CLI or SQL Editor — just the app's anon key from
`.env.local` (never commit that file; it's gitignored). Useful for E2E security/function
audits when you can't run DDL.

## Extract key + URL (no commit)
```bash
KEY=$(grep -E "^VITE_SUPABASE_ANON_KEY=" .env.local | cut -d= -f2-)
URL=$(grep -E "^VITE_SUPABASE_URL="      .env.local | cut -d= -f2-)
```

## Probe a single RPC (unauthenticated = authz audit)
```bash
Z="00000000-0000-0000-0000-000000000000"
curl -sS -X POST "$URL/rest/v1/rpc/<fn>" \
  -H "apikey: $KEY" -H "Authorization: Bearer $KEY" -H "Content-Type: application/json" \
  -d '{"<param>":"<value>"}' -w "\nHTTP=%{http_code}\n"
```

## Real transcript — RINA audit (2026)
Goal: confirm every RPC called by `src/lib/api.ts` exists live AND rejects non-admins.

`approve_organization` (unauth, correct args):
  -> HTTP 400, {"message":"Only the platform admin can approve companies."}  exists+guarded

`is_platform_admin` (unauth, {}):
  -> HTTP 200, false  exists, correctly false

`fetch_orgs_with_creator` (unauth, {}):
  -> HTTP 400, {"message":"Only the platform admin can list companies."}  exists+guarded

`delete_organization` / `set_org_paused` / `master_admin_enter_org` (unauth, named args):
  -> HTTP 400, guard messages  exists+guarded

`upsert_user_profile` (unauth, {org, payload}):
  -> HTTP 400, {"message":"Not authorized to edit users in this organization"}  exists+guarded

`delete_user_profile` / `restore_user_profile` (unauth, {org, target}):
  -> HTTP 404 for every param-shape variant  NOT deployed (app buttons fail)

## Interpretation cheat-sheet
- HTTP 400 + DOMAIN guard message -> function EXISTS and is GUARDED (correct).
- HTTP 200 with a real value -> function EXISTS (e.g. is_platform_admin -> false).
- HTTP 202 PGRST202 "without parameters ... no matches" -> you sent {} to a
  function that REQUIRES params. Resend with realistic named args; NOT proof of absence.
- HTTP 404 for every param variant -> function genuinely NOT deployed.

## Caveat
Unauth calls only prove the RPC rejects anonymous callers. To prove it ALSO rejects a
logged-in non-admin, you'd need a real session token — out of scope for a quick probe.
RLS policies (e.g. tasks scoped to my_org_ids()) still back the row-level guarantee.
