# Supabase anon reachability probe

## `/healthz` returns 401 even when the DB is ALIVE
`GET https://<ref>.supabase.co/healthz` answers 401 because it is auth-gated. A 401 here
does NOT mean the DB is down. Do not report "database down" off a 401 from /healthz.

## Real "is the DB up" signal — table select with anon key
Read the anon key without printing it (see secret-file-read-guard.md):
```
KEY=$(grep VITE_SUPABASE_ANON_KEY .env.local | cut -d= -f2)
URL=$(grep VITE_SUPABASE_URL .env.local | cut -d= -f2)
curl -sS -o /dev/null -w "%{http_code}\n" \
  "$URL/rest/v1/<table>?select=id&limit=1" \
  -H "apikey: $KEY" -H "Authorization: Bearer $KEY"
```
  - HTTP 200 → DB up AND that table allows anon read (RLS permits it).
  - HTTP 404 / 401 on a specific table → usually means that table has NO anon-read RLS
    policy (not that the DB is dead). To confirm the DB itself is up, probe a table you
    KNOW allows anon reads — for RINA that was `organizations` (returned 200 while
    `profiles` returned 404 because profiles blocks anon read).

## Pattern
1. Probe a known-anon-readable table → proves DB + auth gateway live.
2. Probe the app-critical tables separately → distinguish "DB down" from "RLS blocks
   anon" (the latter is expected and not a health problem).

## Gotcha
`supabase/.temp/project-ref` holds the ref too, but `.env.local` is the source of truth
for the live URL+key.
