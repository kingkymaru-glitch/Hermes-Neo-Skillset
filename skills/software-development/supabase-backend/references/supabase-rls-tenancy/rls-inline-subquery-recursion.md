# RLS infinite recursion — the INLINE-subquery variant (42P17)

Companion to PITFALL #1 in SKILL.md. The classic recursion trap is a
non-`SECURITY DEFINER` helper. This is the SECOND, easy-to-miss cause: the
policy body itself inlines a self-referencing subquery on the same table it
guards, so recursion fires even when a correct `SECURITY DEFINER` helper exists.

## Symptom
- App is authenticated but shows nothing / "create returns nothing".
- Direct anon REST call surfaces the real error (the client swallows it):
  ```bash
  curl -s "https://<REF>.supabase.co/rest/v1/user_profiles?select=*" \
    -H "apikey: <ANON>" -H "Authorization: Bearer <ANON>"
  # => {"code":"42P17","message":"infinite recursion detected in policy for relation \"user_profiles\""}
  ```

## The mistake
Writing the org-membership condition as a literal subquery on `user_profiles`
inside a `user_profiles` policy, instead of calling the helper:
```sql
-- WRONG
create policy "profiles_select" on public.user_profiles
  for select using (
    id = auth.uid()
    or organization_id in (
      select organization_id from public.user_profiles
      where id = auth.uid() and approved = true
    )
  );
```
Postgres re-enters RLS to evaluate the inner `from user_profiles` → recursion.
It does NOT matter that `my_org_ids()` is SECURITY DEFINER — the subquery never
calls it.

## The fix
Route every org-membership subquery through the `SECURITY DEFINER` set-helper:
```sql
create policy "profiles_select" on public.user_profiles
  for select using (
    id = auth.uid() or organization_id in (select public.my_org_ids())
  );
```
Apply the same pattern to INSERT/UPDATE/DELETE and to `tasks_all` / `audit_all`
(`organization_id in (select public.my_org_ids())`), plus `orgs_select` on
`organizations` (`id in (select public.my_org_ids()) or public.is_platform_admin()`).

## Prevention / review checklist
When reviewing any multi-org RLS migration, grep the policy bodies for a literal
`from public.user_profiles` — if the policy is ON `user_profiles` (or any table
whose FK/tenant column is derived from `user_profiles`), that inline subquery is a
recursion bomb. Replace it with the helper call. `npm run build` never parses SQL,
so this is invisible at build time.

## Real case (RINA, 2026-08-17)
`supabase/20260816_multi_org_membership.sql` defined `my_org_ids()` correctly
(SECURITY DEFINER) but inlined the subquery in all 6 policies. Result: every
`fetchMyProfiles()` threw 42P17 → app showed "You're not part of any company yet"
even though the profile row existed → founder was told "I try create it again and
it returns nothing." Fix: rewrote all policies to `in (select public.my_org_ids())`
(commit `1577902`). The full one-shot live fix (approve existing company +
`create_org` auto-approve + `my_org_ids()` + all policies) is the `rina_live_fix.sql`
pattern under `references/master-admin-company-control.md`'s sibling files.
