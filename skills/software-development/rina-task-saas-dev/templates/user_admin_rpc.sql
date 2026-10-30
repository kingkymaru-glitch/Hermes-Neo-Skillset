-- ============================================================
-- RINA — known-good admin-gated user RPC template (copy + modify)
-- Project: joliwavzczzfiwpwrbtf
-- Avoids the 3 pitfalls that caused 4 failed SQL rounds:
--   1) no ON CONFLICT (PK is single id) -> use UPDATE-then-INSERT
--   2) local vars prefixed v_ -> no "column reference X is ambiguous"
--   3) audit_logs is (id, organization_id, data, created_at) only
--      -> insert JSON into `data`, never invented columns
-- Run ONCE in Supabase SQL Editor. Idempotent (create or replace).
-- ============================================================

create or replace function public.upsert_user_profile(org uuid, payload jsonb)
returns void language plpgsql security definer set search_path = public as $$
declare
  v_id        uuid  := (payload->>'id')::uuid;
  v_name      text  := payload->>'name';
  v_email     text  := payload->>'email';
  v_position  text  := coalesce(payload->>'position','');
  v_department text := coalesce(payload->>'department','');
  v_role      text  := payload->>'role';
  v_jd        text  := coalesce(payload->>'job_description','');
  v_grade     text  := coalesce(payload->>'grade','');
  v_reports   jsonb := coalesce(payload->'reports_to_ids','[]'::jsonb);
  v_uid       uuid  := auth.uid();
  v_actor     text  := (select name from public.user_profiles where id = v_uid and organization_id = org);
begin
  if not exists (
    select 1 from public.user_profiles
    where id = v_uid and organization_id = org
      and role in ('SuperAdmin','MasterAdmin')
  ) then
    raise exception 'Not authorized to edit users in this org';
  end if;

  update public.user_profiles
     set name = v_name, email = v_email, position = v_position,
         department = v_department, role = v_role, job_description = v_jd,
         grade = v_grade, reports_to_ids = v_reports
   where id = v_id and organization_id = org;

  if not found then
    insert into public.user_profiles
      (id, organization_id, name, email, position, department, role,
       job_description, grade, reports_to_ids, active)
    values
      (v_id, org, v_name, v_email, v_position, v_department, v_role,
       v_jd, v_grade, v_reports, true);
  end if;

  insert into public.audit_logs (organization_id, data)
  values (org, jsonb_build_object(
    'action','user_updated','actor_id',v_uid,'actor_name',v_actor,
    'target_id',v_id,'target_name',v_name,'at',now()));
end;
$$;

create or replace function public.delete_user_profile(org uuid, uid uuid)
returns void language plpgsql security definer set search_path = public as $$
declare v_uid uuid := auth.uid(); v_actor text; v_name text;
begin
  if not exists (
    select 1 from public.user_profiles
    where id = v_uid and organization_id = org
      and role in ('SuperAdmin','MasterAdmin')
  ) then
    raise exception 'Not authorized to remove users in this org';
  end if;
  select name into v_name from public.user_profiles where id = uid and organization_id = org;
  select name into v_actor from public.user_profiles where id = v_uid and organization_id = org;
  update public.user_profiles set active = false where id = uid and organization_id = org;
  insert into public.audit_logs (organization_id, data)
  values (org, jsonb_build_object(
    'action','user_deleted','actor_id',v_uid,'actor_name',v_actor,
    'target_id',uid,'target_name',v_name,'at',now()));
end;
$$;

create or replace function public.restore_user_profile(org uuid, uid uuid)
returns void language plpgsql security definer set search_path = public as $$
declare v_uid uuid := auth.uid(); v_actor text; v_name text;
begin
  if not exists (
    select 1 from public.user_profiles
    where id = v_uid and organization_id = org
      and role in ('SuperAdmin','MasterAdmin')
  ) then
    raise exception 'Not authorized to restore users in this org';
  end if;
  select name into v_name from public.user_profiles where id = uid and organization_id = org;
  select name into v_actor from public.user_profiles where id = v_uid and organization_id = org;
  update public.user_profiles set active = true where id = uid and organization_id = org;
  insert into public.audit_logs (organization_id, data)
  values (org, jsonb_build_object(
    'action','user_restored','actor_id',v_uid,'actor_name',v_actor,
    'target_id',uid,'target_name',v_name,'at',now()));
end;
$$;
