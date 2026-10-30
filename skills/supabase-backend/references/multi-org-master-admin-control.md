# Multi-org Master-Admin control (RINA, 2026-08-17)

Extends P38/P39 (platform-admin / two-tier approval). Adds three things the
platform admin needs once "approve every company" is live: reach the control
centre before entering any company, enter any company as its SuperAdmin to
help set it up, and see each company's creator. All are reusable patterns.

## 1. Inline subquery in RLS policy → 42P17 "infinite recursion" (DISTINCT from P1)

P1 is the helper not being SECURITY DEFINER. This NEW failure is the *policy
itself* inlining a self-referencing subquery instead of calling the helper —
it recurses EVEN IF the helper is SECURITY DEFINER.

```sql
-- BROKEN: policy sub-selects user_profiles inline → infinite recursion (42P17)
create policy "profiles_select" on public.user_profiles
  for select using (
    id = auth.uid()
    or organization_id in (
      select organization_id from public.user_profiles
      where id = auth.uid() and approved = true
    )
  );
```

The fix is to call the SECURITY DEFINER set-returning helper instead:

```sql
create or replace function public.my_org_ids()
returns setof uuid language sql stable security definer set search_path = public as $$
  select organization_id from public.user_profiles where id = auth.uid();
$$;

create policy "profiles_select" on public.user_profiles
  for select using (
    id = auth.uid() or organization_id in (select public.my_org_ids())
  );
```

Signature: anon REST read of the table returns
`{"code":"42P17","message":"infinite recursion detected in policy for
relation \"user_profiles\""}`. When a logged-in user's `fetchMyProfiles()`
errors, the app falls into its empty/choose-a-company state ("logged in but
see nothing") — NOT a crash. Rule: **a policy that must resolve "which orgs
does the caller belong to" MUST go through the SECURITY DEFINER helper, never
an inline subquery on the same table the policy is on.** Same for
tasks/audit/orgs policies — all call `my_org_ids()`.

## 2. In-app create_org RPC that bypasses the signup trigger → founder lockout

When Tier-1 org approval is added (P39), the auto-approval logic lives in the
`on_auth_user_created` SIGNUP trigger. But an already-authed user creating a
company via an in-app RPC (`create_org(name)`) does NOT route through that
trigger — so if the RPC inserts `organizations` without setting `approved`,
the org is born `approved=false` and the Tier-1 gate ("Company registration
pending") blocks the founder who just created it, with no self-approve button.

Fix: make the RPC auto-approve (the founder IS the org's SuperAdmin):

```sql
create or replace function public.create_org(name text)
returns uuid language plpgsql security definer set search_path = public as $$
declare v_org uuid;
begin
  if nullif(trim(name), '') is null then raise exception 'Company name is required.'; end if;
  insert into public.organizations (name, approved) values (trim(name), true) returning id into v_org;
  insert into public.user_profiles (id, organization_id, name, email, position, department, role, active, approved)
  values (auth.uid(), v_org, '', '', '', '', 'SuperAdmin', true, true);
  return v_org;
end;
$$;
```

Rule: **every org-creation path (signup trigger AND in-app RPC) must set
`approved` explicitly.** Don't rely on one path carrying the other.

## 3. "Enter any company as SuperAdmin" (master admin helps set up a company)

The platform admin wants to enter a company they have no profile in. The
normal entry is gated by `fetchMyProfiles()` (only orgs with a profile row),
so add a SECURITY DEFINER RPC that upserts an approved SuperAdmin profile for
the caller into the target org, then re-fetch + selectOrg on the client:

```sql
create or replace function public.master_admin_enter_org(target uuid)
returns void language plpgsql security definer set search_path = public as $$
begin
  if not public.is_platform_admin() then
    raise exception 'Only the platform admin can enter companies as SuperAdmin.';
  end if;
  insert into public.user_profiles
    (id, organization_id, name, email, position, department, role, active, approved)
  values (auth.uid(), target, '', '', '', '', 'SuperAdmin', true, true)
  on conflict (id, organization_id) do update
    set role = 'SuperAdmin', approved = true, active = true;
end;
$$;
grant execute on function public.master_admin_enter_org(uuid) to authenticated;
```

Client flow: `await enterOrgAsAdmin(org)` → `auth.refresh(org, true)` →
`auth.selectOrg(org)` → `setEntered(true)`.

## 4. orgs_select must let the platform admin see EVERY company

The base multi-org `orgs_select` policy (`id in (select my_org_ids())`) hides
orgs the admin is not a member of — so a "Company Control" list shows nearly
nothing. Add the platform-admin override so they see all orgs (approved AND
pending):

```sql
drop policy if exists "orgs_select" on public.organizations;
create policy "orgs_select" on public.organizations
  for select using (
    id in (select public.my_org_ids())
    or public.is_platform_admin()
  );
```

## 5. Reach the control centre from the choose-a-company page

The Company Approvals screen normally lives in the workspace nav (AppShell).
But a master admin with NO enterable company can never reach it → dead loop.
Fix: on the pre-entry OrgHome page, if `is_platform_admin()`, show a
"Company Control" button that renders CompanyApprovals directly
(`onBack` returns to the chooser). Detect platform-admin on mount
(`isPlatformAdmin()` RPC) and gate the button on it.

## 6. Show each company's creator

`organizations` has no creator column. The creator = the EARLIEST SuperAdmin
profile in that org (later "Enter as Super Admin" adds more). Because RLS
scopes profile reads, fetch it via a SECURITY DEFINER, platform-admin-gated
RPC rather than a direct join:

```sql
create or replace function public.fetch_orgs_with_creator()
returns table (id uuid, name text, approved boolean, created_at timestamptz,
               creator_name text, creator_email text)
language plpgsql security definer set search_path = public as $$
begin
  if not public.is_platform_admin() then
    raise exception 'Only the platform admin can list companies.';
  end if;
  return query
  select o.id, o.name, o.approved, o.created_at,
    (select p.name  from public.user_profiles p
      where p.organization_id = o.id and p.role = 'SuperAdmin'
      order by p.created_at asc limit 1),
    (select p.email from public.user_profiles p
      where p.organization_id = o.id and p.role = 'SuperAdmin'
      order by p.created_at asc limit 1)
  from public.organizations o order by o.created_at asc;
end;
$$;
grant execute on function public.fetch_orgs_with_creator() to authenticated;
```

## 7. Workspace header should show the company name

Generic tagline header ("Organizational Clarity") makes a master admin
entering many companies lose track of which project they're in. Carry
`org_name` onto the session user (`toUser` adds `orgName` from the joined
`organizations.name`), and default the header to `user.orgName`, with a custom
admin-set branding header still overriding. Pure frontend, no SQL.

## 8. Display-only role relabel (no migration) — "Department Head" → "Verifier"

When the founder finds a stored role/enum label confusing vs. the person's
actual position and wants it shown differently, do a **display-only rename**:
keep the stored value (`'DepartmentHead'`) and change ONLY the display strings
in every component that renders it. This avoids migrating the stored value
across every row and leaves every `role === 'DepartmentHead'` permission check
untouched.

Find every spot with: `grep -rn "Department Head\|DepartmentHead" src/`.

Spots that render the label (all changed to show "Verifier"):
- Role badge/label mapper (e.g. AppShell `case 'DepartmentHead': return 'Verifier'`)
- `orgChart` chips: `member.role.replace('DepartmentHead','Verifier')`
- AdminPanel role `<option value="DepartmentHead">Verifier</option>`
- Profile / OrgHome `role === 'DepartmentHead' ? 'Verifier' : ...` ternaries
- Help/onboarding copy text ("Super Admin / Verifier can ...")

Only migrate the stored value if the founder explicitly wants the DB to
literally say the new word — otherwise advise against it. SuperAdmin / Member
labels stay unchanged. Confirmed superadmin/member labels unchanged.

## Deploy model (important)

Repo code + SQL are separate: `git push` → Vercel auto-builds the app, but the
SQL must be run by the user in the Dashboard SQL Editor (P35). The agent has no
DB write creds (anon/publishable key only). Deliver each DB change as a clean,
idempotent `.sql` file on the user's Desktop (see USER STYLE PREFERENCE in the
SKILL.md) and have them run it; confirm by a live refresh of the affected
screen, not a build.
