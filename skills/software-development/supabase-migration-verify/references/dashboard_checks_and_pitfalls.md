# Dashboard SQL Editor — check sequence + pitfalls

## The full check sequence (LunaV session, 2026-08)
When the `supabase` CLI is blocked from the target project (`supabase link`
returns "no privileges"), run these read-only SELECTs in
Supabase Dashboard → SQL Editor. Order matters — each step either clears a
false alarm or tells you whether to apply.

1. **CHECK 1 — columns exist?**
   ```sql
   select column_name, data_type, column_default
   from information_schema.columns
   where table_schema='public' and table_name='<t>'
     and column_name in ('<c1>','<c2>');
   ```
   0 rows = absent (apply needed). >=1 = present (skip ALTER).

2. **CHECK 2 (WRONG) — do NOT probe with `::regproc`:**
   ```sql
   select pg_get_functiondef('public.get_shared_project(uuid)'::regproc);
   -- ERROR 42883: function does not exist  <-- FALSE negative
   ```
   This only means the `(uuid)` cast didn't match. The RPC can still exist.

3. **CHECK 2b (RIGHT) — signature-agnostic probe:**
   ```sql
   select p.oid::regprocedure as signature, pg_get_functiondef(p.oid) as def
   from pg_proc p
   join pg_namespace n on n.oid = p.pronamespace
   where n.nspname='public' and p.proname='<rpc>';
   ```
   0 rows = truly absent. 1+ rows = exists.

4. **CHECK 2c — does the RPC body ALREADY emit the new fields? (boolean)**
   ```sql
   select pg_get_functiondef(p.oid) ilike '%<field1>%' as has_field1,
          pg_get_functiondef(p.oid) ilike '%<field2>%' as has_field2
   from pg_proc p
   join pg_namespace n on n.oid = p.pronamespace
   where n.nspname='public' and p.proname='<rpc>';
   ```
   Both true  → already upgraded, skip the RPC apply.
   Both false → old RPC, apply just the function body.
   Mixed      → apply for consistency.

5. **CHECK 3 — confirm project identity** (avoid running on the wrong DB):
   ```sql
   select current_database();
   ```

## PITFALL — Dashboard truncates the `def` blob
The Dashboard results panel CAPS the displayed `def` text from CHECK 2b. In the
LunaV session it cut off mid-body, hiding `client_comment`/`action_needed`,
which could read as "RPC doesn't have them." That's a display artifact. The
CHECK 2c boolean is computed server-side and is NOT truncated — it is the
reliable signal. Always use 2c for the yes/no; use 2b only to eyeball the SQL
once 2c says yes.

## PITFALL — paused migration must stay out of unrelated commits
If a migration is blocked (awaiting a user CHECK, a "go", or a fix), keep its
file UNTRACKED and never bundle it into a different feature commit. In the
LunaV session, `supabase/20260801_apply_client_feedback_live.sql` was paused on
CHECK 2c; when the double-click fix was committed, that file was deliberately
left out (`git add` only the two TSX files). Commit it only after the blocking
check resolves AND the user says "go".
