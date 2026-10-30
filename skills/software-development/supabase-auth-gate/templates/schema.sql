-- ─────────────────────────────────────────────────────────────────────────────
-- MARU auth database — paste into Supabase SQL Editor (Dashboard ▸ SQL).
-- Creates profiles table, signup trigger, row-level security, and the helpers
-- the app relies on. No secrets here; safe to commit.
-- ─────────────────────────────────────────────────────────────────────────────

-- 1. profiles table: one row per auth user, carries role + approval status.
create table if not exists public.profiles (
  id uuid primary key references auth.users(id) on delete cascade,
  email text,
  role text not null default 'user',          -- 'user' | 'superadmin'
  status text not null default 'pending',     -- 'pending' | 'approved' | 'rejected'
  created_at timestamptz not null default now()
);
create index if not exists profiles_status_idx on public.profiles(status);

-- 2. Auto-create a profile row (status=pending) whenever a user signs up.
create or replace function public.handle_new_user()
returns trigger
language plpgsql
security definer set search_path = public
as $$
begin
  insert into public.profiles (id, email, role, status)
  values (new.id, new.email, 'user', 'pending')
  on conflict (id) do nothing;
  return new;
end;
$$;

drop trigger if exists on_auth_user_created on auth.users;
create trigger on_auth_user_created
  after insert on auth.users
  for each row execute function public.handle_new_user();

-- 3. Helper: is the CURRENT user a superadmin? SECURITY DEFINER so it bypasses
--    RLS (avoids recursion when policies reference the profiles table).
create or replace function public.is_superadmin()
returns boolean
language sql
security definer set search_path = public
as $$
  select exists (
    select 1 from public.profiles where id = auth.uid() and role = 'superadmin'
  );
$$;

-- 4. Row-level security. Every read/write of app data goes through here.
alter table public.profiles enable row level security;

-- users read their own row; superadmin reads all
drop policy if exists "profiles_select" on public.profiles;
create policy "profiles_select" on public.profiles
  for select using (auth.uid() = id or public.is_superadmin());

-- only superadmin may change role/status (the approval gate)
drop policy if exists "profiles_update" on public.profiles;
create policy "profiles_update" on public.profiles
  for update using (public.is_superadmin()) with check (public.is_superadmin());

-- direct inserts blocked from the client (the trigger handles insert securely)
drop policy if exists "profiles_no_insert" on public.profiles;
create policy "profiles_no_insert" on public.profiles
  for insert with check (false);

-- ─────────────────────────────────────────────────────────────────────────────
-- SEED YOUR SUPERADMIN (you)
-- Step A: create the user. Easiest = Supabase Dashboard ▸ Authentication ▸ Add user,
--         Email: AdminMARU@maru.app  (or just "AdminMARU" — the app appends @maru.app)
--         Password: the strong one stored in your private vault note.
--         (Leave "Auto Confirm" ON so you can sign in immediately.)
-- Step B: promote that user to superadmin + approved (run here):
--
--   update public.profiles
--     set role = 'superadmin', status = 'approved'
--     where email = 'AdminMARU@maru.app';
--
-- Now signing in as AdminMARU grants the approval console at  #admin
-- (e.g. http://localhost:5175/#admin).
-- ─────────────────────────────────────────────────────────────────────────────
