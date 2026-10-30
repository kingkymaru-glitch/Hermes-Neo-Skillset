# Master Admin company control (approve / reject / delete ANY company)

Pattern: a "platform admin" (super-admin across ALL tenants) who manages every
company's registration — approve, reject, or permanently delete a company, from a
control-centre screen inside one of their own orgs. Session: RINA. Reusable for any
multi-tenant SaaS with a master-operator role.

## The two RLS traps this solves

**Trap 1 — orgs_select hides companies the admin isn't a member of.**
The normal multi-tenant policy is `id in (select my_org_ids())` — member sees only
their own orgs. But a MASTER admin must see EVERY company (pending AND approved, even
ones they never joined) to manage them. Without an override the control centre lists
almost nothing. Fix: OR in the platform-admin check:

```sql
drop policy if exists "orgs_select" on public.organizations;
create policy "orgs_select" on public.organizations
  for select using (
    id in (select public.my_org_ids())
    or public.is_platform_admin()          -- master sees all
  );
```
`is_platform_admin()` must be SECURITY DEFINER (same recursion rule as every helper
used inside RLS). It hardcodes the master emails (e.g. two founder accounts).

**Trap 2 — deleting a company must be a guarded RPC, not a raw `.delete()`.**
A plain `from('organizations').delete()` is denied/empty by RLS (no policy allows it)
or, worse, wide-open. Provide a SECURITY DEFINER RPC that (a) re-checks
`is_platform_admin()` inside the function body and (b) relies on `ON DELETE CASCADE`
FKs to remove the company's profiles/tasks/audit in one shot:

```sql
create or replace function public.delete_organization(target uuid)
returns void language plpgsql security definer set search_path = public as $$
begin
  if not public.is_platform_admin() then
    raise exception 'Only the platform admin can delete companies.';
  end if;
  delete from public.organizations where id = target;   -- cascades users/tasks/audit
end;
$$;
grant execute on function public.delete_organization(uuid) to authenticated;
```
Client: `const { error } = await supabase.rpc('delete_organization', { target: id });`

Confirm the cascade FK actually exists in the live schema before relying on it:
`organization_id uuid references public.organizations(id) on delete cascade` on
user_profiles / tasks / audit_logs. If a table lacks cascade, delete children first.

## Control-centre UI notes
- **REACHABILITY — put the control button on the OrgHome (choose-a-company) page,
  NOT only inside the workspace nav.** If "Company Control" lives only as a nav item
  inside the entered workspace (AppShell), a platform admin who has NO enterable
  company (fresh account, or every org pending) is stuck on the "choose a company"
  screen with no way to reach the control centre — a dead loop (RINA 2026-08-17:
  "I'm logged in and stuck at choose-a-company, I can't see the Company Control button,
  I can't navigate anywhere"). Fix: on the not-entered branch of App, detect the
  platform admin (`isPlatformAdmin()` in a mount effect) and render a "Company Control"
  button on OrgHome that toggles `showCompanyControl` → render `<CompanyApprovals
  onBack={() => setShowCompanyControl(false)} />` in place of OrgHome. Wire the same
  gating prop through `<OrgHome isPlatformAdmin onOpenCompanyControl … />`.
- Screen lists EVERY company split into "Pending approval" and "Approved companies",
  not only pending — the master must manage approved ones too (reject flips them back
  to pending).
- Reject = `approve_organization(id, false)` (same RPC as approve, just `false`). It
  only becomes a visible action once you stop filtering the list to `approved=false`.
- Delete is destructive → require an inline confirm ("Delete <name>? Yes, delete /
  Cancel") before firing the RPC.
- Show the screen only when `isPlatformAdmin()` is true (client gate) — but the RPC's
  own `raise exception` is the real security boundary; the client gate is UX only.
- Keep a note to the user: deleting their OWN org would remove themselves as
  SuperAdmin; the control centre is really for managing the OTHER companies.

## API layer (client)
Add alongside `approveOrganization`:
```ts
export async function deleteOrganization(targetId: string): Promise<void> {
  const { error } = await supabase.rpc('delete_organization', { target: targetId });
  if (error) throw error;
}
export async function fetchAllOrganizations() {
  return (await supabase.from('organizations').select('id, name, approved, created_at').order('created_at')).data ?? [];
}
```
Dropping the old pending-only fetcher (`fetchPendingOrganizations`) breaks no call sites
as long as the control centre is its only consumer — grep before removing.

## "Enter as Super Admin" — master admin helps a company set up (RINA 2026-08-17)
Beyond approve/reject/delete, the master admin often wants to get INSIDE any company's
workspace as its SuperAdmin to help configure functions (roles, users, tasks, chart).
The normal entry path is gated by `fetchMyProfiles()` — you can only enter orgs you have
a `user_profiles` row in. Give the master an RPC that creates that membership on demand:

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
Note the composite PK `(id, organization_id)` (multi-org) → `on conflict` upsert so
re-entering the same company doesn't duplicate the row. Client:
```ts
export async function enterOrgAsAdmin(orgId: string): Promise<void> {
  const { error } = await supabase.rpc('master_admin_enter_org', { target: orgId });
  if (error) throw error;
}
```
Wire it in the control-centre's `onEnterOrg` callback: call the RPC, then `await
auth.refresh(org, true); auth.selectOrg(org); setEntered(true)` so the freshly created
membership is picked up and the app drops into that company's workspace as SuperAdmin.
Add an "Enter as Super Admin" button on each company card (visible to `isPlatformAdmin()`
only). After entering, the company also appears in the master's "choose a company" list,
so they can re-enter anytime without the RPC.

## PITFALL — wire `onEnterOrg` in EVERY place the control screen is rendered (dead button)
RINA 2026-08-17: the same `<CompanyApprovals>` component was rendered in **two** places —
(1) the OrgHome not-entered branch (correctly given `onEnterOrg={async (org) => { enterOrgAsAdmin;
refresh; selectOrg; setEntered }`), and (2) the **workspace nav** `case 'companyApprovals'`
which rendered `<CompanyApprovals onBack={...} />` with **NO `onEnterOrg`**. Result: from
inside any company (e.g. LunaV) the "Enter as Super Admin" button was a dead button — the
master could see every company but could not jump into one. The control centre was only
reachable-from/functional-on the not-entered page.

RULE: when a control screen is mounted in multiple routes, the callback that powers its
primary action must be threaded into **every** mount site. Here: lift the enter handler
into the `Workspace` props (`onEnterOrgAsAdmin`) and pass it through to the
`companyApprovals` view too:
```tsx
case 'companyApprovals':
  return <Screen><CompanyApprovals onBack={() => setView('dashboard')} onEnterOrg={onEnterOrgAsAdmin} /></Screen>;
```
Treat "rendered more than once" as a red flag that you must grep every `<ComponentName`
site and pass the action callback everywhere, not just the first route you wired.

## Master admin lands on Company Control by default (not a company picker)
Founder preference (RINA 2026-08-17): "by default I should land on the Company Approvals
page." The platform admin's home is the control centre, not a company workspace. After the
platform-admin check resolves, auto-open it on the not-entered branch:
```tsx
const [showCompanyControl, setShowCompanyControl] = useState(false);
useEffect(() => {
  if (platformAdmin && !entered) setShowCompanyControl(true);   // master home = control centre
}, [platformAdmin, entered]);
// then in the !entered branch: if (showCompanyControl) return <CompanyApprovals .../>;
```
Keep "Company Approvals" in the workspace nav too so the master can jump back to control
from inside any company. Non-platform-admins are unaffected — they land on their own
company's dashboard (gated by `is_platform_admin()`).

## Show each company's creator (no creator column) — earliest SuperAdmin
Master wants to see "who created/registered this company" in the control list, so they
know exactly who is doing what. The `organizations` table has NO creator column; the
creator is the **earliest SuperAdmin profile** attached to that org (later "Enter as
Super Admin" adds more SuperAdmin rows — the first one is the real founder). Resolve it
in a SECURITY DEFINER RPC (so the master can read profiles of orgs they haven't entered,
which plain RLS would hide):
```sql
create or replace function public.fetch_orgs_with_creator()
returns table (id uuid, name text, approved boolean, created_at timestamptz, creator_name text, creator_email text)
language plpgsql security definer set search_path = public as $$
begin
  if not public.is_platform_admin() then raise exception 'Only the platform admin can list companies.'; end if;
  return query
  select o.id, o.name, o.approved, o.created_at,
    (select p.name  from public.user_profiles p where p.organization_id = o.id and p.role = 'SuperAdmin' order by p.created_at asc limit 1),
    (select p.email from public.user_profiles p where p.organization_id = o.id and p.role = 'SuperAdmin' order by p.created_at asc limit 1)
  from public.organizations o order by o.created_at asc;
end;
$$;
grant execute on function public.fetch_orgs_with_creator() to authenticated;
```
Client: `supabase.rpc('fetch_orgs_with_creator')` replaces the direct
`.from('organizations').select(...)` (which under RLS returns only orgs the master is a
member of). Render `Created by <name> (<email>)` on each card; guard `creator_name ||
creator_email` because an admin-entered org may have an empty name.

## Workspace header = company name (so the master knows which project they're in)
When jumping between companies as master admin, the top header must identify the current
company (e.g. TENAGA vs Integrax Berhad), not a generic tagline. Carry the org name onto
the session user and let it win by default, with an admin-set custom branding header still
overriding:
```ts
export interface User { ...; orgName?: string; }              // types.ts
// mapper (hooks/app.tsx): orgName: p.org_name ?? ''          // profile carries org_name
// AppShell headerTitle: brandingHeader && brandingHeader !== copy.brandHeader
//   ? brandingHeader : user.orgName || copy.brandHeader
```

