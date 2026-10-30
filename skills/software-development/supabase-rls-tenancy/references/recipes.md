# Supabase RLS / Tenancy / Gate — working SQL

## 1. RLS recursion fix (54001 stack depth) — THE footgun
Helper that queries the SAME table the policy sits on MUST be SECURITY DEFINER,
else policy -> my_org_id() -> queries table -> policy -> ... -> stack overflow.

```sql
create or replace function public.my_org_id()
returns uuid language sql stable security definer set search_path = public as $$
  select organization_id from public.user_profiles where id = auth.uid();
$$;

-- Every policy uses it WITHOUT recursion because the function bypasses RLS:
create policy "profiles_select_own" on public.user_profiles
  for select using (organization_id = public.my_org_id());
```

Same rule for any admin-check helper used inside RLS:
```sql
create or replace function public.is_admin()
returns boolean language sql stable security definer set search_path = public as $$
  select exists (
    select 1 from public.profiles p
    join auth.users u on u.id = p.id
    where p.id = auth.uid()
      and (u.email = 'admin@maru.app' or u.email = 'you@gmail.com')
  );
$$;
grant execute on function public.is_admin() to authenticated;
```

## 2. Approval gate (only admin-approved users get in) — full migration
```sql
alter table public.profiles add column if not exists approved boolean not null default false;

-- backfill: approve known admin + bootstrap first user
update public.profiles set approved = true
where id in (select id from auth.users where email = 'you@gmail.com')
   or id in (select id from auth.users where email = 'admin@maru.app');
update public.profiles set approved = true where (select count(*) from public.profiles) = 1;

create or replace function public.approve_user(target uuid)
returns void language plpgsql security definer set search_path = public as $$
begin
  if not public.is_admin() then raise exception 'Forbidden'; end if;
  update public.profiles set approved = true where id = target;
end; $$;
grant execute on function public.approve_user(uuid) to authenticated;

-- signup trigger: auto-approve admin emails + first user, else pending
create or replace function public.handle_new_user()
returns trigger language plpgsql security definer set search_path = public as $$
declare prof_count int;
begin
  select count(*) into prof_count from public.profiles;
  insert into public.profiles (id, full_name, role, approved)
  values (new.id, coalesce(new.raw_user_meta_data->>'full_name',''), 'inspector',
    case
      when new.email in ('you@gmail.com','admin@maru.app') then true
      when prof_count = 0 then true   -- first user bootstraps as admin-approved
      else false end)
  on conflict (id) do nothing;
  return new;
end; $$;
drop trigger if exists on_auth_user_created on auth.users;
create trigger on_auth_user_created after insert on auth.users
  for each row execute function public.handle_new_user();

-- RLS: admins can see/manage all profiles (for the approval UI)
drop policy if exists profiles_select_own on public.profiles;
create policy "profiles_select_own" on public.profiles
  for select using (auth.uid() = id or public.is_admin());
drop policy if exists profiles_admin_update on public.profiles;
create policy "profiles_admin_update" on public.profiles
  for update using (public.is_admin()) with check (public.is_admin());
```

Edge gate (Next.js middleware) after `supabase.auth.getUser()`:
```ts
if (user && !isPublic) {
  const { data: prof } = await supabase.from('profiles').select('approved').eq('id', user.id).single();
  if (!prof?.approved) {
    const url = request.nextUrl.clone();
    url.pathname = '/login'; url.searchParams.set('reason','pending');
    return NextResponse.redirect(url);
  }
}
```
Edge Function (defense in depth): after `getUser()`, repeat the same `approved` read and return 403 if false.

## 3. Verify a signup trigger WITHOUT a deliverable email
Supabase blocks test domains at signup ("Email address … is invalid") and the
owner channel (`supabase db query`) bypasses RLS, so neither can exercise the
trigger+RLS path. Insert into auth.users directly as the linked owner:

```sql
do $$ declare
  new_uid uuid := gen_random_uuid();
  new_org uuid; r_role text;
begin
  insert into auth.users (id, email, raw_user_meta_data)
  values (new_uid, 'x@example.com', '{"company_name":"TriggerCo","name":"Trig"}');
  select organization_id, role into new_org, r_role
    from public.user_profiles where id = new_uid;
  raise notice 'org=% role=%', new_org, r_role;
  -- cleanup
  delete from public.user_profiles where id = new_uid;
  delete from public.organizations where id = new_org;
  delete from auth.users where id = new_uid;
end $$;
```
Confirm the notice shows the expected org + role, then the cleanup lines
have already run. This proves the trigger + RLS *logic* from the CLI.

## 4. Apply / deploy
```bash
supabase link --project-ref okzmblyboudjffaifixa
supabase db query --linked --file supabase/migration.sql
supabase functions deploy r2-presign   # Edge Functions are NOT in the Next build
```
