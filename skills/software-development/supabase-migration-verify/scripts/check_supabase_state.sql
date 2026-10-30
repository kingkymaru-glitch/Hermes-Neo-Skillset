-- ============================================================
-- READ-ONLY state probe — paste into Supabase Dashboard → SQL Editor → Run
-- No mutations. Confirms current live schema/RPC state before applying a migration.
-- Replace the <TOKENS> before running.
-- ============================================================

-- CHECK 1: do the target columns already exist?
select column_name, data_type, column_default
from information_schema.columns
where table_schema = 'public'
  and table_name  = '<TABLE>'
  and column_name in ('<C1>','<C2>');
-- 0 rows = not present (apply needed). >=1 row = present (skip ALTER).

-- CHECK 2b: list ALL overloads of the RPC + their bodies (signature-agnostic)
select p.oid::regprocedure as signature,
       pg_get_functiondef(p.oid) as def
from pg_proc p
join pg_namespace n on n.oid = p.pronamespace
where n.nspname = 'public'
  and p.proname = '<RPC_NAME>';
-- 0 rows = RPC absent. 1+ rows = exists; inspect def for the columns you need.

-- CHECK 2c: does the RPC body already emit the new fields? (boolean, never truncated)
select pg_get_functiondef(p.oid) ilike '%<FIELD1>%' as has_field1,
       pg_get_functiondef(p.oid) ilike '%<FIELD2>%' as has_field2
from pg_proc p
join pg_namespace n on n.oid = p.pronamespace
where n.nspname = 'public'
  and p.proname = '<RPC_NAME>';
-- both true = already upgraded, skip apply. false = old RPC, apply just the function body.

-- CHECK 3: confirm project identity (avoid running on the wrong DB)
select current_database();
