# `::regproc` cast false-negative when probing RPC existence

## Symptom
Running:
```sql
select pg_get_functiondef('public.get_shared_project(uuid)'::regproc);
```
returns:
```
Failed to run sql query: ERROR: 42883: function "public.get_shared_project(uuid)" does not exist
LINE 2: select pg_get_functiondef('public.get_shared_project(uuid)'::regproc);
                                                                          ^
```

## Why it misleads
The `::regproc` cast resolves ONLY if a function with that EXACT argument
signature is registered. If the live RPC has a different signature (or a
transient parse quirk), the cast fails and Postgres reports "does not exist" —
even though the RPC exists and the app calls it successfully.

## Correct probe (signature-agnostic)
```sql
select p.oid::regprocedure as signature, pg_get_functiondef(p.oid) as def
from pg_proc p join pg_namespace n on n.oid = p.pronamespace
where n.nspname = 'public' and p.proname = 'get_shared_project';
```
Returned 1 row, signature `get_shared_project(uuid)`: the RPC WAS present.
The original error was a flaw in the check query, not evidence of a missing RPC.

## Lesson
Never conclude an RPC is missing from a `::regproc` cast failure. Use `pg_proc`.
To check body contents without a truncated results blob, use `ilike '%token%'`
booleans (CHECK 2c in scripts/check_supabase_state.sql).
