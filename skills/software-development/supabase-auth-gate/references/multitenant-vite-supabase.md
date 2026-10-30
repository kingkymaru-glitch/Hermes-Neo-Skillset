# Multi-tenant Supabase for a Vite+React SPA (RINA case study, 2026-07-26)

Real email+password auth, multiple independent companies, free-tier Supabase, no backend server.
Repo: `~/riina` (Vite+React+TS). Reuses an existing free-tier project — link via
`supabase link --project-ref <ref>` then `supabase db query --linked --file supabase/schema.sql`.

## schema.sql (core)
```sql
create table if not exists public.organizations (
  id uuid primary key default gen_random_uuid(),
  name text not null,
  created_at timestamptz not null default now()
);
create table if not exists public.user_profiles (
  id uuid primary key default gen_random_uuid(),          -- = auth.users.id once claimed
  organization_id uuid not null references public.organizations(id) on delete cascade,
  name text not null default '', email text not null default '',
  position text not null default '', department text not null default '',
  grade text not null default '', phone text not null default '', bio text not null default '',
  reports_to text, role text not null default 'Member' check (role in ('SuperAdmin','DepartmentHead','Member')),
  join_date text, active boolean not null default false,
  created_at timestamptz not null default now()
);
create table if not exists public.tasks ( id uuid primary key, organization_id uuid not null references public.organizations(id) on delete cascade, data jsonb not null, created_at timestamptz not null default now() );
create table if not exists public.audit_logs ( id uuid primary key, organization_id uuid not null references public.organizations(id) on delete cascade, data jsonb not null, created_at timestamptz not null default now() );

alter table public.organizations enable row level security;
alter table public.user_profiles  enable row level security;
alter table public.tasks          enable row level security;
alter table public.audit_logs     enable row level security;

create or replace function public.my_org_id() returns uuid language sql stable as $$
  select organization_id from public.user_profiles where id = auth.uid();
$$;

drop policy if exists "profiles_select" on public.user_profiles;
create policy "profiles_select" on public.user_profiles for select using (organization_id = public.my_org_id());
drop policy if exists "profiles_insert" on public.user_profiles;
create policy "profiles_insert" on public.user_profiles for insert with check (organization_id = public.my_org_id());
drop policy if exists "profiles_update" on public.user_profiles;
create policy "profiles_update" on public.user_profiles for update using (organization_id = public.my_org_id()) with check (organization_id = public.my_org_id());
-- tasks / audit_logs: for all using (organization_id = public.my_org_id()) with check (same)

create or replace function public.handle_new_auth_user()
returns trigger language plpgsql security definer set search_path = public as $$
declare v_org uuid; v_name text; v_position text; v_department text; v_existing uuid;
begin
  v_name := coalesce(new.raw_user_meta_data->>'name','');
  v_position := coalesce(new.raw_user_meta_data->>'position','');
  v_department := coalesce(new.raw_user_meta_data->>'department','');
  if new.raw_user_meta_data->>'company_name' is not null and new.raw_user_meta_data->>'company_name' <> '' then
    insert into public.organizations (name) values (new.raw_user_meta_data->>'company_name') returning id into v_org;
    insert into public.user_profiles (id, organization_id, name, email, position, department, role, active)
      values (new.id, v_org, v_name, new.email, v_position, v_department, 'SuperAdmin', true);
    return new;
  end if;
  v_org := (new.raw_user_meta_data->>'organization_id')::uuid;
  if v_org is null then
    insert into public.user_profiles (id, organization_id, name, email, position, department, role, active)
      values (new.id, null, v_name, new.email, v_position, v_department, 'Member', true);
    return new;
  end if;
  select id into v_existing from public.user_profiles where organization_id = v_org and lower(email)=lower(new.email) and active=false limit 1;
  if v_existing is not null then
    update public.user_profiles set id=new.id, active=true, name=coalesce(nullif(v_name,''),name) where id=v_existing;
  else
    insert into public.user_profiles (id, organization_id, name, email, position, department, role, active)
      values (new.id, v_org, v_name, new.email, v_position, v_department, 'Member', true);
  end if;
  return new;
end; $$;
drop trigger if exists on_auth_user_created on auth.users;
create trigger on_auth_user_created after insert on auth.users for each row execute function public.handle_new_auth_user();
```

## API layer (src/lib/api.ts)
- `signUpFirstAdmin({companyName, name, email, password, position, department})` -> `supabase.auth.signUp({ email, password, options:{ data:{ company_name, name, position, department } } })`.
- `signUpMember({organizationId, name, email, password, position, department})` -> `signUp({..., options:{ data:{ organization_id, name, position, department } } })`.
- `signIn({email,password})` -> `supabase.auth.signInWithPassword`.
- `fetchUsers(orgId)` / `fetchTasks(orgId)` / `fetchAudit(orgId)` -> `supabase.from(...).select().eq('organization_id', orgId)`.
- `inviteMember(orgId, user)` -> `insert` a `user_profiles` row (`active:false`, no auth id yet) so the member can later claim it.
- `upsertProfile(orgId, user)` -> **`.upsert(row, { onConflict:'id' })`** (insert new / update existing — one path).
- `removeProfile(orgId, id)` / `removeTask` / `addAudit` -> `eq('organization_id', orgId)`.
- `setCurrentOrg(id)` / `getCurrentOrg()` — module-global used only for branding scoping (localStorage `rina:activeOrg`); the data hooks take `orgId` as a prop (see pitfall below).

## React (src/App.tsx + hooks/app.tsx)
- `useAuth()` returns `{ session, orgId, loading, login, logout }`. `orgId` set from the profile's `organization_id` inside the auth effect AND `onAuthStateChange`.
- `App` = thin shell: `if (auth.loading) <Loading/>; if (!user) <Login onLogin={/* session updates via onAuthStateChange */}/>; return <Workspace key={`${user.id}:${orgId}`} user orgId ... />`.
- **Data hooks take `orgId` and reload on it** — this is the child-before-parent fix:
  ```ts
  export function useUsers(orgId: string | null) {
    const [users, setUsers] = useState<User[]>([]);
    const reload = useCallback(async () => {
      if (!orgId) { setUsers([]); return; }
      setUsers(await fetchUsers(orgId));
    }, [orgId]);
    useEffect(() => { reload(); }, [reload]);
    // addUser -> inviteMember(orgId, user) + reload; upsert -> upsertProfile(orgId, payload) + reload; removeUser similar
  }
  ```
  Do NOT have these hooks read `getCurrentOrg()` from a module-global inside the initializer — child effects run before the parent `useAuth` effect that sets it, so they'd load with a null org.
- `supabase.ts` must guard the import: `export const SUPABASE_CONFIGURED = Boolean(url && anonKey);` and build a placeholder client when false so App can render a "Backend not configured" screen instead of a blank white crash (`createClient('', '')` throws `supabaseUrl is required`).

## Login.tsx (real auth)
Three modes — Sign in / Create company / Join company (invite code = the org id).
Create -> `signUpFirstAdmin`; Join -> `signUpMember({organizationId: inviteCode})`; Sign in -> `signIn`.
After signup, Supabase may require email confirmation (depending on project setting) — handle by
showing "Check your email to confirm" and/or disabling "Confirm signups" for the test.

## Verification (what actually worked this session)
- Schema + trigger applied via `supabase db query --linked --file`. Tables + trigger confirmed present.
- Trigger tested by inserting into `auth.users` directly as the project owner (fires the trigger);
  confirmed an org + SuperAdmin profile were created, then deleted the test rows. No deliverable email needed.
- `npm run build` green. **Also ran `npx tsc --noEmit`** after a refactor that left `submitNewUser`
  undefined — esbuild's `vite build` did NOT catch the dangling reference; tsc did. (Covered in
  `vercel-prod-deploy-verification` esbuild pitfall.)
- Vercel env vars `VITE_SUPABASE_URL` + `VITE_SUPABASE_ANON_KEY` MUST be set in the dashboard or
  the deployed app shows "Backend not configured" / blank. `.env.local` covers local dev only.
