-- Share-token public portal pattern (proven in ss-rover-cloud).
-- Full working schema: ~/Documents/ss-rover-cloud/supabase/schema.sql
-- Core idea: owners get RLS CRUD; anonymous clients get ONE security-definer
-- RPC keyed by an unguessable UUID token. No anon table policies.

-- Owner RLS (repeat per table, joining up to the owning project):
-- create policy "x_owner_all" on public.x for all
--   using (exists (select 1 from projects p where p.id = x.project_id and p.owner_id = auth.uid()))
--   with check (same);

-- Public read path:
create or replace function public.get_shared_project(share_token uuid)
returns jsonb language sql security definer set search_path = public stable
as $$
  select jsonb_build_object(
    'project', jsonb_build_object('id', p.id, 'project_name', p.project_name),
    'models', coalesce((
      select jsonb_agg(jsonb_build_object(
        'id', m.id, 'file_url', m.file_url,
        'markers', coalesce((select jsonb_agg(to_jsonb(k)) from markers k where k.model_id = m.id), '[]')
      )) from models m where m.project_id = p.id), '[]')
  ) from projects p where p.client_share_token = share_token;
$$;
grant execute on function public.get_shared_project(uuid) to anon, authenticated;

-- Token mint/rotate (owner-checked):
create or replace function public.generate_share_token(p_project_id uuid)
returns uuid language plpgsql security definer set search_path = public
as $$
declare t uuid;
begin
  if not exists (select 1 from projects where id = p_project_id and owner_id = auth.uid())
    then raise exception 'Not project owner'; end if;
  t := gen_random_uuid();
  update projects set client_share_token = t where id = p_project_id;
  return t;
end; $$;
grant execute on function public.generate_share_token(uuid) to authenticated;

-- Also: trigger on auth.users to auto-insert profiles row on signup
-- (security definer handle_new_user(); on conflict do nothing).
