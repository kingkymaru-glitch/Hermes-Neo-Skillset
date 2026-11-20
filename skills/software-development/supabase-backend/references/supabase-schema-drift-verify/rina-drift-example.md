# Worked example — RINA SaaS (`~/riina`, Supabase `joliwavzczzfiwpwrbtf`)

Session 2026-08-18: resumed RINA dev; verified which tables the code uses vs.
which the committed SQL actually defines.

## Recipe applied
1. Tables the client code touches (from `src/lib/api.ts`): `organizations`,
   `user_profiles`, `tasks`, `audit_logs`, `company_settings`, `reporting_lines`,
   `org_chart_positions`, `notifications`.
2. `grep -rIn "create table" --include=*.sql .` over the WHOLE repo (base
   `schema.sql` + every migration + every hand-run file under `supabase/`).
   Found DDL only for: `organizations`, `user_profiles`, `tasks`, `audit_logs`.
3. Diff → 4 drifted (live-only, NO committed DDL):
   - `company_settings` — inferred cols: `organization_id` (PK), `auto_start_hours`.
     Code paths: `getCompanySettings` (select `auto_start_hours`),
     `saveCompanySettings` (upsert, onConflict `organization_id`).
   - `reporting_lines` — inferred cols: `id`, `org_id`, `manager`, `report`,
     `is_primary`. Code: `fetchReportingLines` (select * where `org_id`),
     `addReportingLine` (upsert `{org_id,manager,report,is_primary}`,
     onConflict `org_id,manager,report`), `removeReportingLine` (delete by `id`).
   - `org_chart_positions` — inferred cols: `organization_id`, `user_id`, `x`, `y`.
     Code: `fetchOrgChartPositions` (select `user_id,x,y` where `organization_id`),
     `upsertOrgChartPosition` (upsert `{organization_id,user_id,x,y}`,
     onConflict `organization_id,user_id`).
   - `notifications` — inferred cols: `id`, `organization_id`, `data` (jsonb).
     jsonb carries: `userId`, `message`, `isRead`, `createdDate`,
     `relatedTaskId`. Code: `addNotification` (insert `{id,organization_id,
     data}`), `fetchNotifications` (select where `data->>userId`, order
     `data->>createdDate`), `markNotificationRead` (flip `data.isRead`).
4. PK drift check: `user_profiles` PK was single-col `id`; the
   `20260816_multi_org_membership.sql` migration drops it and adds composite
   `primary key (id, organization_id)`. `schema.sql` still shows the old PK — do
   NOT trust `schema.sql` alone.

## jsonb-carrier note
`tasks`, `notifications`, `audit_logs` store their real model inside a `data`
jsonb column. `tasks.data` carries BOTH the legacy `Task` and the RINA
`RinaTask` shape; `fetchRinaTasks` filters rows that have both `executor` and
`initiator` keys. So the table DDL exists but the RINA model's true schema lives
in `src/types.ts` (the `RinaTask` type) + the select/insert payloads.

## Recommendation given to user
These 4 tables live only in the live DB with no migration file. To make the repo
reproducible from SQL: (a) export each table's DDL from the Supabase SQL Editor,
or (b) author `create table if not exists` migrations. Until then, any fresh-DB
build from the repo SQL will break RINA.

## Commands that worked
```
cd ~/riina && grep -rIn "create table" --include=*.sql .
cd ~/riina && grep -rIn "from('reporting_lines'\|from('org_chart_positions'\|from('company_settings'\|from('notifications')" src/lib/api.ts
```
(note: the 4 drifted tables have NO `create table` anywhere — confirmed by the
first grep returning only the 4 base tables.)
