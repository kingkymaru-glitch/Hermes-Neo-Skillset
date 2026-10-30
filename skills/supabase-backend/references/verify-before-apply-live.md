# Verify a Supabase migration BEFORE applying it live

Use this whenever a user pastes a "paste into SQL Editor → Run" migration and
worries "what if it's already applied?" or "don't run it just to discover it
was already done." The apply script is usually idempotent (`add column if not
exists`, `create or replace function`) so blind-running is *safe*, but a
read-only **status check** still earns its keep: it tells you if the feature is
currently working on live (e.g. autosave silently failing) and avoids a
noisy/wrong "success" that hides a real state.

## The check sequence (read-only — no mutations)

Run in Supabase Dashboard → SQL Editor. Each step answers one question.

```sql
-- CHECK 1: do the target columns already exist on live?
select column_name, data_type, column_default
from information_schema.columns
where table_schema = 'public'
  and table_name  = 'markers'          -- <-- swap table
  and column_name in ('client_comment','action_needed');  -- <-- swap cols
-- 0 rows  => columns NOT on live  => apply needed
-- 2 rows  => columns present       => add-column lines will be no-ops

-- CHECK 2: is the RPC already upgraded to emit the new fields?
--          DO NOT use ::regproc with an assumed signature — see gotcha below.
select pg_get_functiondef('public.get_shared_project(uuid)'::regproc);
-- ERROR 42883 "function ... (uuid) does not exist" is a FALSE NEGATIVE if the
-- real signature differs (e.g. (share_token text)). Go to CHECK 2b instead.

-- CHECK 2b (signature-agnostic): list EVERY overload + body
select p.oid::regprocedure as signature,
       pg_get_functiondef(p.oid) as def
from pg_proc p
join pg_namespace n on n.oid = p.pronamespace
where n.nspname = 'public'
  and p.proname = 'get_shared_project';   -- <-- swap fn name
-- 0 rows  => RPC genuinely absent  => apply whole script
-- 1+ rows => RPC exists; scan def for the new field names

-- CHECK 2c (compact boolean — use when 2b's def column truncates in the UI):
select
  pg_get_functiondef(p.oid) ilike '%client_comment%' as has_client_comment,
  pg_get_functiondef(p.oid) ilike '%action_needed%'  as has_action_needed
from pg_proc p
join pg_namespace n on n.oid = p.pronamespace
where n.nspname = 'public'
  and p.proname = 'get_shared_project';
-- true/true  => already upgraded, do NOT apply
-- false/false=> old RPC, apply ONLY the create-or-replace fn block
--              (skip the already-done add-column lines)

-- CHECK 3: confirm we are pointed at the right project (not a stale ref)
select current_database();
```

## GOTCHA — the `::regproc` 42883 false negative

`pg_get_functiondef('public.fn(uuid)'::regproc)` only resolves if a function
with that **exact** signature exists. If the live fn has a different signature,
Postgres throws `42883: function "public.fn(uuid)" does not exist` — which looks
identical to "the RPC is missing" but is NOT proof of absence. The app may well
be calling a working RPC with another signature. Always follow a 42883 with the
signature-agnostic CHECK 2b/2c before concluding anything.

## Apply decision matrix

| CHECK 1 | CHECK 2c            | Action                                  |
|----------|---------------------|-----------------------------------------|
| 0 rows   | n/a (no fn or old)  | Apply WHOLE script (cols + fn).         |
| 2 rows   | false/false         | Apply ONLY the `create or replace fn` block; skip add-column lines. |
| 2 rows   | true/true           | Do NOT apply. Just commit the file for backup. |

## Why the CLI path is often blocked (Supabase)

The skill's `supabase db query --linked` route runs SQL via the Management API
using the *logged-in* CLI account. If that account isn't the project owner,
`supabase link --project-ref <ref>` returns "Your account does not have the
necessary privileges" and `supabase projects list` won't even show the project.
In that case the read-only check + apply MUST run in the Dashboard SQL Editor
(project's own privileged connection). To let the agent self-apply instead, the
user runs `supabase login` (browser OAuth into the owner account) first.

## Standing rule for this user

Never `git push` a DB/schema change without an explicit "go". `git add` + commit
for backup is fine unprompted; push is not.
