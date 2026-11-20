# Multi-org migration breaks role-guard RPCs (silent empty data)

## The trap
After a multi-org migration that changes a table's PK from `id` to the
composite `(id, organization_id)` (one auth user now belongs to several
orgs), any existing RPC/trigger whose AUTH GUARD reads the caller's role
WITHOUT an `organization_id` filter silently breaks.

Symptom signature: a privileged RPC ("set hierarchy", "approve user", etc.)
raises its "only a Super Admin / Master Admin can …" exception on EVERY call
— even from a verified SuperAdmin — yet the related UI *looks* fine because it
also reads from a redundant source (e.g. the org chart renders from
`user_profiles.reports_to_ids`, not the `reporting_lines` table the RPC was
supposed to populate). So `reporting_lines` stays empty (EDGES 0), matrix /
canvas edges sourced from it never appear, and the break is invisible until
someone uses the Admin "save hierarchy" write path.

## Why the guard fails
Pre-migration guard (WRONG after composite PK):
```sql
select role into v_role from user_profiles where id = auth.uid();
```
Post-migration `id` is no longer unique — the caller has one row per org.
This query returns multiple rows ("query returned more than one row") or,
with `limit 1`, an arbitrary non-privileged org row. Either way the guard
never sees the caller's SuperAdmin/MasterAdmin row in *this* org, so it
rejects. The fix is to scope by the org argument AND require `approved`:
```sql
select role into v_caller_role
from user_profiles
where id = auth.uid() and organization_id = org and approved = true;
if v_caller_role is null or v_caller_role not in ('SuperAdmin','MasterAdmin')
then raise exception 'Only a Super Admin or Master Admin can …';
end if;
```
Mirror the live role list exactly (`role in ('SuperAdmin','MasterAdmin',…)`).
If the app also has `MasterAdmin`, the guard MUST include it — a guard that
only checks `SuperAdmin` locks out real MasterAdmins.

## Silent-empty-data tell (how to spot it fast)
When a "write failed but UI looks right" report lands, suspect a dual-source
render:
1. grep the chart/canvas component for where EDGES come from. If the primary
   source is `reporting_lines`/`reporting_lines.*` but it ALSO merges in
   `user_profiles.reports_to_ids`, the chart can render even when the RPC that
   writes `reporting_lines` is dead.
2. Ask for a live `SELECT count(*) FROM reporting_lines WHERE org_id = :org;`.
   Zero rows + a working-looking chart = the RPC write path is broken, not the
   read path.
3. Reproduce the exact RPC call the UI makes (`supabase.rpc('set_user_hierarchy',
   {org, target, p_lvl, p_reports})`) and read the error string. The guard
   exception name is the tell.

## Root-cause protocol (don't guess the guard)
1. The broken RPC may NOT exist in any committed `supabase/*.sql` — it was
   created live during testing and lives only in the DB. Search the repo; if
   absent, the live body is authoritative and must be reconstructed from the
   app's call signature (types.ts + the api.ts rpc() call) and the real column
   set (live `user_profiles` columns, not the stale `schema.sql`).
2. Read the EXACT call: which params (org, target, p_lvl, p_reports), which
   columns they map to, and which table the RPC is supposed to write
   (`reporting_lines` here). Build the corrected RPC to match that contract
   exactly so the frontend needs no change.
3. Make the replacement RPC ALSO keep the secondary source in sync if the app
   reads from both — here: write `level` + `reports_to_ids` on the profile AND
   upsert the PRIMARY `reporting_lines`, while PRESERVING any matrix
   (`is_primary = false`) lines the admin drew on canvas.

## Schema/DB drift is the root cause, not a one-off
RPCs/triggers that were created live (during a debugging session) and never
committed to `supabase/` are a standing liability: the next migration can drop
or contradict them and nobody notices. When you fix a live-only RPC, ALSO add
it to `supabase/schema.sql` (or a dated migration) so the repo becomes the
source of truth again. Recommend this to the user even if they only pasted the
fix into the SQL Editor.

## Idempotent live-fix shape (matches the apply-verify runbook)
Write ONE re-runnable file: `ADD COLUMN IF NOT EXISTS` for any missing cols,
`CREATE TABLE IF NOT EXISTS` for the edge table, `DROP FUNCTION IF EXISTS …;
CREATE OR REPLACE FUNCTION …` for the RPC (full body), then `GRANT EXECUTE`.
Hand it to the user to paste into the Supabase SQL Editor (agent holds no DB
creds for this project). Verify with a live SELECT, not "SQL ran".
