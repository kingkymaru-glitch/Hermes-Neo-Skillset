# Centralized platform-admin approval gate (LUNAV model)

Use when a founder wants EVERY registration on a multi-tenant app to land in
their (owner) account for approve/reject — instead of each company's own
SuperAdmin only seeing their org's joins.

## The mechanism (LUNAV, ss-rover-cloud, 2026-07-29 — `supabase/phase2_approval.sql`)

LUNAV is single-platform (no companies). The gate:

1. `is_admin()` = hardcoded owner email list (e.g. `inventedmaru@gmail.com`,
   `adminmaru@maru.app`) joined against `auth.users.email`. SECURITY DEFINER.
2. Signup trigger `handle_new_user()` fires on `auth.users` INSERT:
   - admin emails -> `approved = true`
   - first user ever (`prof_count = 0`) -> `approved = true` (bootstrap)
   - everyone else -> `approved = false`
3. RLS `profiles_select_own`: `using ( auth.uid() = id or public.is_admin() )`
   -> admin sees ALL profiles across the platform.
4. `approve_user(target)` RPC guarded by `is_admin()` -> flips `approved=true`.

Result: every signup except the owner lands pending; the owner's approval UI
lists all of them; nobody enters until the owner clicks Approve.

## How RINA differs today (and what to change)

RINA is multi-tenant: `organization_id` per row, `my_org_id()` RLS, and the
"User Approvals" list is filtered by `fetchUsers(orgId)` -> `eq('organization_id', orgId)`.
So each company's SuperAdmin only sees their own org's pending joins, and a
"New company" founder auto-approves themselves (`approved=true`) and never
reaches the owner.

To mirror LUNAV on RINA, ADD a platform-admin concept on top of the per-org
role (do NOT remove the per-org model unless the founder wants full
centralization):

```sql
create or replace function public.is_platform_admin()
returns boolean language sql stable security definer set search_path = public as $$
  select exists (
    select 1 from auth.users u
    where u.id = auth.uid()
      and u.email in ('owner@domain.com')   -- the platform owner's email(s)
  );
$$;

-- profiles_select: platform admin sees every org
drop policy if exists "profiles_select" on public.user_profiles;
create policy "profiles_select" on public.user_profiles
  for select using ( organization_id = public.my_org_id() or id = auth.uid()
                     or public.is_platform_admin() );
```

**Critical gotcha:** `is_platform_admin()` reads `auth.uid()`, which is the
*calling* session — inside a `SECURITY DEFINER` trigger fired on `auth.users`
INSERT there is no "current user" session, so don't gate the trigger on
`is_platform_admin()`. Instead branch on `new.email` directly (the incoming
row's email). The RPC/RLS checks (called by a logged-in owner) CAN use
`is_platform_admin()` safely.

## Trade-off to confirm BEFORE building (founder often misses this)

Full LUNAV-mirror = the owner becomes a manual approval bottleneck for
EVERY registration, including people who'd otherwise self-serve a free company.
Ask: (a) owner approves all signups (full centralization), or (b) keep per-org
SuperAdmins AND add a separate platform-level "All pending" view the owner can
also action? The second preserves self-serve companies while still giving the
owner global visibility/override.

## Verification
- Owner email signs up -> profile row present, `approved=true` (dashboard table editor, postgres).
- Random email signs up -> `approved=false`, visible in owner's approval UI
  (NOT just the owner's own company).
- `approve_user(id)` called as owner -> flips `approved=true`; called as a
  non-owner -> raises `Forbidden`.
- Confirm the "New company" path ALSO lands pending (the whole point of
  centralization) — verify by creating a second throwaway company and checking
  it appears in the owner queue.
