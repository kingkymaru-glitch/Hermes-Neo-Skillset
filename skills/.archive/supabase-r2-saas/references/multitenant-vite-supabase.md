# Multi-tenant Vite SPA on Supabase (RINA pattern)

Condensed, reusable recipe for a multi-company SaaS where each org is fully isolated
and login is real email+password. Frontend-agnostic schema; client layer shown for Vite.

## Schema (apply with `supabase db query --linked --file supabase/schema.sql`)

Tables — every tenant row carries `organization_id`:
```sql
create table if not exists public.organizations (
  id uuid primary key default gen_random_uuid(),
  name text not null,
  created_at timestamptz not null default now()
);
create table if not exists public.user_profiles (
  id uuid primary key default gen_random_uuid(),   -- becomes auth.users.id once claimed
  organization_id uuid not null references public.organizations(id) on delete cascade,
  name text not null default '', email text not null default '',
  position text not null default '', department text not null default '',
  grade text not null default '', phone text not null default '', bio text not null default '',
  reports_to text,
  role text not null default 'Member' check (role in ('SuperAdmin','DepartmentHead','Member')),
  join_date text, active boolean not null default false,
  created_at timestamptz not null default now()
);
create table if not exists public.tasks (
  id uuid primary key, organization_id uuid not null references public.organizations(id) on delete cascade,
  data jsonb not null, created_at timestamptz not null default now()
);
create table if not exists public.audit_logs (
  id uuid primary key, organization_id uuid not null references public.organizations(id) on delete cascade,
  data jsonb not null, created_at timestamptz not null default now()
);
```

RLS — one helper, every policy:
```sql
alter table public.organizations enable row level security;
alter table public.user_profiles  enable row level security;
alter table public.tasks          enable row level security;
alter table public.audit_logs     enable row level security;
create or replace function public.my_org_id()
returns uuid language sql stable as $$
  select organization_id from public.user_profiles where id = auth.uid();
$$;
-- repeat per table, e.g. tasks:
drop policy if exists "tasks_all" on public.tasks;
create policy "tasks_all" on public.tasks
  for all using (organization_id = public.my_org_id())
  with check (organization_id = public.my_org_id());
```

Signup trigger — handles BOTH first-admin and member-join in one place:
```sql
create or replace function public.handle_new_auth_user()
returns trigger language plpgsql security definer set search_path = public as $$
declare v_org uuid; v_name text; v_pos text; v_dep text; v_existing uuid;
begin
  v_name := coalesce(new.raw_user_meta_data->>'name','');
  v_pos  := coalesce(new.raw_user_meta_data->>'position','');
  v_dep  := coalesce(new.raw_user_meta_data->>'department','');
  if new.raw_user_meta_data->>'company_name' is not null and new.raw_user_meta_data->>'company_name' <> '' then
    insert into public.organizations (name) values (new.raw_user_meta_data->>'company_name') returning id into v_org;
    insert into public.user_profiles (id, organization_id, name, email, position, department, role, active)
      values (new.id, v_org, v_name, new.email, v_pos, v_dep, 'SuperAdmin', true);
    return new;
  end if;
  v_org := (new.raw_user_meta_data->>'organization_id')::uuid;
  if v_org is null then
    insert into public.user_profiles (id, organization_id, name, email, position, department, role, active)
      values (new.id, null, v_name, new.email, v_pos, v_dep, 'Member', true);
    return new;
  end if;
  select id into v_existing from public.user_profiles
    where organization_id = v_org and lower(email)=lower(new.email) and active=false limit 1;
  if v_existing is not null then
    update public.user_profiles set id=new.id, active=true,
      name=coalesce(nullif(v_name,''),name), position=coalesce(nullif(v_pos,''),position),
      department=coalesce(nullif(v_dep,''),department) where id=v_existing;
  else
    insert into public.user_profiles (id, organization_id, name, email, position, department, role, active)
      values (new.id, v_org, v_name, new.email, v_pos, v_dep, 'Member', true);
  end if;
  return new;
end; $$;
drop trigger if exists on_auth_user_created on auth.users;
create trigger on_auth_user_created after insert on auth.users
  for each row execute function public.handle_new_auth_user();
```

## Client layer (Vite) — `src/lib/supabase.ts` + `src/lib/api.ts`

```ts
export const supabase = createClient(import.meta.env.VITE_SUPABASE_URL, import.meta.env.VITE_SUPABASE_ANON_KEY, {
  auth: { persistSession: true, autoRefreshToken: true, detectSessionInUrl: true },
});
```
- `signUpFirstAdmin({companyName, name, email, password, position, department})` →
  `supabase.auth.signUp({ email, password, options:{ data:{ company_name, name, position, department } } })`.
- `signUpMember({organizationId, name, email, password, position, department})` → same but `data:{ organization_id, ... }`.
- `signIn({email,password})` → `supabase.auth.signInWithPassword(...)`.
- All data fns take `orgId` and `select`/`insert`/`update`/`delete` with `.eq('organization_id', orgId)`.

## orgId threading (the load-order trap)
`useAuth()` reads the session profile and stores `orgId` in **state**, returns it. Pass
`orgId` as a prop into `useUsers(orgId)` / `useTasks(orgId)` / `useAudit(orgId)`. Their
`reload()` effect depends on `orgId`, so the first real load happens AFTER auth resolves
it. Do NOT stash `orgId` in a module global and read it inside a child hook's mount
effect — React runs child effects before parent effects, so the child reads the stale
global and loads empty. Thread it via state/props.

## Gotchas
- Supabase blocks signups from many domains (`example.com`, `rinatest.app` → "Email address ... is invalid"). Test the trigger by `insert into auth.users (...)` as the project owner (postgres) instead of a scripted signUp; clean up after.
- Free-tier SMTP rate-limits (~3-4/hr) and lands in spam. Turn OFF "Confirm signups" for headless testing; turn on + set Site URL for launch.
- Vite build succeeds with unset `VITE_*` env (inlines empty strings) → silent runtime auth failure. Set `VITE_SUPABASE_URL` + `VITE_SUPABASE_ANON_KEY` in Vercel dashboard; `.env.local` is dev-only.
- Avoid the dead near-twin Supabase project (the `eobkcsx...` ref here); reuse the real one (`okzmblyboudjffaixa`).
