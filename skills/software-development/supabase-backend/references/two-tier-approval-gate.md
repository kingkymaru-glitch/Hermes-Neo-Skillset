# Two-tier registration approval gate (platform-admin approves companies, per-org SuperAdmin approves members)

Real case: RINA (Vite/React SPA, project `joliwavzczzfiwpwrbtf`, 2026-08-07). The founder wanted LUNAV-style control: every NEW COMPANY registration must be approved by his main account; then everyone joining that company is approved by the company's own SuperAdmin. This is a hybrid of the centralized gate (P38) and the per-org silo — capture it as its own pattern.

## Model
- **TIER 1 (platform):** "New company" signup → company row `approved=false`, founder becomes `SuperAdmin` with `approved=false`. Nobody in that company can use RINA until the PLATFORM ADMIN clicks Approve in a Company Approvals screen.
- **TIER 2 (per-org):** Once a company is approved, a member who joins via invite code → `approved=false`, awaits that company's SuperAdmin (existing User Approvals flow).

## DB (idempotent migration)
```sql
-- 1) company approval flag
alter table public.organizations
  add column if not exists approved boolean not null default false;

-- 2) platform admin = hardcoded owner emails (mirrors LUNAV's two-email pattern)
create or replace function public.is_platform_admin()
returns boolean language sql stable security definer set search_path = public as $$
  select exists (
    select 1 from auth.users u
    where u.id = auth.uid()
      and u.email in ('kingkymaru@gmail.com', 'inventedmaru@gmail.com')
  );
$$;
grant execute on function public.is_platform_admin() to authenticated;

-- 3) CANONICAL profiles_select for a two-tier gate:
--    member sees own org (incl. pending), pending user sees own row, platform admin sees ALL.
drop policy if exists "profiles_select" on public.user_profiles;
create policy "profiles_select" on public.user_profiles
  for select using (
    organization_id = public.my_org_id()
    or id = auth.uid()
    or public.is_platform_admin()
  );

-- 4) platform admin can see/select ALL orgs (for Company Approvals)
drop policy if exists "orgs_select" on public.organizations;
create policy "orgs_select" on public.organizations
  for select using (id = public.my_org_id() or public.is_platform_admin());

-- 5) RPC: platform admin approves/rejects a company
create or replace function public.approve_organization(target uuid, approve boolean)
returns void language plpgsql security definer set search_path = public as $$
begin
  if not public.is_platform_admin() then
    raise exception 'Only the platform admin can approve companies.';
  end if;
  update public.organizations set approved = approve where id = target;
end;
$$;
grant execute on function public.approve_organization(uuid, boolean) to authenticated;

-- 6) trigger: founder is NOT auto-approved (TIER 1). Platform-admin emails auto-approve
--    their own company so the owner is never locked out.
--    Member-join path unchanged (approved=false).
--    (see P20 for backfilling PRE-EXISTING companies: legacy orgs stay approved=true
--     by NOT flipping them here.)
```

## App code (SPA gate)
- `App.tsx`: **TIER-1 gate first** — `if (orgId && !orgApproved) return <Company registration pending/>` before the existing `user.approved===false` TIER-2 gate. Fetch `orgApproved` via `fetchOrgApproved(orgId)` (a `select approved from organizations`). Default to `true` on error so a missing column never locks everyone out.
- `CompanyApprovals.tsx`: lists `organizations where approved=false` (fetched via anon-granted RPC/`fetchPendingOrganizations`), Approve/Reject → `approveOrganization`.
- `AppShell.tsx`: show the "Company Approvals" nav item only when `isPlatformAdmin()` is true (fetched on mount). Regular SuperAdmins never see it.

## Verification
1. Live probe: create company → founder `approved=false`, org `approved=false`; sign in as founder → app shows "Company registration pending" (TIER-1 gate). Approve org via platform admin.
2. Join member into approved org → `pending_user_count()` 0→1; SuperAdmin sees them in User Approvals (TIER 2). Approve → user enters.
3. **Both tiers need a DELETE policy too** — see P37 hygiene note. A probe that creates test rows but can't delete them strands orphan rows in prod.

## Recurrency warning
A LATER migration in the same repo can re-introduce the over-restricted `profiles_select` (P22) AFTER an earlier fix "corrected" it. RINA's `20260729_profiles_rls_fix.sql` set the correct `or id = auth.uid()` policy, but `approval.sql` (applied later) reset it to `organization_id = my_org_id() and approved = true`, hiding pending users again. Always read the LIVE policy text or run a live approval probe; never trust that an earlier fix migration is the live state.
