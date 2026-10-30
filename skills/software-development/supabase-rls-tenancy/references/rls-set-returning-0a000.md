# PITFALL #9 — ERROR 0A000: set-returning function in a policy expression

## The two wrong shapes that produced the error (RINA org-chart-canvas feature, 2026-08-18)

```sql
-- (1) In the RLS policy — calling a setof-returning fn directly via = any()
create policy "org_chart_positions_select" on public.org_chart_positions
  for select using ( organization_id = any (public.my_org_ids()) );
-- Error: Failed to run sql query:
-- ERROR: 0A000: set-returning functions are not allowed in policy expressions

-- (2) In the upsert RPC guard — unnest() on a setof is the wrong shape
if p_org is distinct from any (select unnest(public.my_org_ids())) then
  raise exception 'Not a member of this organization.';
end if;
```

`my_org_ids()` is `returns setof uuid`. Postgres rejects a set-returning function called
*directly* inside a policy USING/CHECK expression (0A000). `unnest()` of a setof is also
wrong — `my_org_ids()` already returns rows; wrapping it in `unnest()` has no array to unnest.

## The fix (idempotent — paste into the SQL Editor, re-runnable)

```sql
-- RINA org-chart-canvas: shared per-box positions, org-scoped RLS.
-- RULE: every membership test uses `in (select public.my_org_ids())`, never `= any (fn())`.

create table if not exists public.org_chart_positions (
  id          uuid primary key default gen_random_uuid(),
  organization_id uuid not null references public.organizations(id) on delete cascade,
  user_id     uuid not null,
  x           numeric not null,
  y           numeric not null,
  updated_by  uuid,
  updated_at  timestamptz not null default now(),
  unique (organization_id, user_id)
);
create index if not exists org_chart_positions_org_idx
  on public.org_chart_positions (organization_id);
alter table public.org_chart_positions enable row level security;

drop policy if exists org_chart_positions_select on public.org_chart_positions;
create policy org_chart_positions_select on public.org_chart_positions
  for select using (organization_id in (select public.my_org_ids()));

drop policy if exists org_chart_positions_insert on public.org_chart_positions;
create policy org_chart_positions_insert on public.org_chart_positions
  for insert with check (organization_id in (select public.my_org_ids()));

drop policy if exists org_chart_positions_update on public.org_chart_positions;
create policy org_chart_positions_update on public.org_chart_positions
  for update using (organization_id in (select public.my_org_ids()))
  with check (organization_id in (select public.my_org_ids()));

drop policy if exists org_chart_positions_delete on public.org_chart_positions;
create policy org_chart_positions_delete on public.org_chart_positions
  for delete using (organization_id in (select public.my_org_ids()));

create or replace function public.upsert_org_chart_position(
  p_org uuid, p_user uuid, p_x numeric, p_y numeric
) returns void language plpgsql security definer set search_path = public as $$
begin
  if not (p_org in (select public.my_org_ids())) then
    raise exception 'Not a member of this organization.';
  end if;
  insert into public.org_chart_positions (organization_id, user_id, x, y, updated_by, updated_at)
  values (p_org, p_user, p_x, p_y, auth.uid(), now())
  on conflict (organization_id, user_id)
  do update set x = excluded.x, y = excluded.y, updated_by = excluded.updated_by, updated_at = now();
end; $$;

grant execute on function public.upsert_org_chart_position(uuid, uuid, numeric, numeric) to authenticated;
grant select, insert, update, delete on public.org_chart_positions to authenticated;
```

## Why this is apply-time, not query-time
The 0A000 error is raised when Postgres *validates* the policy expression at `create policy`
time — i.e. the instant you hit Run in the SQL Editor. The migration never applies, the table
may be half-created, and the app gets a 500 on the first upsert. After fixing, re-run is safe
(`drop policy if exists` + `create or replace function` make it idempotent).

## Distinction from PITFALL #1 (recursion)
- `42P17 / 54001` (infinite recursion) → a policy/helper re-enters RLS on the same table.
- `0A000` → a set-returning function is called *directly* (e.g. `= any(fn())`) in a policy
  expression. No loop — Postgres just refuses the expression shape.
Both are fixed by routing through `in (select public.my_org_ids())`.
