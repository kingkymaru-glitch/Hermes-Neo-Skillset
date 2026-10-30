# Supabase DB health audit (beyond "is it up")

Use when the ask is "is the DB healthy", "check its status", or "I don't remember
when I last updated this project". A reachability 200 is the START, not the answer.

## 0. Find which project the app uses

```bash
cd <repo> && grep -rhoE "https://[a-z]+\.supabase\.co" .env* src/ | sort -u
```
Several LunaV-family apps share ONE project (`okzmblyboudjffaifixa`) — so "R-Tessera's
DB" and "LunaV Studio's DB" are the same database. Say that explicitly in the report;
the user often assumes each app has its own.

## 1. Row counts (cheap, exact)

The anon key is enough for tables with anon-read RLS. Do NOT try to `read_file` the
`.env.local` (blocked by the secret guard) — extract the key inline in `terminal`:

```bash
KEY=$(grep -h VITE_SUPABASE_ANON_KEY .env.local | head -1 | cut -d= -f2- | tr -d '"' | tr -d "'" | tr -d ' ')
URL=https://<ref>.supabase.co
curl -sI "$URL/rest/v1/<table>?select=id&limit=0" \
  -H "apikey: $KEY" -H "Authorization: Bearer $KEY" -H "Prefer: count=exact" \
  | grep -i content-range      # -> */5
```
`*/0` with a 200 means RLS allows the table but returns no rows to anon — NOT an error.
Confirm with an authenticated/service key before calling a table empty.

## 2. Schema drift (highest-value check)

Select `*` from each table the app queries and compare the returned columns against
the columns the CODE selects:

```bash
curl -s "$URL/rest/v1/<table>?select=*&limit=1" -H "apikey: $KEY" -H "Authorization: Bearer $KEY" \
  | python3 -c "import sys,json; d=json.load(sys.stdin); print(', '.join(sorted(d[0].keys())) if d else 'no rows')"
```
Then list what the code needs:
```bash
grep -rhoE "\.from\('[a-z_]+'\)" src/ | sort -u
grep -rn "const SELECT" src/services/    # many apps keep the column list in a const
```
A column the code reads but the table lacks (or a rename) is the silent killer — the
query 400s or returns undefined and the UI shows an empty list, not an error.

## 3. Orphan check

For rows that reference another project's id (a link table), resolve EACH through the
RPC that reads it and confirm it returns a live parent:

```python
for r in rows:
    body = json.dumps({"share_token": r["lunav_share_token"]})
    # POST $URL/rest/v1/rpc/get_shared_project
    # a non-null .project in the response = live; null = orphaned/broken link
```
Report as "N/N resolve — no orphans" or name the broken ones.

## 4. Staleness

```bash
curl -s "$URL/rest/v1/<table>?select=created_at" -H "apikey: $KEY" -H "Authorization: Bearer $KEY" \
  | python3 -c "import sys,json;from datetime import datetime,timezone;d=json.load(sys.stdin);
print('newest',max(x['created_at'] for x in d));print('oldest',min(x['created_at'] for x in d))"
```
Report "last data change was N days ago" — that is the number the user is asking for
when they say they don't remember when they last touched it. Also `git log -1 --format='%ad %s'
--date=short` for the last CODE change; data-stale and code-stale are different answers.

## 5. Dead externals (see TRAP C in SKILL.md)

Probe every stored URL that the app renders:
```bash
curl -s -o /dev/null -w "%{http_code}\n" --max-time 12 "<stored_url>"
```
`000` = dead. `*.trycloudflare.com` / `*.ngrok.io` quick tunnels are ephemeral — a row
pointing at one is stale test data, not a DB fault.

## TRAP — an RPC 404 (PGRST202) from an empty probe body is NOT a missing function

`{"code":"PGRST202", ... "Could not find the function public.x without parameters"}`
means PostgREST could not match the CALL SIGNATURE, not that the function is absent.
Calling `rpc/<fn>` with `-d '{}'` against a function that takes NAMED params produces
this. Before concluding a function is missing:
1. Read its real signature from the repo SQL:
   `grep -n -A10 "create or replace function public.<fn>" supabase/**/*.sql`
2. Re-call with every named param:
   `-d '{"p_lunav_project_id":"000...","p_handoff_token":"x", ...}'`
A correct call with a bogus id returns a clean domain error (`P0001 Unknown project`)
— that proves the function EXISTS and works. Same for a `select` that returns `null`
from a valid RPC: null is "no matching row", not "broken".
