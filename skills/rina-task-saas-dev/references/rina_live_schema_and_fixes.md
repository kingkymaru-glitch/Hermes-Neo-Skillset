# RINA live schema, RPC signatures & DB fixes

## Live `user_profiles` columns (introspected 2026-08-18)
id, organization_id, name, email, position, department, role, grade, level, reports_to, reports_to_ids, active, approved, job_description, phone, bio, join_date, created_at, updated_at
**No `avatar` column.** The `upsert_user_profile` RPC referenced `avatar` → broke Add/Upload/Edit.

## RPC signatures (how the app calls them — match these exactly)
- `upsert_user_profile(org text, payload jsonb)` — payload keys: `id, name, email, position, department, role, active, job_description, reports_to_ids`. (Recreate WITHOUT `avatar`.)
- `set_user_hierarchy(org, target, p_lvl int, p_reports text[])` — sets `level` + `reports_to_ids`.
- `create_org(name text)` → returns org id; caller → SuperAdmin, org approved.
- `join_org(org text)` → pending Member.
- `approve_user(target, org, approve bool)`.
- `delete_user_profile(org, target)` / `restore_user_profile(org, target)`.

## FINDING #1 — fix SQL (Desktop: RIINA_fix_upsert_avatar.sql)
Recreate `upsert_user_profile` as SECURITY DEFINER, body inserting/updating ONLY the live columns above (no `avatar`). Idempotent `CREATE OR REPLACE`. Pattern when any Admin add/edit button throws `42703 column "X" does not exist`: the RPC body references a dropped column — rebuild the RPC to match live columns.

## Signup 500 — fix SQL (Desktop: RIINA_fix_signup_null_org.sql)
Replace `handle_new_auth_user` trigger function so the bare-signup branch (no company_name, no organization_id) is a no-op `RETURN NEW`. `create_org`/`join_org` RPCs own profile creation, so no profile is needed on bare signup.

## DDL delivery constraint
Agent cannot run DDL (anon key blocked, CLI not authed, no service key/password in env). Deliver every schema change as a SQL file to MARU's `~/Desktop`; he pastes into Supabase SQL Editor and replies "SQL success". Verify the effect afterward via a Node read script (see scripts/audit_roster.cjs).
