---
name: rina-task-saas-dev
description: Use when working on RINA task SaaS (~/riina).
---

# RINA — Task Management SaaS (dev guide)

Multi-tenant task SaaS. React 19 + Vite + Supabase.

- Repo: `~/riina` (local), GitHub `kingkymaru-glitch/riina` (**PRIVATE**)
- Live: **https://rina-m.vercel.app** (renamed from riina-eight; `rina.vercel.app` is a THIRD-PARTY site — never use it)
- Supabase: `joliwavzczzfiwpwrbtf` (**Sydney**)
- Auth: real Supabase auth. Roles: `SuperAdmin`, `DepartmentHead`, `Member`.
- Two-tier approval: Tier-1 org approval by **Master Admin**; Tier-2 member approval by company SuperAdmin.

## Master Admin model
- Master Admin = `inventedmaru@gmail.com` + `kingkymaru@gmail.com` (hardcoded in `is_platform_admin()`).
- Lands on **Company Control** (approve/reject/delete companies). RPCs: `delete_organization`, `master_admin_enter_org` (enter any company as SuperAdmin), `fetch_orgs_with_creator` (list + creator + recent_actions), `approve_organization`.
- Company Control "Enter as Super Admin" calls `master_admin_enter_org(org)` then re-fetches profiles + selects org.

## CRITICAL — RLS infinite recursion
Policies on `user_profiles` / `organizations` / `tasks` / `audit_logs` MUST scope via the **SECURITY DEFINER** helper `my_org_ids()`:
```sql
create policy "profiles_select" on public.user_profiles
  for select using (id = auth.uid() or organization_id in (select public.my_org_ids()));
```
NEVER inline `select organization_id from public.user_profiles where id=auth.uid()` inside a policy on `user_profiles` — Postgres raises "infinite recursion detected in policy for relation user_profiles". Same pattern for insert/update/delete and tasks/audit (all via `my_org_ids()`). `my_org_ids()` is `security definer` so it bypasses RLS internally.

## DB access — what the agent CAN and CANNOT do
- **CANNOT run DDL** (CREATE/ALTER/GRANT, function body edits). No service-role key; anon key is rejected for DDL. Any schema/RPC change → write a clean `.sql` to `~/Desktop/`, MARU pastes into Supabase SQL Editor (project `joliwavzczzfiwpwrbtf`, postgres role). Never claim "applied" — only MARU can confirm.
- **CAN do row-level writes via the anon client when RLS permits** — e.g. an org member can `update`/`insert` `user_profiles` rows in the SAME org (verified: the seed/QA scripts used `sb.from('user_profiles').insert({...})` and `.update(...)` successfully as an authed org member).
- **CAN call SECURITY DEFINER RPCs** through the anon client: `create_org`, `join_org`, `approve_user`, `upsert_user_profile`, `set_user_hierarchy`, `delete_user_profile`, `restore_user_profile`, `master_admin_enter_org`, etc. These are the SAME functions the UI buttons invoke — so driving them from a Node script equals exercising the button.
- **Sanitized env parser is mandatory**: `.env.local` has trailing CR/whitespace that corrupts `VITE_SUPABASE_URL` parsing. Read with `m[1].replace(/[^ -~]/g,'').trim()`. See `references/rina_live_bugs.md`.
- If changing a function's RETURNS TABLE shape, you must `drop function if exists public.foo();` first — `create or replace` cannot change return type (42P13).

## Roles reality (corrected)
- Live enum (verified): **`SuperAdmin | MasterAdmin | DepartmentHead | Member`**. The skill's older top-line list (`SuperAdmin, DepartmentHead, Member`) is incomplete.
- **MasterAdmin is a real `user_profiles.role` value** — the highest non-platform tier. When MARU says "system admin", he means the **MasterAdmin role**, set via `user_profiles.update({ role: 'MasterAdmin' })` (RLS permits an org member to update same-org profiles). It is DISTINCT from the platform-admin tier (`is_platform_admin()` = inventedmaru/kingkymaru) that lands on Company Control.
- `fetchMyProfile` does **NOT** overwrite role on login, so a role set directly persists across sessions.
- Multi-org composite PK: `user_profiles` PK is `(id, organization_id)` with `organization_id` **NOT NULL** (migration 20260816). `create_org` → caller becomes SuperAdmin + org auto-approved. `join_org` → pending Member. `approve_user` (by SuperAdmin) activates.

## AI org-chart import (Gemini)
- `api/import-org-chart.ts` — Vercel serverless proxy, holds `GEMINI_API_KEY` server-side. Model `gemini-flash-latest` with retry + `gemini-flash-lite-latest` fallback on 503/429.
- UI: Admin → User Management → "Import from chart (AI)" (SuperAdmin only). Upload image/PDF → Gemini returns people JSON → merge by email/name (update existing, add new, never delete) → wire reportsTo → Org Chart + personnel refresh.
- **Env var trap:** Linux/Node env names are **case-sensitive**. Vercel var MUST be exactly `GEMINI_API_KEY` (all caps). A var named `Gemini_API_Key` won't be found by `process.env.GEMINI_API_KEY`. Setting an env var requires a **redeploy** to take effect, and a failed function build (e.g. missing `@types/node` → TS2580 'process') silently keeps the old function live.
- `@types/node` must be a devDependency or the api/ function fails to build (TS2580 on `process`).

## Deploy
- Vercel auto-deploys from git push to `main`. Commit with `git -c user.name=maru -c user.email=kingkymaru@gmail.com` so the webhook fires.
- Verify live function: `curl -X POST https://rina-m.vercel.app/api/import-org-chart -H "Content-Type: application/json" -d '{}'`. Response `Missing image/PDF data.` = env var loaded & function healthy; `GEMINI_API_KEY is not set` = env not in runtime.
- Verify UI: `curl -s -o /dev/null -w "%{http_code}" https://rina-m.vercel.app` → 200.

## SECURITY DEFINER RPC authoring pitfalls (VERIFIED by reading code — cost 4 failed SQL rounds)
When you author admin-gated RPCs (`upsert_user_profile`, `delete_user_profile`, etc.) that MARU runs in Supabase SQL Editor, these three mistakes each produced a SILENT failure (UI showed "Saved" but nothing persisted, or the function threw):
1. **`ON CONFLICT (id, organization_id)` with no composite constraint.** `user_profiles` PK is single-column `id` only — there is NO unique `(id, organization_id)`. Postgres throws `no unique or exclusion constraint matching the ON CONFLICT specification`. FIX: use **UPDATE-then-INSERT** (`update ... where id=:v_id and organization_id=:v_org; if not found then insert`), which has zero constraint dependency.
2. **Local PL/pgSQL vars named like columns -> `column reference "grade" is ambiguous`.** In `UPDATE ... SET grade = grade` the planner can't tell column from var. FIX: prefix EVERY local var `v_` (`v_grade`, `v_name`, `v_role`, `v_uid`...). This is mandatory, not cosmetic.
3. **`audit_logs` INSERT into invented columns rolls back the whole function.** The live `audit_logs` table is `(id, organization_id, data, created_at)` — it does NOT have `org_id / actor_id / actor_name / action / target_type / target_id / target_name`. Inserting into those non-existent columns throws and the tx rolls back, so even the user UPDATE never commits. FIX: insert as `insert into public.audit_logs (organization_id, data) values (org, jsonb_build_object('action',...,'actor_id',v_uid,...))`.
- **Verify column names against `supabase/schema.sql` before authoring** — the repo schema is the record of live columns (it drifted from what the agent assumed). Do not invent column names.
- **Make the audit INSERT defensive** so a logging failure can't void the data change (keep it last, and it's fine if it's best-effort).
- Known-good template: `templates/user_admin_rpc.sql` (copy + modify).

## Misc
- Org chart hierarchy uses `user_profiles.reports_to`. Org chart renders from `users` array (fetchUsers per org).
- `vercel.json` has SPA fallback rewrite `/(.*) -> /index.html`.
- Workspace header shows company name (`user.orgName`) unless Admin Panel branding overrides.

## Process-QA methodology (MARU's standing ask: exercise EVERY button, report what's broken)
When asked to verify the platform: do NOT skip to raw SQL — drive the exact `lib/api`
function each button calls (grep the component), authenticated as the correct role.
Record each as WORKS / BROKEN (with error code) → emit FINDINGS. Full function maps
for the Admin and Org Chart tabs + the seeded demo org are in
`references/rina_live_bugs.md` and `references/qa_function_map.md`.
- Admin-tab mutations (Add user, Upload .xlsx, Edit→Save, Remove/Restore) all funnel
  through `upsert_user_profile` / `set_user_hierarchy` / `remove_profile` /
  `restore_profile` RPCs — so ONE broken RPC can kill several buttons at once
  (see FINDING: `avatar` column, references/rina_live_bugs.md §3).
- Demo test org for QA: "RINA Test Co" (org `08fd8cd4-5ff6-4497-98f4-f6403a05ac08`),
  Neo=SuperAdmin / MARU=MasterAdmin / member1+member2 Members (password `RinaTest!2026`).
  Expanded to ~17 named staff for org-chart testing.

## Destructive-action guard (MARU's rule)
NEVER run a `delete`/`update` that removes rows without explicit consent. A terminal
row-delete command was BLOCKED by the consent gate this session — honor that: print
the target rows, ask, then act. This applies to Supabase row deletions too.
