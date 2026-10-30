---
name: supabase-schema-drift-verify
description: Verify committed Supabase SQL defines all tables code uses.
version: 1
author: Neo
license: MIT
metadata:
  hermes:
    tags: [supabase, postgres, schema, drift, migration, verification]
    related_skills: [rina-task-saas-dev]
---

# Supabase / Postgres Schema-Drift Verification

When you inherit or resume work on a Supabase app, the repo's SQL is often NOT the
source of truth for what's live. Tables, PK changes, and functions get created in
the Supabase SQL Editor by hand and never committed. If you assume "repo SQL = DB",
you will (a) write migrations that fail because a table already exists, or (b)
believe the app is reproducible from the repo when it is not.

This skill gives a fast, deterministic verification recipe. Run it before
authoring any DDL/RPC, and again after to confirm parity.

## When to use
- Resuming an unfamiliar Supabase repo (especially ones with a `supabase/` dir of
  hand-run `.sql` migrations).
- Before writing a new migration that touches an existing table.
- When the app "works locally/live" but the repo schema doesn't mention a table
  the code clearly uses.
- After a session where the user pasted SQL into the Supabase editor — confirm the
  change is now represented in the repo.

## Verification recipe (deterministic)
1. Enumerate every table the client touches. From the data-layer code (e.g.
   `src/lib/api.ts`), grep for the accessors:
   `grep -rIn "from('TABLE')\|\.insert(\|\.upsert(\|rpc('" src/`
   Note each distinct table name the code reads/writes.
2. Enumerate every `create table` actually committed:
   `grep -rIn "create table" --include=*.sql .`
   Capture the set of defined tables.
3. Diff the two sets. Anything in (1) but not (2) is **schema drift** — a table
   that exists only in the live DB, with no committed DDL. Flag it explicitly;
   do NOT silently write a `create table` for it (that will 409/duplicate the
   live one) — instead recover its real shape from the code (step 4) and either
   (a) ask the user to export the DDL from Supabase, or (b) write a
   `create table if not exists` migration only if a fresh-DB rebuild is the goal.
4. Recover column shapes from code when DDL is missing: read the `.select('a,b')`
   and the `.upsert({...})` / `.insert({...})` payloads. Snake_case DB columns
   map to camelCase TS fields (e.g. `auto_start_hours` → `autoStartHours`).
   Record the inferred columns so a future migration or recovery script is exact.

## Pitfalls (verified this session)
- **Base schema.sql lies after migrations.** A migration can `alter table ... add
  constraint ... primary key (id, organization_id)` without updating
  `schema.sql`. If you grep only `schema.sql` you'll wrongly conclude the PK is
  single-column. ALWAYS grep ALL `*.sql` (base + every migration + every
  hand-run file under supabase/), not just the umbrella schema.
- **`create or replace function` cannot change return type.** If a committed
  function's RETURNS changed, the migration must `drop function if exists
  public.foo();` first or it errors 42P13. This is a drift signal too: a live
  function may differ from the repo copy.
- **jsonb-carrier tables hide the model.** Some apps store a typed model as
  `jsonb` inside one generic table (e.g. `tasks.data`, `notifications.data`,
  `audit_logs.data`). The table is "defined" but the model's real shape lives
  only in TypeScript types + the select/insert payloads. Treat the TS type +
  payload as the authoritative schema for that model.
- **Migrations that only rewrite policies/functions leave table DDL absent.** A
  file named like a "create tables" migration may in fact only rewrite RLS
  helpers — confirm by reading it, don't trust the filename.

## Output of a verification pass
Report to the user as:
- Tables defined in repo SQL (committed, reproducible).
- Tables drifted (live-only, no DDL) — list each with inferred columns from code.
- Any PK/function drift between repo and assumed live state.
- A one-line recommendation (recover DDL via Supabase export, or author
  `create table if not exists` for rebuild reproducibility).

## Reference
See `references/rina-drift-example.md` for a concrete worked example from the
`riina` RINA SaaS (4 tables live-only, recovered column shapes).
