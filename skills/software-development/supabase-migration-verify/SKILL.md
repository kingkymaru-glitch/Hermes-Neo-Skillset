---
name: supabase-migration-verify
description: Verify Supabase schema/RPC state READ-ONLY before applying a migration. Covers the add-column-if-not-exists / create-or-replace-function idempotent apply pattern, the dangerous `::regproc` cast false-negative pitfall when probing RPC existence, and the Dashboard SQL Editor fallback when the supabase CLI is blocked from the target project. Use whenever you have a Supabase SQL migration (new columns, RPCs, schema changes) to apply and need to know current live state first, or when `supabase link`/`db query` fails with "no privileges".
category: software-development
---

# Supabase Migration Verify (check-then-apply)

## When to use
- You have a SQL migration file (new columns, `create or replace function`, RLS) to apply to a Supabase Postgres DB.
- You need to know CURRENT live state before applying — e.g. "was this already done?", "is the RPC upgraded?", "will this ALTER error?".
- The `supabase` CLI is logged into a different account / lacks privileges, so `supabase db query --linked` or `supabase link` fail.

## Core mechanism — STATUS CHECK ≠ APPLY
These are two DIFFERENT operations; never conflate them:
- STATUS CHECK = pure `SELECT`s against `information_schema` / `pg_catalog`. Read-only. Tells you current state. Does NOT change anything.
- APPLY = `ALTER` / `CREATE OR REPLACE` / `GRANT`. Mutates. Does NOT report prior state.

Pasting an apply script does NOT answer "was it already done?". You must run the SELECTs separately. A verified state is also the only thing that dissolves the "don't apply only to find it was already done" worry — and because apply scripts are idempotent, that worry is structurally impossible to act on harmfully anyway (see below).

## Idempotent apply pattern (so apply-twice is safe)
Write migrations so re-running is a no-op:
- `alter table public.<t> add column if not exists <c> <type> default <v>;`
- `create or replace function public.<fn>(<sig>) returns <t> language sql security definer set search_path=public stable as $$ ... $$;`
- `grant execute on function public.<fn>(<sig>) to anon, authenticated;`

PITFALL: `create or replace function` only works if the argument SIGNATURE is identical. A signature mismatch errors with "cannot change argument types" — do NOT blindly `drop` the function; inspect the live signature first (see pitfall below) and handle the mismatch separately.

## Runtime RPC-existence + authz probe (anon-key, two forms)  [2026-08-18]
When you CANNOT run SQL (CLI blocked, no Dashboard access) but the app's anon Supabase
key IS available, you can prove an RPC EXISTS and is GUARDED at runtime by calling it.

FORM A — Node script (uses the app's `@supabase/supabase-js` from repo `node_modules`):
```js
const { createClient } = require('@supabase/supabase-js');
const sb = createClient(URL, ANON);
const r = await sb.rpc('mint_handoff_token', { p_project_id: '00000000-0000-0000-0000-000000000000' });
console.log(r.error?.message);
```
- DOMAIN error ("Unknown project" / "Not project owner" / "Only the platform admin…") → function RAN → EXISTS.
- "function … does not exist" / "Could not find the function … in the schema cache" → MISSING
  (or the param NAME you passed doesn't match its signature — `rpc('fn',{p_token})` looks for a
  param literally named `p_token`; if the live fn uses `share_token`, call with `{share_token:…}`
  or you'll get a false "not found").

FORM B — raw curl against the REST RPC endpoint (no Node deps; works from any shell with the
anon key). Pull the key/URL from the app's `.env.local` WITHOUT committing it:
```bash
KEY=$(grep -E "^VITE_SUPABASE_ANON_KEY=" .env.local | cut -d= -f2-)
URL=$(grep -E "^VITE_SUPABASE_URL="      .env.local | cut -d= -f2-)
curl -sS -X POST "$URL/rest/v1/rpc/approve_organization" \
  -H "apikey: $KEY" -H "Authorization: Bearer $KEY" -H "Content-Type: application/json" \
  -d '{"target":"00000000-0000-0000-0000-000000000000","approve":true}' -w "\nHTTP=%{http_code}\n"
```
Same interpretation as Form A: DOMAIN guard message + HTTP 400 = exists & guarded;
`PGRST202 "…without parameters…no matches were found"` = you sent `{}` to a function that
REQUIRES params (NOT proof of absence — resend with realistic named args); `HTTP 404` on every
param-shape variant = function genuinely NOT deployed.

PITFALL — empty `{}` masks existence for parameterized RPCs  [CRITICAL]
Calling `curl -X POST …/rpc/delete_organization -d '{}'` returns
`PGRST202 … without parameters … no matches were found` even when the function EXISTS,
because PostgREST can't bind the empty arg list to its required signature. ALWAYS send
plausible named args matching the app's call shape (e.g. `{"target":"<uuid>"}`,
`{"target":"<uuid>","paused":true}`, `{"org":"<uuid>","payload":{}}`). A true absence
returns `HTTP 404` (not 202) for every variant tried.

AUTHORIZATION audit: call each privileged RPC as an UNAUTHENTICATED caller (just the anon key,
no session). A correctly-guarded `SECURITY DEFINER` RPC raises its guard exception
("Only the platform admin…", "Not authorized to edit users…") → proves the server rejects
non-admins. If it SUCCEEDS or returns data instead, the RPC is unguarded — a security hole to flag.

This is the app-level equivalent of the `pg_proc` probe and avoids the `::regproc`
false-negative entirely. It also works for tables: `sb.from('project_nodes').select('id').limit(1)`
→ error means missing/absent; no error + `data:[]` means the table EXISTS. Run the script
from the app repo dir so `node_modules` resolves, or copy the `.cjs` into the repo and
delete it after (never commit the throwaway probe).

## Find MISSING RPC definitions (api.ts ↔ SQL diff)  [2026-08-18]
The app calls RPCs that may not be committed anywhere in the repo's `supabase/*.sql`. To find
which called RPCs have NO on-disk definition (and thus might be undeployed):
```bash
# RPCs DEFINED in repo SQL
grep -rhE "create or replace function public\.[a-z_]+" supabase --include=*.sql \
  | sed -E 's/.*function public\.([a-z_]+).*/\1/' | sort -u
# RPCs CALLED in the api client
grep -oE "supabase\.rpc\('[a-z_]+'" src/lib/api.ts | sed -E "s/supabase.rpc\('//" | sort -u
```
Diff the two lists. Any called RPC absent from the defined list is a candidate for "deployed
out-of-band / missing" — the live probe above (404 = truly missing; guard message = deployed
but not in version control) settles it. When missing, write the SQL to the user's Desktop
(you cannot run DDL; see house rule) and have them paste it into the Supabase SQL Editor.

## PITFALL — `::regproc` cast gives a FALSE "does not exist"  [CRITICAL]
Do NOT probe an RPC's existence like this:
```sql
select pg_get_functiondef('public.get_shared_project(uuid)'::regproc);
```
If no overload with EXACTLY that signature is registered, Postgres throws:
```
ERROR: 42883: function "public.get_shared_project(uuid)" does not exist
```
This does NOT prove the RPC is absent — it only means the `(uuid)` cast didn't match (different signature, or a transient parse quirk). The function can still exist and be called fine by the app. In one session this exact error was treated as "RPC missing" — but a signature-agnostic probe then returned 1 row proving the RPC WAS live.

CORRECT, signature-agnostic probe:
```sql
select p.oid::regprocedure as signature, pg_get_functiondef(p.oid) as def
from pg_proc p
join pg_namespace n on n.oid = p.pronamespace
where n.nspname = 'public' and p.proname = 'get_shared_project';
```
To check whether a function body ALREADY contains a column/keyword (and avoid reading a truncated `def` blob in the results panel), use a boolean `ilike`:
```sql
select pg_get_functiondef(p.oid) ilike '%client_comment%' as has_client_comment,
       pg_get_functiondef(p.oid) ilike '%action_needed%'  as has_action_needed
from pg_proc p
join pg_namespace n on n.oid = p.pronamespace
where n.nspname = 'public' and p.proname = 'get_shared_project';
```
See references/regproc_false_negative.md for the full error transcript.

## PITFALL — `hmac()` / `encode()` need the `pgcrypto` extension (often OFF)
`hmac(text, text, text)` and `encode(...)` for crypto live in the `pgcrypto`
extension, which is NOT enabled by default on Supabase. A function that uses them
will `create or replace` fine (DDL succeeds) but throw at RUNTIME:
`function hmac(text, text, unknown) does not exist` → the calling RPC returns 404.
This looks like "function missing" but the real cause is the missing extension.
**Fix without pgcrypto:** use `gen_random_uuid()` (core Postgres 13+, no extension)
to mint a random token, store it on the row, and verify binding in the consumer
RPC by comparing to the stored value. Pattern (handoff token for a geo-link):
```sql
create or replace function public.mint_handoff_token(p_project_id uuid)
returns text language plpgsql security definer set search_path=public as $$
declare v_owner uuid; v_token uuid := gen_random_uuid();
begin
  select owner_id into v_owner from public.projects where id = p_project_id;
  if v_owner is null then raise exception 'Unknown project'; end if;
  if v_owner <> auth.uid() then raise exception 'Not project owner'; end if;
  update public.projects set handoff_token = v_token where id = p_project_id;
  return v_token::text;
end; $$;
```
Then `upsert_project_node` checks `p_handoff_token = (select handoff_token::text
from projects where id = p_lunav_project_id)`. Avoids pgcrypto entirely.

## Verify a build's output chunks parse (catches minifier-emitted syntax errors)
`next build` / `vite build` can PASS while a production chunk contains an illegal
strict-mode escape (e.g. `\0` in a template literal from a bundled lib like
Cesium) that only breaks in the browser. After any build that bundles a heavy
3rd-party lib, run `node --check` over the emitted chunks:
```bash
for f in .next/static/chunks/*.js; do node --check "$f" 2>/tmp/e || grep -qi "octal\|numeric escape\|SyntaxError" /tmp/e && echo "BROKEN $f"; done
```
Expect: no "BROKEN" lines. (Companion to the Cesium-CDN note in `lunav-studio`.)

## Column-existence check
```sql
select column_name, data_type, column_default
from information_schema.columns
where table_schema='public' and table_name='<t>'
  and column_name in ('<c1>','<c2>');
```
0 rows = not present (apply needed). >=1 rows = present (skip ALTER).

## CLI-blocked fallback → Dashboard SQL Editor
When `supabase link --project-ref <ref>` returns "Your account does not have the necessary privileges", the CLI cannot reach the target project. The Supabase Dashboard → SQL Editor uses the project's own privileged connection, so all the SELECTs/APPLY above still run there. Paste SQL into Dashboard → SQL Editor → Run. This is read-only-safe for the checks and is the standard manual-apply path for projects where Vercel/CI migrations don't run.

## Workflow
1. Run the status checks (columns via `information_schema`; RPC via `pg_proc`; optionally `current_database()` to confirm project identity).
2. Interpret: present → skip; absent → apply only the needed part (column ALTERs vs just the function body).
3. Apply minimally. Keep the full migration file for backup (`git add`, but NEVER push without explicit "go").
4. Confirm the on-disk migration file is byte-identical to what you paste — verify with `read_file` before telling the user to paste, so backup == applied.

## Validate a supplied credential by CALLING it — never by its shape
Same principle as the probes above, applied to keys. When the user hands over a
`service_role` key or a storage credential, guessing from its appearance wastes a
turn in one of two opposite ways:

- **Falsely rejecting a good key.** A value pasted through a rich-text editor,
  terminal wrap, or a screenshot can be *displayed* elided (`eyJhbG..._7_8`) while
  the stored bytes are complete. Read the RAW bytes before concluding anything
  (`textutil -convert txt -stdout file.rtf`, or strip RTF control words) — never
  judge from how a value was rendered to you. A Supabase JWT is self-describing:
  base64-decode the middle segment and confirm `ref` matches the project and
  `role` is the expected one.
- **Falsely accepting a bad one.** A hash-looking value can be the wrong field.
  Provider IDs are short and fixed-length, a bucket is a human-readable name, and
  only the secret is long — so a set of uniformly long hex strings is a red flag,
  not a credential. A 64-char string cannot be an account ID: it will not even
  form a valid DNS label.

**The only proof is a live call.** Hit the real endpoint and report the status:
```bash
KEY='<service_role jwt>'; URL='https://<ref>.supabase.co'
curl -s -o /dev/null -w "tables: %{http_code}\n" "$URL/rest/v1/<table>?select=id&limit=1" \
  -H "apikey: $KEY" -H "Authorization: Bearer $KEY"
curl -s -o /dev/null -w "rpc:    %{http_code}\n" -X POST "$URL/rest/v1/rpc/<service_only_fn>" \
  -H "apikey: $KEY" -H "Authorization: Bearer $KEY" -H "Content-Type: application/json" -d '{...}'
```
A `200` on a table read proves both the key AND that the migration landed; `204` on
a `service_role`-only RPC proves the privilege split is correct. Do BOTH directions
— confirm the good key works AND that the suspect one fails, with the real error.
Then state plainly which earlier claim was wrong. Shape-based reasoning produces
confident wrong answers in both directions.

## Object storage — check the project's own store before demanding an external one
`GET <url>/storage/v1/bucket` with the service key returns the bucket list. A `200`
with `[]` is an EMPTY but AVAILABLE store — you can create a bucket and skip an
entire external provider (and its credential trip) for small artifacts. Only reach
for a dedicated object store when the payloads are large or egress-heavy.

## Support files
- scripts/check_supabase_state.sql — the full read-only check block (CHECK 1 / 2b / 2c / 3), ready to paste into Dashboard with placeholder tokens.
- references/regproc_false_negative.md — the exact error transcript + why it misleads.
- references/live_rpc_probe_recipe.md — curl/anon-key recipe + real RINA audit transcript proving RPC existence + guard rejection (HTTP 400 guard vs HTTP 404 missing vs PGRST202 empty-arg trap).
