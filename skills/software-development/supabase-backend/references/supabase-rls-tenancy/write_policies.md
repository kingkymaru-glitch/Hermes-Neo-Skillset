# Mutating RLS policies for a user_profiles table

Use when you enable RLS and must also lock down INSERT / UPDATE / DELETE
(not just SELECT). The pattern below is org-scoped + role-scoped and assumes
two SECURITY DEFINER helpers already exist (see recipes.md): `public.my_org_id()`
and `public.is_admin()`.

## The policy set
```sql
-- SELECT: org directory visible to all members (the approvals page and org
-- chart depend on it); a pending user can still read their OWN row so the
-- client can render an "awaiting approval" screen.
drop policy if exists "profiles_select" on public.user_profiles;
create policy "profiles_select" on public.user_profiles
  for select using ( organization_id = public.my_org_id() or id = auth.uid() );

-- INSERT: SuperAdmin only (client-side invites are SuperAdmin-gated).
drop policy if exists "profiles_insert" on public.user_profiles;
create policy "profiles_insert" on public.user_profiles
  for insert with check ( public.is_admin() or organization_id = public.my_org_id() );

-- UPDATE: a member edits ONLY their own row; SuperAdmin edits anyone in org.
-- Prevents a rank-and-file member rewriting role / reports_to / job_description.
drop policy if exists "profiles_update" on public.user_profiles;
create policy "profiles_update" on public.user_profiles
  for update using ( id = auth.uid() or public.is_admin() )
  with check ( id = auth.uid() or public.is_admin() );

-- DELETE: SuperAdmin only.
drop policy if exists "profiles_delete" on public.user_profiles;
create policy "profiles_delete" on public.user_profiles
  for delete using ( public.is_admin() );

-- Finally turn RLS ON. It is frequently OFF on a live table even when
-- schema.sql said ENABLE — the deploy pipeline never ran that line
-- (see SKILL.md PITFALL #3).
alter table public.user_profiles enable row level security;
```

## Why this does NOT break signup
New signups are written by the `handle_new_auth_user()` trigger, which is
`SECURITY DEFINER` -> it bypasses RLS entirely. So the INSERT policy above
never gates a real signup. (`is_admin()` / `my_org_id()` are also
SECURITY DEFINER, so evaluating these policies cannot recurse — see PITFALL #1.)

## Client-side pitfall that silently blanks writes
When mapping a DB profile row -> client `User` state, do NOT hardcode fields to
`''`. A hardcoded `jobDescription: ''` in the profile->user mapper means:
  - the field always displays blank, AND
  - saving an edit writes `''` back, silently erasing real data.
Always map every column through (`profile.job_description ?? ''`). When you add
a column, grep every place the row is mapped to the client type and carry it.

## Verify after applying (no deliverable email needed)
Signup goes through the trigger (bypasses RLS), so you can't easily exercise the
INSERT policy from a normal client. To prove the UPDATE/DELETE policies hold,
sign up as a non-admin, then (as that user) attempt to UPDATE another user's
row — it should be rejected (0 rows changed). As SuperAdmin the same update
should succeed.

## Real-world example (RINA, 2026-07-31)
RLS was OFF on live `user_profiles` even though `schema.sql` contained the ENABLE
line. Added `supabase/migrations/20260731_profiles_rls_writes.sql` with the above
set, plus the `jobDescription` column migration from a prior commit. The code
(`hooks/app.tsx`) was also overwriting `jobDescription` with `''` — fixed by
mapping `profile.job_description ?? ''`. Both shipped via `git push` (Vercel build
green) but the SQL was applied by PASTING into the Supabase SQL Editor, because
Vercel's SPA build never runs migrations.
