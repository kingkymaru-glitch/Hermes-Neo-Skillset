# Creator-gate RPCs (Supabase, paste in SQL Editor)

MARU's rule: only an authenticated, installed app user may create a room
(broadcast the AR big arrow). Browser/link users are view-only. Enforce in the
RPC itself AND hide the "Summon" button in the client.

```sql
-- creator must be a real, logged-in Supabase user
create or replace function create_room(
  p_skin text default 'arrow',
  p_all_app boolean default false,
  p_label text default 'SkyPin'
) returns json language plpgsql security definer as $$
declare v_id uuid; v_token text;
begin
  if auth.uid() is null then
    raise exception 'auth_required';   -- anonymous callers blocked here
  end if;
  v_token := encode(gen_random_bytes(9), 'base64')
            ;  -- make URL-safe in app layer
  insert into rooms (creator_id, skin, all_app, label, token)
  values (auth.uid(), p_skin, p_all_app, p_label, v_token)
  returning id into v_id;
  insert into participants (room_id, user_id, display_name, is_creator)
  values (v_id, auth.uid(), 'Host', true);
  return json_build_object('room_id', v_id, 'token', v_token);
end; $$;

-- join is open (anonymous viewers allowed) but CREATE is not
create or replace function join_room(p_token text, p_name text default 'Guest')
returns json language plpgsql security definer as $$
declare v_room rooms; v_cap int;
begin
  select * into v_room from rooms where token = p_token and (expires_at is null or expires_at > now());
  if not found then raise exception 'not_found'; end if;
  select case when v_room.all_app then 15 else 5 end into v_cap;
  if (select count(*) from participants where room_id = v_room.id) >= v_cap
  then raise exception 'full'; end if;
  insert into participants (room_id, user_id, display_name)
  values (v_room.id, coalesce(auth.uid(), gen_random_uuid()), p_name)
  on conflict do nothing;
  return json_build_object('room_id', v_room.id);
end; $$;

-- wipe live positions immediately on close
create or replace function close_room(p_room uuid)
returns void language plpgsql security definer as $$
begin
  delete from participants where room_id = p_room;
  update rooms set expires_at = now() where id = p_room;
end; $$;
```

After applying: `notify pgrst, 'reload schema';`

Client: the "Summon SkyPin" button renders only when `supabase.auth.currentUser`
is non-null (installed app). The web viewer screen ships with NO create button.
